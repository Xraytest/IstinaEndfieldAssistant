"""
GPU检测模块 - 检测NVIDIA显卡配置和CUDA可用性
"""
import os
import sys
import subprocess
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

# 添加项目根目录到路径
if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from core.logger import get_logger, LogCategory
    logger = get_logger()
except ImportError:
    import logging
    logger = logging.getLogger("GPUChecker")
    # 创建LogCategory的替代
    class LogCategory:
        MAIN = "main"


@dataclass
class GPUInfo:
    """GPU信息数据类"""
    name: str = ""
    total_memory_gb: float = 0.0
    free_memory_gb: float = 0.0
    compute_capability: str = ""
    driver_version: str = ""
    cuda_version: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "total_memory_gb": self.total_memory_gb,
            "free_memory_gb": self.free_memory_gb,
            "compute_capability": self.compute_capability,
            "driver_version": self.driver_version,
            "cuda_version": self.cuda_version,
        }


class GPUChecker:
    """
    显卡检测器 - 检测NVIDIA显卡配置
    
    职责:
    1. 检测CUDA可用性
    2. 获取显卡显存信息
    3. 判断是否满足本地推理要求
    4. 推荐合适的模型
    """
    
    MIN_MEMORY_GB = 16  # 最低显存要求(GB)
    MIN_CUDA_VERSION = "12.0"  # 最低CUDA版本要求
    
    # 模型推荐配置
    MODEL_RECOMMENDATIONS = {
        24: "qwen3.5-35b-a3b-fp16",  # 24GB+ 推荐35B模型
        16: "qwen3.5-9b-fp16",       # 16GB+ 推荐9B模型
        8: "qwen3.5-0.6b-q8_0",      # 8GB+ 推荐0.6B模型
    }
    
    def __init__(self):
        self._gpu_info: List[GPUInfo] = []
        self._cuda_available: bool = False
        self._cuda_version: str = ""
        self._driver_version: str = ""
        self._checked: bool = False
        
    def check_gpu_availability(self) -> Dict[str, Any]:
        """
        检查GPU可用性
        
        Returns:
            {
                "available": bool,
                "cuda_available": bool,
                "cuda_version": str,
                "driver_version": str,
                "gpu_count": int,
                "gpus": [],
                "meets_requirements": bool,
                "recommended_model": str | None,
                "error": str | None
            }
        """
        result = {
            "available": False,
            "cuda_available": False,
            "cuda_version": "",
            "driver_version": "",
            "gpu_count": 0,
            "gpus": [],
            "meets_requirements": False,
            "recommended_model": None,
            "error": None
        }
        
        try:
            # 方法1: 尝试使用nvidia-ml-py或pynvml
            nvml_result = self._check_via_nvml()
            if nvml_result["available"]:
                result.update(nvml_result)
                self._checked = True
                return result
                
            # 方法2: 尝试使用torch
            torch_result = self._check_via_torch()
            if torch_result["available"]:
                result.update(torch_result)
                self._checked = True
                return result
                
            # 方法3: 尝试使用nvidia-smi命令
            nvidia_smi_result = self._check_via_nvidia_smi()
            if nvidia_smi_result["available"]:
                result.update(nvidia_smi_result)
                self._checked = True
                return result
                
            # 没有检测到NVIDIA GPU
            result["error"] = "未检测到NVIDIA GPU或CUDA环境"
            logger.warning("GPU检测: 未检测到NVIDIA GPU")
            
        except Exception as e:
            result["error"] = f"GPU检测失败: {str(e)}"
            logger.exception("GPU检测异常: %s", str(e))
        
        self._checked = True
        return result
    
    def _check_via_nvml(self) -> Dict[str, Any]:
        """通过NVML检查GPU"""
        result = {
            "available": False,
            "cuda_available": False,
            "cuda_version": "",
            "driver_version": "",
            "gpu_count": 0,
            "gpus": [],
            "meets_requirements": False,
            "recommended_model": None,
        }
        
        try:
            # 尝试导入pynvml
            from pynvml import nvmlInit, nvmlShutdown, nvmlDeviceGetCount, \
                nvmlDeviceGetHandleByIndex, nvmlDeviceGetName, nvmlDeviceGetMemoryInfo, \
                nvmlDeviceGetCudaComputeCapability, nvmlSystemGetDriverVersion
            
            nvmlInit()
            result["cuda_available"] = True
            
            # 获取驱动版本
            try:
                result["driver_version"] = nvmlSystemGetDriverVersion().decode('utf-8')
            except:
                pass
            
            # 获取GPU数量
            gpu_count = nvmlDeviceGetCount()
            result["gpu_count"] = gpu_count
            
            gpus = []
            max_memory = 0
            
            for i in range(gpu_count):
                handle = nvmlDeviceGetHandleByIndex(i)
                
                # 获取GPU名称
                try:
                    name = nvmlDeviceGetName(handle).decode('utf-8')
                except:
                    name = f"GPU {i}"
                
                # 获取显存信息
                try:
                    mem_info = nvmlDeviceGetMemoryInfo(handle)
                    total_gb = mem_info.total / (1024**3)
                    free_gb = (mem_info.total - mem_info.used) / (1024**3)
                except:
                    total_gb = 0
                    free_gb = 0
                
                # 获取计算能力
                try:
                    major, minor = nvmlDeviceGetCudaComputeCapability(handle)
                    compute_capability = f"{major}.{minor}"
                except:
                    compute_capability = ""
                
                gpu_info = GPUInfo(
                    name=name,
                    total_memory_gb=round(total_gb, 2),
                    free_memory_gb=round(free_gb, 2),
                    compute_capability=compute_capability,
                    driver_version=result["driver_version"],
                    cuda_version=result["cuda_version"]
                )
                gpus.append(gpu_info)
                
                if total_gb > max_memory:
                    max_memory = total_gb
            
            nvmlShutdown()
            
            result["gpus"] = [g.to_dict() for g in gpus]
            result["available"] = True
            result["meets_requirements"] = max_memory >= self.MIN_MEMORY_GB
            result["recommended_model"] = self._get_recommended_model(max_memory)
            
            logger.info("GPU检测(NVML)成功: gpu_count=%d, max_memory=%.2fGB", 
                       gpu_count, max_memory)
            
        except ImportError:
            logger.debug(LogCategory.MAIN, "pynvml未安装，跳过NVML检测")
        except Exception as e:
            logger.debug(LogCategory.MAIN, f"NVML检测失败: {str(e)}")
        
        return result
    
    def _check_via_torch(self) -> Dict[str, Any]:
        """通过PyTorch检查GPU"""
        result = {
            "available": False,
            "cuda_available": False,
            "cuda_version": "",
            "driver_version": "",
            "gpu_count": 0,
            "gpus": [],
            "meets_requirements": False,
            "recommended_model": None,
        }
        
        try:
            import torch
            
            if not torch.cuda.is_available():
                logger.debug(LogCategory.MAIN, "PyTorch CUDA不可用")
                return result
            
            result["cuda_available"] = True
            
            # 获取CUDA版本
            try:
                result["cuda_version"] = torch.version.cuda or ""
            except:
                pass
            
            # 获取GPU数量
            gpu_count = torch.cuda.device_count()
            result["gpu_count"] = gpu_count
            
            gpus = []
            max_memory = 0
            
            for i in range(gpu_count):
                props = torch.cuda.get_device_properties(i)
                
                # 获取显存信息
                total_bytes = props.total_memory
                allocated_bytes = torch.cuda.memory_allocated(i)
                
                total_gb = total_bytes / (1024**3)
                free_gb = (total_bytes - allocated_bytes) / (1024**3)
                
                gpu_info = GPUInfo(
                    name=props.name,
                    total_memory_gb=round(total_gb, 2),
                    free_memory_gb=round(free_gb, 2),
                    compute_capability=f"{props.major}.{props.minor}",
                    driver_version=result["driver_version"],
                    cuda_version=result["cuda_version"]
                )
                gpus.append(gpu_info)
                
                if total_gb > max_memory:
                    max_memory = total_gb
            
            result["gpus"] = [g.to_dict() for g in gpus]
            result["available"] = True
            result["meets_requirements"] = max_memory >= self.MIN_MEMORY_GB
            result["recommended_model"] = self._get_recommended_model(max_memory)
            
            logger.info("GPU检测(PyTorch)成功: gpu_count=%d, max_memory=%.2fGB", 
                       gpu_count, max_memory)
            
        except ImportError:
            logger.debug(LogCategory.MAIN, "PyTorch未安装，跳过PyTorch检测")
        except Exception as e:
            logger.debug(LogCategory.MAIN, f"PyTorch检测失败: {str(e)}")
        
        return result
    
    def _check_via_nvidia_smi(self) -> Dict[str, Any]:
        """通过nvidia-smi命令检查GPU"""
        result = {
            "available": False,
            "cuda_available": False,
            "cuda_version": "",
            "driver_version": "",
            "gpu_count": 0,
            "gpus": [],
            "meets_requirements": False,
            "recommended_model": None,
        }
        
        try:
            # 运行nvidia-smi命令
            output = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,memory.used,compute_cap", 
                 "--format=csv,noheader"],
                universal_newlines=True,
                stderr=subprocess.DEVNULL
            )
            
            # 获取驱动版本
            try:
                driver_output = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                    universal_newlines=True,
                    stderr=subprocess.DEVNULL
                )
                result["driver_version"] = driver_output.strip().split('\n')[0]
            except:
                pass
            
            gpus = []
            max_memory = 0
            
            for line in output.strip().split('\n'):
                if not line:
                    continue
                    
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 5:
                    name = parts[0]
                    # 解析显存 (格式: "16384 MiB")
                    total_str = parts[1].replace('MiB', '').strip()
                    free_str = parts[2].replace('MiB', '').strip()
                    
                    try:
                        total_gb = int(total_str) / 1024
                        free_gb = int(free_str) / 1024
                    except:
                        total_gb = 0
                        free_gb = 0
                    
                    compute_cap = parts[4]
                    
                    gpu_info = GPUInfo(
                        name=name,
                        total_memory_gb=round(total_gb, 2),
                        free_memory_gb=round(free_gb, 2),
                        compute_capability=compute_cap,
                        driver_version=result["driver_version"],
                        cuda_version=result["cuda_version"]
                    )
                    gpus.append(gpu_info)
                    
                    if total_gb > max_memory:
                        max_memory = total_gb
            
            result["gpu_count"] = len(gpus)
            result["gpus"] = [g.to_dict() for g in gpus]
            result["available"] = True
            result["cuda_available"] = True
            result["meets_requirements"] = max_memory >= self.MIN_MEMORY_GB
            result["recommended_model"] = self._get_recommended_model(max_memory)
            
            logger.info("GPU检测(nvidia-smi)成功: gpu_count=%d, max_memory=%.2fGB", 
                       len(gpus), max_memory)
            
        except FileNotFoundError:
            logger.debug(LogCategory.MAIN, "nvidia-smi命令未找到")
        except Exception as e:
            logger.debug(LogCategory.MAIN, f"nvidia-smi检测失败: {str(e)}")
        
        return result
    
    def _get_recommended_model(self, memory_gb: float) -> Optional[str]:
        """根据显存大小推荐模型"""
        for min_mem, model in sorted(self.MODEL_RECOMMENDATIONS.items(), reverse=True):
            if memory_gb >= min_mem:
                return model
        return None
    
    def get_gpu_info(self) -> List[GPUInfo]:
        """获取GPU信息列表"""
        return self._gpu_info
    
    def is_cuda_available(self) -> bool:
        """检查CUDA是否可用"""
        return self._cuda_available
    
    def get_cuda_version(self) -> str:
        """获取CUDA版本"""
        return self._cuda_version
    
    def meets_requirements(self) -> bool:
        """检查是否满足最低要求"""
        if not self._checked:
            self.check_gpu_availability()
        
        if not self._gpu_info:
            return False
        
        max_memory = max(gpu.total_memory_gb for gpu in self._gpu_info)
        return max_memory >= self.MIN_MEMORY_GB
    
    def get_recommended_model(self) -> Optional[str]:
        """获取推荐的模型"""
        if not self._checked:
            result = self.check_gpu_availability()
            return result.get("recommended_model")
        
        if not self._gpu_info:
            return None
        
        max_memory = max(gpu.total_memory_gb for gpu in self._gpu_info)
        return self._get_recommended_model(max_memory)


# 便捷函数
def check_gpu() -> Dict[str, Any]:
    """快速检查GPU可用性"""
    checker = GPUChecker()
    return checker.check_gpu_availability()


def is_gpu_sufficient() -> bool:
    """检查GPU是否满足本地推理要求"""
    checker = GPUChecker()
    return checker.meets_requirements()


if __name__ == "__main__":
    # 测试GPU检测
    print("=" * 60)
    print("GPU检测测试")
    print("=" * 60)
    
    result = check_gpu()
    
    print(f"\n检测结果:")
    print(f"  可用: {result['available']}")
    print(f"  CUDA可用: {result['cuda_available']}")
    print(f"  CUDA版本: {result['cuda_version']}")
    print(f"  驱动版本: {result['driver_version']}")
    print(f"  GPU数量: {result['gpu_count']}")
    print(f"  满足要求: {result['meets_requirements']}")
    print(f"  推荐模型: {result['recommended_model']}")
    
    if result['gpus']:
        print(f"\nGPU详情:")
        for i, gpu in enumerate(result['gpus']):
            print(f"  GPU {i}:")
            print(f"    名称: {gpu['name']}")
            print(f"    总显存: {gpu['total_memory_gb']:.2f} GB")
            print(f"    可用显存: {gpu['free_memory_gb']:.2f} GB")
            print(f"    计算能力: {gpu['compute_capability']}")
    
    if result['error']:
        print(f"\n错误: {result['error']}")
    
    print("\n" + "=" * 60)
