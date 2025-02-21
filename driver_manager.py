import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
import threading
import time
import os

class DriverManager:
    _driver = None  # 存储全局 driver 实例
    _monitor_thread = None  # 监控线程
    _stop_monitor = False  # 线程停止标志
    
    @classmethod
    def get_driver(cls):
        """ 获取全局 driver 实例，如果不存在则创建 """
        if cls._driver is None or not cls.is_driver_alive():
            chrome_options = Options()
            # 取消图片加载
            # chrome_options.add_argument("--blink-settings=imagesEnabled=false")
            # 禁用视频和插件
            # chrome_options.add_argument("--disable-web-security")
            # chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")

            # 启用性能日志
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

            # 创建 driver
            cls._driver = uc.Chrome(use_subprocess=True, version_main=128, options=chrome_options)
            cls._driver.implicitly_wait(10)

            # 启动浏览器监控线程
            cls._stop_monitor = False
            cls._monitor_thread = threading.Thread(target=cls._monitor_browser, daemon=True)
            cls._monitor_thread.start()

        return cls._driver

    @classmethod
    def is_driver_alive(cls):
        """ 检测 driver 是否存活 """
        return cls._driver is not None and cls._driver.service.process.poll() is None

    @classmethod
    def close_driver(cls):
        """ 关闭 driver 并停止监控线程 """
        if cls._driver:
            cls._driver.quit()
            cls._driver = None
            cls._stop_monitor = True  # 停止监控线程
        print("浏览器已关闭")

    @classmethod
    def _monitor_browser(cls):
        """ 后台线程监测 driver 是否关闭 """
        while not cls._stop_monitor:
            time.sleep(2)
            try:
                if cls._driver and cls._driver.service.process.poll() is not None:
                    print("检测到浏览器已关闭，强制退出")
                    os._exit(1)  # 终止 Python 进程
            except:
                pass
