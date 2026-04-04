import ctypes
import ctypes.util
import json
import os
import pathlib
import platform
from typing import Optional, Union
from .utils import JSON, InstanceOptionType, StaticOptionType

class Asst:
    CallBackType = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)
    '\n    回调函数，使用实例可参照 my_callback\n\n    :params:\n        ``param1 message``: 消息类型\n        ``param2 details``: json string\n        ``param3 arg``:     自定义参数\n    '

    @staticmethod
    def load(path: Union[pathlib.Path, str], incremental_path: Optional[Union[pathlib.Path, str]]=None, user_dir: Optional[Union[pathlib.Path, str]]=None) -> bool:
        platform_values = {'windows': {'libpath': 'MaaCore.dll', 'environ_var': 'PATH'}, 'darwin': {'libpath': 'libMaaCore.dylib', 'environ_var': 'DYLD_LIBRARY_PATH'}, 'linux': {'libpath': 'libMaaCore.so', 'environ_var': 'LD_LIBRARY_PATH'}}
        lib_import_func = None
        platform_type = platform.system().lower()
        if platform_type == 'windows':
            lib_import_func = ctypes.WinDLL
        else:
            lib_import_func = ctypes.CDLL
        Asst.__libpath = pathlib.Path(path) / platform_values[platform_type]['libpath']
        try:
            os.environ[platform_values[platform_type]['environ_var']] += os.pathsep + str(path)
        except KeyError:
            os.environ[platform_values[platform_type]['environ_var']] = os.pathsep + str(path)
        try:
            Asst.__lib = lib_import_func(str(Asst.__libpath))
        except OSError:
            Asst.__libpath = ctypes.util.find_library('MaaCore')
            Asst.__lib = lib_import_func(str(Asst.__libpath))
        Asst.__set_lib_properties()
        ret: bool = True
        if user_dir:
            ret &= Asst.__lib.AsstSetUserDir(str(user_dir).encode('utf-8'))
        ret &= Asst.__lib.AsstLoadResource(str(path).encode('utf-8'))
        if incremental_path:
            ret &= Asst.__lib.AsstLoadResource(str(incremental_path).encode('utf-8'))
        return ret

    def __init__(self, callback: CallBackType=None, arg=None):
        self.__callback = callback
        if callback:
            self.__ptr = Asst.__lib.AsstCreateEx(callback, arg)
        else:
            self.__ptr = Asst.__lib.AsstCreate()

    def __del__(self):
        Asst.__lib.AsstDestroy(self.__ptr)
        self.__ptr = None

    def set_instance_option(self, option_type: InstanceOptionType, option_value: str):
        return Asst.__lib.AsstSetInstanceOption(self.__ptr, int(option_type), option_value.encode('utf-8'))

    def set_static_option(option_type: StaticOptionType, option_value: str):
        return Asst.__lib.AsstSetStaticOption(int(option_type), option_value.encode('utf-8'))

    def connect(self, adb_path: str, address: str, config: str='General'):
        return Asst.__lib.AsstConnect(self.__ptr, adb_path.encode('utf-8'), address.encode('utf-8'), config.encode('utf-8'))

    def get_image(self, size: int) -> bytes | None:
        buffer_type = ctypes.c_byte * size
        buffer = buffer_type()
        buffer.value = b'\x00' * size
        if (got := Asst.__lib.AsstGetImage(self.__ptr, buffer, size)) and got > 0:
            return bytes(buffer)
        else:
            return None

    def set_connection_extras(name: str, extras: JSON):
        Asst.__lib.AsstSetConnectionExtras(name.encode('utf-8'), json.dumps(extras, ensure_ascii=False).encode('utf-8'))
    TaskId = int

    def append_task(self, type_name: str, params: JSON={}) -> TaskId:
        return Asst.__lib.AsstAppendTask(self.__ptr, type_name.encode('utf-8'), json.dumps(params, ensure_ascii=False).encode('utf-8'))

    def set_task_params(self, task_id: TaskId, params: JSON) -> bool:
        return Asst.__lib.AsstSetTaskParams(self.__ptr, task_id, json.dumps(params, ensure_ascii=False).encode('utf-8'))

    def start(self) -> bool:
        return Asst.__lib.AsstStart(self.__ptr)

    def stop(self) -> bool:
        return Asst.__lib.AsstStop(self.__ptr)

    def running(self) -> bool:
        return Asst.__lib.AsstRunning(self.__ptr)

    @staticmethod
    def log(level: str, message: str) -> None:
        Asst.__lib.AsstLog(level.encode('utf-8'), message.encode('utf-8'))

    def get_version(self) -> str:
        return Asst.__lib.AsstGetVersion().decode('utf-8')

    @staticmethod
    def __set_lib_properties():
        Asst.__lib.AsstSetUserDir.restype = ctypes.c_bool
        Asst.__lib.AsstSetUserDir.argtypes = (ctypes.c_char_p,)
        Asst.__lib.AsstLoadResource.restype = ctypes.c_bool
        Asst.__lib.AsstLoadResource.argtypes = (ctypes.c_char_p,)
        Asst.__lib.AsstSetStaticOption.restype = ctypes.c_bool
        Asst.__lib.AsstSetStaticOption.argtypes = (ctypes.c_int, ctypes.c_char_p)
        Asst.__lib.AsstSetConnectionExtras.restype = ctypes.c_void_p
        Asst.__lib.AsstSetConnectionExtras.argtypes = (ctypes.c_char_p, ctypes.c_char_p)
        Asst.__lib.AsstGetImage.restype = ctypes.c_uint64
        Asst.__lib.AsstGetImage.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64)
        Asst.__lib.AsstCreate.restype = ctypes.c_void_p
        Asst.__lib.AsstCreate.argtypes = ()
        Asst.__lib.AsstCreateEx.restype = ctypes.c_void_p
        Asst.__lib.AsstCreateEx.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
        Asst.__lib.AsstDestroy.argtypes = (ctypes.c_void_p,)
        Asst.__lib.AsstSetInstanceOption.restype = ctypes.c_bool
        Asst.__lib.AsstSetInstanceOption.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p)
        Asst.__lib.AsstConnect.restype = ctypes.c_bool
        Asst.__lib.AsstConnect.argtypes = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p)
        Asst.__lib.AsstAsyncConnect.restype = ctypes.c_int
        Asst.__lib.AsstAsyncConnect.argtypes = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_bool)
        Asst.__lib.AsstAppendTask.restype = ctypes.c_int
        Asst.__lib.AsstAppendTask.argtypes = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p)
        Asst.__lib.AsstSetTaskParams.restype = ctypes.c_bool
        Asst.__lib.AsstSetTaskParams.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p)
        Asst.__lib.AsstStart.restype = ctypes.c_bool
        Asst.__lib.AsstStart.argtypes = (ctypes.c_void_p,)
        Asst.__lib.AsstStop.restype = ctypes.c_bool
        Asst.__lib.AsstStop.argtypes = (ctypes.c_void_p,)
        Asst.__lib.AsstRunning.restype = ctypes.c_bool
        Asst.__lib.AsstRunning.argtypes = (ctypes.c_void_p,)
        Asst.__lib.AsstGetVersion.restype = ctypes.c_char_p
        Asst.__lib.AsstLog.restype = None
        Asst.__lib.AsstLog.argtypes = (ctypes.c_char_p, ctypes.c_char_p)