import logging



# 创建日志对象
global_logger = logging.getLogger("TranslaterLogger")
global_logger.setLevel(logging.DEBUG)
#输出到控制台
console_handler = logging.StreamHandler()
global_logger.addHandler(console_handler)