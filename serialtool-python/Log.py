import logging
import os
import datetime

'''
    单例模式状态机变量
    使用单例模式(避免反复创建实例，用状态机来保证只使用一个实例就是单例模式)
    1. _instance:存储唯一实例
    2. _initialized: 是否初始化过

    self用于实例方法参数,cls用于类方法参数
    self修改实例,cls修改类
    用单例模式.我们始终返回唯一的实例,所以用cls直接处理类就行

    @classmethod是直接调用类的方法,而不是用于实例的方法
    要和cls配套使用,二者均是直接作用在类上

    __new__方法用于创建新实例,并返回实例的引用
    简单来说:new一个新对象

    new和init方法的区别
    1. new方法用于创建新实例,并返回实例的引用
    2. init方法用于初始化实例,并返回实例的引用

1. 我们这里用一个变量存储实例,并在new里进行检查:
    如果实例不存在,创建新实例,并更新状态机变量
    如果实例存在,直接返回实例的引用
    这里我们相当于就是一个init,只是用于实例检测的init,变量的init在Log_Config里进行
'''
class Logger:
    _instance=None
    _initialized=False
    _logger=None

    #检查是否存在实例，如果存在，更新状态机变量，否则创建新实例并更新状态机变量
    def __new__(cls):
        if cls._instance is None:
            cls._instance=super(Logger,cls).__new__(cls)
        # 确保实例能够访问类变量 _logger
        if hasattr(cls, '_logger'):
            cls._instance._logger = cls._logger
        return cls._instance

    # 初始化日志记录器
    @classmethod
    def __InitLogger__(cls, log_file=None, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',encoding='utf-8'):
        if not cls._initialized:
            try:
                # 处理 log_file 为 None 的情况
                if log_file is None:
                    # 默认日志文件路径
                    log_dir = os.path.join(os.getcwd(), 'logs')
                    if not os.path.exists(log_dir):
                        os.makedirs(log_dir)
                    log_file = os.path.join(log_dir, f'application_{datetime.datetime.now().strftime("%Y%m%d")}.log')
                else:
                    # 确保日志目录存在
                    log_dir = os.path.dirname(log_file)
                    if log_dir and not os.path.exists(log_dir):
                        os.makedirs(log_dir)
                
                #配置日志
                logging.basicConfig(
                    filename=log_file,
                    level=level,
                    format=format,
                    encoding=encoding
                    )
                #初始化日志记录器
                cls._logger = logging.getLogger(__name__)
                #更新状态机变量
                cls._initialized=True
            except Exception as e:
                print('初始化日志失败:', e)

    # 配置日志记录器
    @classmethod
    def Log_Config(cls,file_path=None,level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',encoding='utf-8'):
        cls.__InitLogger__(file_path,level,format,encoding)


    # 获取实例
    @classmethod
    def get_instance(cls):
        # 确保实例存在,如果不存在,创建新实例并更新状态机变量
        if cls._instance is None:
            cls._instance = cls()
        # 确保日志初始化过
        if not cls._initialized:
            cls.__InitLogger__()
        # 确保实例能够访问类变量 _logger
        if hasattr(cls, '_logger'):
            cls._instance._logger = cls._logger
        return cls._instance
            
    # 写入INFO日志记录
    def log_info(self,msg):
        if hasattr(self, '_logger') and self._logger:
            self._logger.info(msg)

    # 写入ERROR日志记录
    def log_error(self,msg):
        if hasattr(self, '_logger') and self._logger:
            self._logger.error(msg)
    
    # 写入WARNING日志记录
    def log_warning(self,msg):
        if hasattr(self, '_logger') and self._logger:
            self._logger.warning(msg)
    
    # 写入DEBUG日志记录
    def log_debug(self,msg):
        if hasattr(self, '_logger') and self._logger:
            self._logger.debug(msg)
    
    # 写入CRITICAL日志记录
    def log_critical(self,msg):
        if hasattr(self, '_logger') and self._logger:
            self._logger.critical(msg)