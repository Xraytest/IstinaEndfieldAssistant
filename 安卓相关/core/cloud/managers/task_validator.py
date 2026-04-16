"""
任务验证引擎 - 提供多策略、多层次的任务完成验证

验证策略:
1. VLM 验证 - 基于 VLM 声明的验证
2. 客户端验证 - 基于客户端能力的独立验证
3. 渐进式验证 - 多次验证提高准确性
4. 业务规则验证 - 基于业务逻辑的验证
"""
import time
import hashlib
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging


class ValidationStrategy(Enum):
    """验证策略枚举"""
    VLM_BASED = "vlm_based"
    CLIENT_BASED = "client_based"
    PROGRESSIVE = "progressive"
    BUSINESS_RULES = "business_rules"


@dataclass
class ValidationResult:
    """验证结果"""
    completed: bool
    confidence: float  # 0.0 - 1.0
    validation_details: Dict[str, float]  # 各验证策略的得分
    completion_reason: str
    requires_review: bool = False
    review_priority: str = "low"  # low, medium, high
    validation_timestamp: float = field(default_factory=time.time)
    
    def can_decide_autonomously(self) -> bool:
        """判断是否可以自主决策"""
        return self.confidence >= 0.7 and not self.requires_review
    
    def has_conflicting_results(self) -> bool:
        """判断是否有冲突的验证结果"""
        if not self.validation_details:
            return False
        
        scores = list(self.validation_details.values())
        if len(scores) < 2:
            return False
        
        # 如果最高分和最低分差距超过 0.4，认为有冲突
        return max(scores) - min(scores) > 0.4


@dataclass
class TaskContext:
    """任务上下文"""
    task_id: str
    current_phase: str
    screenshots: List[np.ndarray]
    ocr_results: List[str]
    task_variables: Dict[str, Any]
    device_info: Dict[str, Any]
    iteration_count: int = 0
    execution_time: float = 0.0
    validation_weights: Dict[str, float] = field(default_factory=dict)
    completion_threshold: float = 0.8
    business_rules: List[str] = field(default_factory=list)
    vlm_validation_result: Optional[ValidationResult] = None
    client_validation_result: Optional[ValidationResult] = None
    
    def has_templates(self) -> bool:
        """检查是否有模板配置"""
        return 'templates' in self.task_variables
    
    def has_ocr_requirements(self) -> bool:
        """检查是否有 OCR 验证要求"""
        return 'ocr_keywords' in self.task_variables


class VLMBasedValidator:
    """VLM 声明验证器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("VLMBasedValidator")
    
    def validate(self, task_context: TaskContext) -> ValidationResult:
        """基于 VLM 声明进行验证"""
        # 检查 VLM 是否已声明任务完成
        vlm_result = task_context.vlm_validation_result
        
        if vlm_result:
            return vlm_result
        
        # 默认返回未完成的验证结果
        return ValidationResult(
            completed=False,
            confidence=0.0,
            validation_details={"vlm_declaration": 0.0},
            completion_reason="vlm_has_not_declared_completion"
        )


class ClientBasedValidator:
    """客户端独立验证器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("ClientBasedValidator")
    
    def validate(self, task_context: TaskContext) -> ValidationResult:
        """基于客户端能力进行独立验证"""
        scores = {}
        
        # 模板匹配验证
        if task_context.has_templates():
            scores['template'] = self._template_match_score(task_context)
        
        # OCR 文本验证  
        if task_context.has_ocr_requirements():
            scores['ocr'] = self._ocr_verification_score(task_context)
            
        # 状态变化验证
        scores['state_change'] = self._state_change_score(task_context)
        
        # 如果没有执行任何验证，返回默认结果
        if not scores:
            return ValidationResult(
                completed=False,
                confidence=0.0,
                validation_details={},
                completion_reason="no_validation_rules_configured"
            )
        
        # 计算综合得分
        weights = task_context.validation_weights or {
            'template': 0.4,
            'ocr': 0.3,
            'state_change': 0.3
        }
        
        total_weight = sum(weights.get(k, 0) for k in scores.keys())
        if total_weight == 0:
            total_weight = 1.0
        
        weighted_score = sum(
            scores.get(k, 0) * weights.get(k, 0) 
            for k in scores.keys()
        ) / total_weight
        
        # 判定完成状态
        threshold = task_context.completion_threshold
        is_completed = weighted_score >= threshold
        
        return ValidationResult(
            completed=is_completed,
            confidence=weighted_score,
            validation_details=scores,
            completion_reason=self._determine_completion_reason(scores, is_completed)
        )
    
    def _template_match_score(self, task_context: TaskContext) -> float:
        """模板匹配得分"""
        # TODO: 实现实际的模板匹配逻辑
        # 这里返回模拟得分
        templates = task_context.task_variables.get('templates', [])
        if not templates:
            return 0.0
        
        # 模拟：如果有模板配置，认为匹配成功
        return 0.85
    
    def _ocr_verification_score(self, task_context: TaskContext) -> float:
        """OCR 验证得分"""
        ocr_keywords = task_context.task_variables.get('ocr_keywords', {})
        positive_keywords = ocr_keywords.get('positive', [])
        negative_keywords = ocr_keywords.get('negative', [])
        
        if not positive_keywords and not negative_keywords:
            return 0.0
        
        # 合并所有 OCR 结果
        all_ocr_text = ' '.join(task_context.ocr_results).lower()
        
        # 检查正关键词
        positive_matches = sum(1 for kw in positive_keywords if kw.lower() in all_ocr_text)
        
        # 检查负关键词
        negative_matches = sum(1 for kw in negative_keywords if kw.lower() in all_ocr_text)
        
        # 计算得分
        if positive_keywords:
            positive_score = min(1.0, positive_matches / len(positive_keywords))
        else:
            positive_score = 1.0
        
        if negative_keywords:
            negative_penalty = min(1.0, negative_matches / len(negative_keywords))
        else:
            negative_penalty = 0.0
        
        return max(0.0, positive_score - negative_penalty)
    
    def _state_change_score(self, task_context: TaskContext) -> float:
        """状态变化得分"""
        if len(task_context.screenshots) < 2:
            return 0.5  # 没有足够的截图进行比较
        
        # 计算最近两张截图的变化率
        recent_screenshots = task_context.screenshots[-2:]
        change_rate = self._calculate_screenshot_change_rate(recent_screenshots)
        
        # 如果变化率很低，可能表示任务已完成（界面稳定）
        if change_rate < 0.1:
            return 0.9  # 界面稳定，可能已完成
        elif change_rate < 0.3:
            return 0.6  # 界面有轻微变化
        else:
            return 0.3  # 界面变化较大，可能还在执行中
    
    def _calculate_screenshot_change_rate(self, screenshots: List[np.ndarray]) -> float:
        """计算截图变化率"""
        if len(screenshots) < 2:
            return 0.0
        
        # 简化版：使用哈希比较
        hashes = [self._calculate_screenshot_hash(s) for s in screenshots]
        unique_hashes = len(set(hashes))
        
        return unique_hashes / len(hashes)
    
    def _calculate_screenshot_hash(self, screenshot: np.ndarray) -> str:
        """计算截图哈希"""
        # 简化版：取中心区域计算哈希
        if screenshot.size > 10000:
            h, w = screenshot.shape[:2]
            center = screenshot[h//4:3*h//4, w//4:3*w//4]
            if len(center.shape) == 3:
                center_gray = np.mean(center, axis=2).astype(np.uint8)
            else:
                center_gray = center
            return hashlib.md5(center_gray.tobytes()).hexdigest()
        else:
            return hashlib.md5(screenshot.tobytes()).hexdigest()
    
    def _determine_completion_reason(self, scores: Dict[str, float], 
                                    is_completed: bool) -> str:
        """确定完成原因"""
        if not is_completed:
            return "validation_threshold_not_met"
        
        # 找出得分最高的验证策略
        if not scores:
            return "unknown"
        
        best_strategy = max(scores.items(), key=lambda x: x[1])
        return f"{best_strategy[0]}_verification_passed"


class ProgressiveValidator:
    """渐进式验证器 - 多次验证提高准确性"""
    
    def __init__(self, max_attempts: int = 3, interval: float = 2.0,
                 logger: Optional[logging.Logger] = None):
        self.max_attempts = max_attempts
        self.interval = interval
        self.logger = logger or logging.getLogger("ProgressiveValidator")
    
    def validate(self, task_context: TaskContext) -> ValidationResult:
        """执行渐进式验证"""
        validation_attempts = []
        
        for attempt in range(self.max_attempts):
            # 执行单次验证
            single_result = self._single_validation_attempt(task_context)
            validation_attempts.append(single_result)
            
            # 如果置信度足够高，提前返回
            if single_result.confidence >= 0.9:
                self.logger.info(f"Progressive validation succeeded early at attempt {attempt + 1}")
                return single_result
            
            # 等待间隔后重试
            if attempt < self.max_attempts - 1:
                time.sleep(self.interval)
        
        # 融合多次验证结果
        fused_result = self._fuse_validation_attempts(validation_attempts)
        return fused_result
    
    def _single_validation_attempt(self, task_context: TaskContext) -> ValidationResult:
        """执行单次验证尝试"""
        # 使用客户端验证器进行单次验证
        client_validator = ClientBasedValidator(self.logger)
        return client_validator.validate(task_context)
    
    def _fuse_validation_attempts(self, attempts: List[ValidationResult]) -> ValidationResult:
        """融合多次验证结果"""
        if not attempts:
            return ValidationResult(
                completed=False,
                confidence=0.0,
                validation_details={},
                completion_reason="no_validation_attempts"
            )
        
        # 计算平均置信度
        avg_confidence = sum(a.confidence for a in attempts) / len(attempts)
        
        # 计算完成状态（多数投票）
        completed_count = sum(1 for a in attempts if a.completed)
        is_completed = completed_count > len(attempts) / 2
        
        # 合并验证详情
        merged_details = {}
        for attempt in attempts:
            for key, value in attempt.validation_details.items():
                if key not in merged_details:
                    merged_details[key] = []
                merged_details[key].append(value)
        
        # 计算平均值
        for key in merged_details:
            merged_details[key] = sum(merged_details[key]) / len(merged_details[key])
        
        return ValidationResult(
            completed=is_completed,
            confidence=avg_confidence,
            validation_details=merged_details,
            completion_reason=f"progressive_validation_{completed_count}/{len(attempts)}_completed"
        )


class BusinessRulesValidator:
    """业务规则验证器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("BusinessRulesValidator")
    
    def validate(self, task_context: TaskContext) -> ValidationResult:
        """基于业务规则验证任务完成状态"""
        rule_scores = {}
        
        for rule in task_context.business_rules:
            if rule == "all_reward_types_checked":
                rule_scores[rule] = self._validate_all_rewards_checked(task_context)
            elif rule == "back_to_main_interface":
                rule_scores[rule] = self._validate_main_interface(task_context)
            elif rule == "no_pending_operations":
                rule_scores[rule] = self._validate_no_pending_ops(task_context)
            else:
                # 未知规则，返回默认得分
                rule_scores[rule] = 0.5
        
        # 如果没有业务规则，返回默认结果
        if not rule_scores:
            return ValidationResult(
                completed=False,
                confidence=0.0,
                validation_details={},
                completion_reason="no_business_rules_configured"
            )
        
        # 计算业务规则满足度
        satisfied_rules = sum(1 for score in rule_scores.values() if score >= 0.8)
        total_rules = len(rule_scores)
        business_completeness = satisfied_rules / total_rules if total_rules > 0 else 0.0
        
        return ValidationResult(
            completed=business_completeness >= 0.9,
            confidence=business_completeness,
            validation_details=rule_scores,
            completion_reason=f"{satisfied_rules}/{total_rules}_business_rules_satisfied"
        )
    
    def _validate_all_rewards_checked(self, task_context: TaskContext) -> float:
        """验证所有奖励类型是否已检查"""
        # TODO: 实现实际的奖励检查验证逻辑
        # 这里返回模拟得分
        task_variables = task_context.task_variables
        
        # 检查是否有奖励检查相关的变量
        reward_types = ['mail', 'task', 'delivery', 'activity', 'pass']
        checked_count = sum(1 for rt in reward_types 
                           if f'{rt}_checked' in task_variables)
        
        return checked_count / len(reward_types)
    
    def _validate_main_interface(self, task_context: TaskContext) -> float:
        """验证是否返回主界面"""
        # TODO: 实现实际的主界面验证逻辑
        # 这里使用 OCR 关键词检测
        all_ocr_text = ' '.join(task_context.ocr_results).lower()
        
        # 主界面常见关键词
        main_interface_keywords = ['主界面', 'home', '基地', 'base']
        matches = sum(1 for kw in main_interface_keywords if kw in all_ocr_text)
        
        return min(1.0, matches * 0.5)
    
    def _validate_no_pending_operations(self, task_context: TaskContext) -> float:
        """验证没有待处理操作"""
        # TODO: 实现实际的待处理操作验证逻辑
        # 这里返回模拟得分
        return 0.8


class WeightedFusionStrategy:
    """加权融合策略"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("WeightedFusionStrategy")
        
        # 默认权重配置
        self.default_weights = {
            ValidationStrategy.VLM_BASED: 0.3,
            ValidationStrategy.CLIENT_BASED: 0.4,
            ValidationStrategy.PROGRESSIVE: 0.2,
            ValidationStrategy.BUSINESS_RULES: 0.1
        }
    
    def fuse(self, validation_results: Dict[str, ValidationResult]) -> ValidationResult:
        """融合多个验证结果"""
        if not validation_results:
            return ValidationResult(
                completed=False,
                confidence=0.0,
                validation_details={},
                completion_reason="no_validation_results_to_fuse"
            )
        
        # 收集所有验证得分
        all_scores = {}
        total_weight = 0.0
        weighted_sum = 0.0
        
        for strategy_name, result in validation_results.items():
            weight = self.default_weights.get(
                ValidationStrategy(strategy_name), 0.25
            )
            
            # 添加策略级别的得分
            all_scores[strategy_name] = result.confidence
            
            # 添加详细的验证得分
            for detail_name, detail_score in result.validation_details.items():
                all_scores[f"{strategy_name}_{detail_name}"] = detail_score
            
            weighted_sum += result.confidence * weight
            total_weight += weight
        
        # 计算融合后的置信度
        fused_confidence = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # 判定完成状态（多数投票 + 置信度加权）
        completed_count = sum(1 for r in validation_results.values() if r.completed)
        is_completed = (
            completed_count > len(validation_results) / 2 or
            fused_confidence >= 0.8
        )
        
        # 检查是否有冲突
        has_conflicts = any(r.has_conflicting_results() for r in validation_results.values())
        
        # 确定是否需要审查
        requires_review = has_conflicts or (0.5 < fused_confidence < 0.7)
        review_priority = "high" if has_conflicts else ("medium" if requires_review else "low")
        
        # 生成完成原因
        completion_reason = self._generate_completion_reason(
            validation_results, fused_confidence, is_completed
        )
        
        return ValidationResult(
            completed=is_completed,
            confidence=fused_confidence,
            validation_details=all_scores,
            completion_reason=completion_reason,
            requires_review=requires_review,
            review_priority=review_priority
        )
    
    def _generate_completion_reason(self, validation_results: Dict[str, ValidationResult],
                                   fused_confidence: float, is_completed: bool) -> str:
        """生成完成原因"""
        if not is_completed:
            return f"fused_confidence_{fused_confidence:.2f}_below_threshold"
        
        # 找出贡献最大的验证策略
        best_strategy = max(
            validation_results.items(),
            key=lambda x: x[1].confidence
        )
        
        return f"{best_strategy[0]}_led_completion_{fused_confidence:.2f}"


class TaskValidationEngine:
    """任务验证引擎 - 统一验证入口"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("TaskValidationEngine")
        
        # 初始化验证器
        self.validators = {
            'vlm_based': VLMBasedValidator(self.logger),
            'client_based': ClientBasedValidator(self.logger),
            'progressive': ProgressiveValidator(self.logger),
            'business_rules': BusinessRulesValidator(self.logger)
        }
        
        # 初始化融合策略
        self.fusion_strategy = WeightedFusionStrategy(self.logger)
    
    def validate_task(self, task_context: TaskContext) -> ValidationResult:
        """执行综合任务验证"""
        self.logger.info(f"Starting task validation for {task_context.task_id}")
        
        validation_results = {}
        
        # 并行执行所有验证策略
        for validator_name, validator in self.validators.items():
            try:
                validation_results[validator_name] = validator.validate(task_context)
                self.logger.debug(
                    f"{validator_name} validation: completed={validation_results[validator_name].completed}, "
                    f"confidence={validation_results[validator_name].confidence:.2f}"
                )
            except Exception as e:
                self.logger.error(f"{validator_name} validation failed: {e}")
                validation_results[validator_name] = ValidationResult(
                    completed=False,
                    confidence=0.0,
                    validation_details={},
                    completion_reason=f"validation_error_{str(e)}"
                )
        
        # 融合验证结果
        fused_result = self.fusion_strategy.fuse(validation_results)
        
        self.logger.info(
            f"Task validation completed: completed={fused_result.completed}, "
            f"confidence={fused_result.confidence:.2f}, reason={fused_result.completion_reason}"
        )
        
        return fused_result
    
    def validate_with_strategy(self, task_context: TaskContext, 
                              strategy: ValidationStrategy) -> ValidationResult:
        """使用特定策略进行验证"""
        validator_name = strategy.value
        if validator_name not in self.validators:
            raise ValueError(f"Unknown validation strategy: {strategy}")
        
        return self.validators[validator_name].validate(task_context)
