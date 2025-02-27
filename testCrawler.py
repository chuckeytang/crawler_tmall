from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
import subprocess
from selenium.webdriver.chrome.service import Service
# import chromedriver_autoinstaller
# chromedriver_path = chromedriver_autoinstaller.install()  

# 打印 chromedriver 路径
# print(f"🔥 [INFO] ChromeDriver 路径: {chromedriver_path}")

# 运行 chromedriver --version 命令
# version_output = subprocess.check_output([chromedriver_path, "--version"], text=True).strip()
# print(f"🚀 [INFO] 安装的 ChromeDriver 版本: {version_output}")
chrome_path = "/Applications/Google Chrome 121.app/Contents/MacOS/Google Chrome"
chromedriver_path = "/Users/jiaqitang/Documents/zj_project/crawler/老项目/IC交易网/chromedriver/121/chromedriver"

chrome_options = webdriver.ChromeOptions()
chrome_options.binary_location = chrome_path
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# 设置 ChromeDriver Service
service = Service(executable_path=chromedriver_path) # 指定 ChromeDriver 路径

driver = webdriver.Chrome(service=service, options=chrome_options)

driver.get("https://login.taobao.com/member/login.jhtml")
print("✅ 正常打开网页，等待 3600 秒...")
time.sleep(3600)

driver.close()
driver.quit()
