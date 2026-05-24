"""
决策转回机制 - 管理子任务与主任务间的决策流转

核心组件:
1. DecisionDelegationTrigger - 决策转回触发条件管理器
2. DecisionRequestGenerator - 决策请求生成器
3. DecisionResponseProcessor - 决策响应处理器
4. DecisionCoordinator - 决策协调器
"""
import time
import uuid
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging


class UrgencyLevel(Enum):
    """紧急程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionAction(Enum):
    """决策动作枚举"""
    CONTINUE_EXECUTION = "continue_execution"
    SKIP_TASK = "skip_task"
    RETRY_WITH_MODIFICATIONS = "retry_with_modifications"
    PAUSE_EXECUTION = "pause_execution"
    TERMINATE_CHAIN = "terminate_chain"
    ESCALATE_TO_HUMAN = "escalate_to_human"


@dataclass
class DecisionOption:
    """决策选项"""
    id: str
    action: str
    parameters: Dict[str, Any]
    confidence: float
    rationale: str


@dataclass
class DecisionRequest:
    """决策请求"""
    task_id: str
    current_state: Dict[str, Any]
    validation_results: Dict[str, Any]
    uncertainty_factors: List[str]
    recommended_options: List[DecisionOption]
    urgency_level: str
    context_snapshot: bytes
    request_timestamp: float = field(default_factory=time.time)
    cached_decision_reference: Optional[str] = None


@dataclass
class DecisionResponse:
    """决策响应"""
    decision_id: str
    action: str
    parameters: Optional[Dict[str, Any]]
    rationale: str
    confidence: float
    source: str
    response_timestamp: float = field(default_factory=time.time)


@dataclass
class ExecutionDirective:
    """执行指令"""
    action: str  # continue, skip, retry, terminate, delegate
    parameters: Optional[Dict[str, Any]] = None
    priority: int = 1
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DecisionDelegationTrigger:
    """决策转回触发条件管理器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("DecisionDelegationTrigger")
        
        # 触发阈值配置
        self.thresholds = {
            'confidence_threshold': 0.7,
            'conflict_threshold': 2,  # 至少 2 个验证策略冲突
            'ambiguity_score_threshold': 0.6,
            'resource_usage_threshold': 0.8,  # 80% 资源使用率
            'timeout_risk_threshold': 0.9  # 90% 超时风险
        }
    
    def should_delegate_decision(self, task_context: Dict[str, Any]) -> tuple:
        """
        判断是否需要将决策转回给主任务
        
        Returns:
            tuple: (should_delegate: bool, trigger_reasons: List[str])
        """
        trigger_reasons = []
        
        # 检查低置信度
        if self._check_low_confidence(task_context):
            trigger_reasons.append('low_confidence')
        
        # 检查验证冲突
        if self._check_conflicting_validations(task_context):
            trigger_reasons.append('conflicting_validations')
        
        # 检查模糊状态
        if self._check_ambiguous_state(task_context):
            trigger_reasons.append('ambiguous_state')
        
        # 检查资源约束
        if self._check_resource_constraints(task_context):
            trigger_reasons.append('resource_constraints')
        
        # 检查超时风险
        if self._check_timeout_risk(task_context):
            trigger_reasons.append('timeout_risk')
        
        # 检查业务规则违反
        if self._check_business_rule_violation(task_context):
            trigger_reasons.append('business_rule_violation')
        
        # 检查意外状态
        if self._check_unexpected_state(task_context):
            trigger_reasons.append('unexpected_state')
        
        # 决策逻辑：满足任一高优先级条件或满足多个低优先级条件
        high_priority_triggers = [
            'conflicting_validations',
            'business_rule_violation',
            'unexpected_state'
        ]
        
        low_priority_triggers = [
            'low_confidence',
            'ambiguous_state',
            'resource_constraints',
            'timeout_risk'
        ]
        
        # 检查高优先级条件
        for trigger in high_priority_triggers:
            if trigger in trigger_reasons:
                self.logger.info(f"High priority trigger activated: {trigger}")
                return True, trigger_reasons
        
        # 检查低优先级条件：至少满足 2 个
        low_priority_count = sum(1 for trigger in low_priority_triggers 
                                if trigger in trigger_reasons)
        
        if low_priority_count >= 2:
            self.logger.info(f"Multiple low priority triggers activated: {low_priority_count}")
            return True, trigger_reasons
        
        return False, trigger_reasons
    
    def _check_low_confidence(self, task_context: Dict[str, Any]) -> bool:
        """检查低置信度"""
        validation_results = task_context.get('validation_results', {})
        
        if not validation_results:
            return False
        
        # 检查所有验证结果的置信度
        for strategy, result in validation_results.items():
            if isinstance(result, dict):
                confidence = result.get('confidence', 1.0)
                if confidence < self.thresholds['confidence_threshold']:
                    self.logger.debug(f"Low confidence detected in {strategy}: {confidence}")
                    return True
        
        return False
    
    def _check_conflicting_validations(self, task_context: Dict[str, Any]) -> bool:
        """检查验证冲突"""
        validation_results = task_context.get('validation_results', {})
        
        if not validation_results:
            return False
        
        # 检查是否有冲突的完成状态
        completed_states = []
        for strategy, result in validation_results.items():
            if isinstance(result, dict):
                completed_states.append(result.get('completed', False))
        
        # 如果既有完成又有未完成，认为有冲突
        if len(completed_states) >= self.thresholds['conflict_threshold']:
            if True in completed_states and False in completed_states:
                self.logger.warning("Conflicting validation results detected")
                return True
        
        return False
    
    def _check_ambiguous_state(self, task_context: Dict[str, Any]) -> bool:
        """检查模糊状态"""
        # 检查界面变化率是否在模糊范围内
        change_rate = task_context.get('change_rate', 1.0)
        
        # 变化率在 0.1-0.3 之间认为是模糊状态
        if 0.1 <= change_rate <= 0.3:
            self.logger.debug(f"Ambiguous state detected: change_rate={change_rate}")
            return True
        
        return False
    
    def _check_resource_constraints(self, task_context: Dict[str, Any]) -> bool:
        """检查资源约束"""
        # 检查迭代次数是否接近上限
        iteration_count = task_context.get('iteration_count', 0)
        max_iterations = task_context.get('max_iterations', 20)
        
        if max_iterations > 0 and iteration_count / max_iterations > self.thresholds['resource_usage_threshold']:
            self.logger.warning(f"Resource constraint detected: {iteration_count}/{max_iterations} iterations")
            return True
        
        return False
    
    def _check_timeout_risk(self, task_context: Dict[str, Any]) -> bool:
        """检查超时风险"""
        execution_time = task_context.get('execution_time', 0)
        timeout_seconds = task_context.get('timeout_seconds', 300)
        
        if timeout_seconds > 0 and execution_time / timeout_seconds > self.thresholds['timeout_risk_threshold']:
            self.logger.warning(f"Timeout risk detected: {execution_time}/{timeout_seconds} seconds")
            return True
        
        return False
    
    def _check_business_rule_violation(self, task_context: Dict[str, Any]) -> bool:
        """检查业务规则违反"""
        # TODO: 实现业务规则违反检查
        return False
    
    def _check_unexpected_state(self, task_context: Dict[str, Any]) -> bool:
        """检查意外状态"""
        # TODO: 实现意外状态检查
        return False


class DecisionRequestGenerator:
    """决策请求生成器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("DecisionRequestGenerator")
    
    def create_decision_request(self, task_context: Dict[str, Any], 
                              trigger_reasons: List[str]) -> DecisionRequest:
        """创建详细的决策请求"""
        
        # 收集决策上下文信息
        decision_context = self._collect_decision_context(task_context)
        
        # 生成推荐选项
        recommended_options = self._generate_recommendations(task_context, trigger_reasons)
        
        # 评估紧急程度
        urgency_level = self._assess_urgency(task_context, trigger_reasons)
        
        # 创建上下文快照
        context_snapshot = self._create_context_snapshot(task_context)
        
        return DecisionRequest(
            task_id=task_context.get('task_id', 'unknown'),
            current_state=decision_context['current_state'],
            validation_results=decision_context['validation_results'],
            uncertainty_factors=trigger_reasons,
            recommended_options=recommended_options,
            urgency_level=urgency_level,
            context_snapshot=context_snapshot
        )
    
    def _collect_decision_context(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """收集决策上下文"""
        return {
            'current_state': {
                'task_id': task_context.get('task_id'),
                'current_phase': task_context.get('current_phase'),
                'iteration_count': task_context.get('iteration_count', 0),
                'execution_time': task_context.get('execution_time', 0),
                'device_info': task_context.get('device_info', {})
            },
            'validation_results': task_context.get('validation_results', {})
        }
    
    def _generate_recommendations(self, task_context: Dict[str, Any], 
                                trigger_reasons: List[str]) -> List[DecisionOption]:
        """生成推荐决策选项"""
        options = []
        
        # 基于触发原因生成不同的推荐选项
        if 'conflicting_validations' in trigger_reasons:
            options.extend([
                DecisionOption(
                    id="continue_with_vlm",
                    action="continue_execution",
                    parameters={"validation_strategy": "trust_vlm"},
                    confidence=0.6,
                    rationale="VLM 可能看到客户端未检测到的细节"
                ),
                DecisionOption(
                    id="continue_with_client",
                    action="continue_execution",
                    parameters={"validation_strategy": "trust_client"},
                    confidence=0.7,
                    rationale="客户端验证通常更可靠"
                ),
                DecisionOption(
                    id="skip_and_continue",
                    action="skip_task",
                    parameters={"skip_reason": "validation_conflict"},
                    confidence=0.8,
                    rationale="避免在冲突状态下继续执行"
                )
            ])
        
        if 'low_confidence' in trigger_reasons:
            options.extend([
                DecisionOption(
                    id="retry_with_different_approach",
                    action="retry_with_modifications",
                    parameters={"approach": "different_strategy"},
                    confidence=0.65,
                    rationale="尝试不同的执行策略可能提高成功率"
                ),
                DecisionOption(
                    id="pause_for_review",
                    action="pause_execution",
                    parameters={"review_type": "human_review"},
                    confidence=0.9,
                    rationale="需要人工介入确认当前状态"
                )
            ])
        
        if 'timeout_risk' in trigger_reasons:
            options.append(DecisionOption(
                id="skip_to_avoid_timeout",
                action="skip_task",
                parameters={"skip_reason": "timeout_risk"},
                confidence=0.85,
                rationale="为避免超时，建议跳过当前任务"
            ))
        
        # 添加默认选项
        options.append(DecisionOption(
            id="default_continue",
            action="continue_execution",
            parameters={},
            confidence=0.5,
            rationale="继续执行，但风险较高"
        ))
        
        return options
    
    def _assess_urgency(self, task_context: Dict[str, Any], 
                        trigger_reasons: List[str]) -> str:
        """评估决策紧急程度"""
        urgency_score = 0
        
        # 基于触发原因计算紧急程度
        urgency_factors = {
            'timeout_risk': 0.8,
            'resource_constraints': 0.6,
            'business_rule_violation': 0.9,
            'unexpected_state': 0.7,
            'conflicting_validations': 0.5,
            'low_confidence': 0.4,
            'ambiguous_state': 0.3
        }
        
        for reason in trigger_reasons:
            urgency_score += urgency_factors.get(reason, 0.2)
        
        # 基于任务状态调整紧急程度
        if task_context.get('iteration_count', 0) > 15:
            urgency_score += 0.3
        
        if task_context.get('execution_time', 0) > 200:
            urgency_score += 0.4
        
        # 确定紧急级别
        if urgency_score >= 1.5:
            return UrgencyLevel.CRITICAL.value
        elif urgency_score >= 1.0:
            return UrgencyLevel.HIGH.value
        elif urgency_score >= 0.5:
            return UrgencyLevel.MEDIUM.value
        else:
            return UrgencyLevel.LOW.value
    
    def _create_context_snapshot(self, task_context: Dict[str, Any]) -> bytes:
        """创建上下文快照"""
        # 序列化上下文为 JSON
        snapshot_data = {
            'task_id': task_context.get('task_id'),
            'current_phase': task_context.get('current_phase'),
            'iteration_count': task_context.get('iteration_count'),
            'execution_time': task_context.get('execution_time'),
            'task_variables': task_context.get('task_variables', {}),
            'validation_results': task_context.get('validation_results', {}),
            'timestamp': time.time()
        }
        
        return json.dumps(snapshot_data, ensure_ascii=False).encode('utf-8')


class DecisionResponseProcessor:
    """决策响应处理器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("DecisionResponseProcessor")
        self.decision_log = []
    
    def process_decision_response(self, decision_response: DecisionResponse, 
                                task_context: Dict[str, Any]) -> ExecutionDirective:
        """处理主任务的决策响应"""
        
        # 记录决策
        self._log_decision(decision_response, task_context)
        
        # 验证决策有效性
        if not self._validate_decision(decision_response, task_context):
            return self._create_fallback_directive(task_context)
        
        # 执行对应的处理逻辑
        action_handlers = {
            'continue_execution': self._handle_continue,
            'skip_task': self._handle_skip,
            'retry_with_modifications': self._handle_retry,
            'pause_execution': self._handle_pause,
            'terminate_chain': self._handle_terminate
        }
        
        handler = action_handlers.get(decision_response.action)
        if handler:
            return handler(decision_response, task_context)
        else:
            return self._create_fallback_directive(task_context)
    
    def _handle_continue(self, decision_response: DecisionResponse,
                        task_context: Dict[str, Any]) -> ExecutionDirective:
        """处理继续执行决策"""
        parameters = decision_response.parameters or {}
        
        return ExecutionDirective(
            action="continue",
            parameters={
                "validation_strategy": parameters.get('validation_strategy'),
                "max_additional_iterations": parameters.get('max_iterations', 10),
                "monitoring_intensity": parameters.get('monitoring_level', 'high')
            },
            priority=1,
            timeout=parameters.get('timeout', 60),
            metadata={
                "decision_source": "master",
                "decision_id": decision_response.decision_id,
                "applied_parameters": parameters
            }
        )
    
    def _handle_skip(self, decision_response: DecisionResponse,
                    task_context: Dict[str, Any]) -> ExecutionDirective:
        """处理跳过任务决策"""
        skip_reason = decision_response.parameters.get('skip_reason', 'decision_based_skip') if decision_response.parameters else 'decision_based_skip'
        
        return ExecutionDirective(
            action="skip",
            parameters={
                "skip_reason": skip_reason,
                "mark_as_completed": decision_response.parameters.get('mark_completed', False) if decision_response.parameters else False
            },
            priority=10,
            metadata={
                "decision_source": "master",
                "decision_id": decision_response.decision_id,
                "skip_justification": decision_response.rationale
            }
        )
    
    def _handle_retry(self, decision_response: DecisionResponse,
                     task_context: Dict[str, Any]) -> ExecutionDirective:
        """处理重试决策"""
        retry_parameters = decision_response.parameters or {}
        
        return ExecutionDirective(
            action="retry",
            parameters={
                "retry_count": task_context.get('retry_count', 0) + 1,
                "max_retries": retry_parameters.get('max_retries', 3),
                "approach": retry_parameters.get('approach', 'default')
            },
            priority=5,
            timeout=retry_parameters.get('timeout', 120),
            metadata={
                "decision_source": "master",
                "decision_id": decision_response.decision_id,
                "retry_changes": retry_parameters
            }
        )
    
    def _handle_pause(self, decision_response: DecisionResponse,
                     task_context: Dict[str, Any]) -> ExecutionDirective:
        """处理暂停决策"""
        return ExecutionDirective(
            action="pause",
            parameters={
                "pause_reason": decision_response.rationale,
                "review_type": decision_response.parameters.get('review_type', 'human') if decision_response.parameters else 'human'
            },
            priority=15,
            metadata={
                "decision_source": "master",
                "decision_id": decision_response.decision_id
            }
        )
    
    def _handle_terminate(self, decision_response: DecisionResponse,
                         task_context: Dict[str, Any]) -> ExecutionDirective:
        """处理终止决策"""
        return ExecutionDirective(
            action="terminate",
            parameters={
                "terminate_reason": decision_response.rationale
            },
            priority=20,
            metadata={
                "decision_source": "master",
                "decision_id": decision_response.decision_id
            }
        )
    
    def _create_fallback_directive(self, task_context: Dict[str, Any]) -> ExecutionDirective:
        """创建降级决策指令"""
        # 基于任务状态选择最安全的降级策略
        if task_context.get('iteration_count', 0) > 15:
            return ExecutionDirective(
                action="skip",
                parameters={
                    "skip_reason": "fallback_after_excessive_iterations",
                    "mark_as_completed": False
                },
                priority=8,
                metadata={"fallback_reason": "excessive_iterations"}
            )
        elif task_context.get('execution_time', 0) > 150:
            return ExecutionDirective(
                action="skip",
                parameters={
                    "skip_reason": "fallback_after_timeout_risk",
                    "mark_as_completed": False
                },
                priority=7,
                metadata={"fallback_reason": "timeout_risk"}
            )
        else:
            return ExecutionDirective(
                action="continue",
                parameters={
                    "validation_strategy": "conservative",
                    "max_additional_iterations": 5,
                    "monitoring_intensity": "very_high"
                },
                priority=3,
                timeout=30,
                metadata={"fallback_reason": "default_continue"}
            )
    
    def _validate_decision(self, decision_response: DecisionResponse,
                          task_context: Dict[str, Any]) -> bool:
        """验证决策有效性"""
        # 检查决策 ID
        if not decision_response.decision_id:
            self.logger.error("Invalid decision: missing decision_id")
            return False
        
        # 检查动作
        if not decision_response.action:
            self.logger.error("Invalid decision: missing action")
            return False
        
        # 检查置信度
        if decision_response.confidence < 0.3:
            self.logger.warning(f"Low confidence decision: {decision_response.confidence}")
            # 低置信度但不一定无效
        
        return True
    
    def _log_decision(self, decision_response: DecisionResponse,
                     task_context: Dict[str, Any]):
        """记录决策"""
        log_entry = {
            'timestamp': time.time(),
            'task_id': task_context.get('task_id'),
            'decision_id': decision_response.decision_id,
            'action': decision_response.action,
            'confidence': decision_response.confidence,
            'source': decision_response.source
        }
        
        self.decision_log.append(log_entry)
        self.logger.info(f"Decision logged: {log_entry}")


class DecisionCoordinator:
    """决策协调器 - 统一管理决策转回流程"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("DecisionCoordinator")
        
        # 初始化组件
        self.trigger = DecisionDelegationTrigger(self.logger)
        self.request_generator = DecisionRequestGenerator(self.logger)
        self.response_processor = DecisionResponseProcessor(self.logger)
        
        # 决策缓存
        self.decision_cache = {}
    
    def should_delegate_decision(self, task_context: Dict[str, Any]) -> tuple:
        """判断是否需要决策转回"""
        return self.trigger.should_delegate_decision(task_context)
    
    def create_decision_request(self, task_context: Dict[str, Any],
                               trigger_reasons: List[str]) -> DecisionRequest:
        """创建决策请求"""
        return self.request_generator.create_decision_request(task_context, trigger_reasons)
    
    def process_decision_response(self, decision_response: DecisionResponse,
                                 task_context: Dict[str, Any]) -> ExecutionDirective:
        """处理决策响应"""
        return self.response_processor.process_decision_response(decision_response, task_context)
    
    def make_autonomous_decision(self, task_context: Dict[str, Any]) -> ExecutionDirective:
        """自主决策（无需转回）"""
        # 基于验证结果进行自主决策
        validation_results = task_context.get('validation_results', {})
        
        # 如果所有验证都通过，继续执行
        if all(r.get('completed', False) for r in validation_results.values() if isinstance(r, dict)):
            return ExecutionDirective(
                action="continue",
                parameters={"validation_strategy": "all_passed"},
                priority=1,
                metadata={"decision_source": "autonomous"}
            )
        
        # 如果置信度足够高，继续执行
        confidences = [r.get('confidence', 0) for r in validation_results.values() if isinstance(r, dict)]
        if confidences and sum(confidences) / len(confidences) >= 0.7:
            return ExecutionDirective(
                action="continue",
                parameters={"validation_strategy": "high_confidence"},
                priority=1,
                metadata={"decision_source": "autonomous"}
            )
        
        # 否则选择保守策略
        return ExecutionDirective(
            action="continue",
            parameters={
                "validation_strategy": "conservative",
                "max_additional_iterations": 5
            },
            priority=2,
            metadata={"decision_source": "autonomous_conservative"}
        )
