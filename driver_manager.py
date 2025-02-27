import undetected_chromedriver as uc
import chromedriver_autoinstaller
from selenium.webdriver.chrome.options import Options
import subprocess
import os
import logging

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

            # 手动指定 chromedriver 路径
            chrome_path = os.path.normpath(os.getenv('CHROM_PATH', ''))
            chromedriver_path = os.path.normpath(os.getenv('CHROMEDRIVER_PATH', ''))
            
            # 确保文件存在
            if not os.path.exists(chrome_path):
                logging.error(f"🔥 [ERROR] 找不到 chrome.exe 文件: {chrome_path}")
                logging.getLogger().handlers[0].flush()
                return None
            
            if not os.path.exists(chromedriver_path):
                logging.error(f"🔥 [ERROR] 找不到 chromedriver.exe 文件: {chromedriver_path}")
                logging.getLogger().handlers[0].flush()
                return None
            
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

            # 创建 driver
            cls._driver = uc.Chrome(browser_executable_path=chrome_path, driver_executable_path=chromedriver_path, use_subprocess=True, version_main=133, options=chrome_options)
            cls._driver.implicitly_wait(10)

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
