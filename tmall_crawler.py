import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import logging

import time
import random
import urllib.parse
import json
import os
import re

# 设置 Chrome 启动参数
chrome_options = Options()
# 禁用图片加载
# chrome_options.add_argument("--blink-settings=imagesEnabled=false")
# # 禁用视频和插件
# chrome_options.add_argument("--disable-web-security")
# chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")

# 启用性能日志
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = uc.Chrome(use_subprocess=True, version_main=128, options=chrome_options)
driver.implicitly_wait(10)

# 模拟键盘向下箭头键滚动页面
def keyboard_scroll(driver, num_of_scrolls, pause_time):
    for _ in range(num_of_scrolls):
        ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform()
        time.sleep(random.random()*(pause_time/2)+pause_time/2)

# 模拟鼠标滚轮滚动
def mouse_wheel_scroll(driver, num_of_scrolls, pause_time):
    body = driver.find_element_by_css_selector('body')
    for _ in range(num_of_scrolls):
        ActionChains(driver).move_to_element(body).click().send_keys(Keys.PAGE_DOWN).perform()
        time.sleep(random.random()*(pause_time/2)+pause_time/2)


# 加载已爬取商品ID的列表
def load_scraped_product_ids(filename="scraped_product_ids.txt"):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            scraped_ids = set(f.read().splitlines())
        return scraped_ids
    return set()

# 更新已爬取商品ID的列表
def update_scraped_product_ids(product_id, filename="scraped_product_ids.txt"):
    with open(filename, "a") as f:
        f.write(f"{product_id}\n")

# 保存商品信息到文件
def save_product_info(product_info, product_id):
    filename = f"product_info/{product_id}.json"
    os.makedirs("product_info", exist_ok=True)  # 确保目录存在
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(product_info, f, ensure_ascii=False, indent=4)
    print(f"商品信息已保存: {filename}")

def login_process():
    # 打开淘宝登录页面
    driver.get("https://login.taobao.com/member/login.jhtml")

    # 等待扫码登录成功后，用户名元素出现
    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[class^='myAccountName']"))
        )
        print("用户已登录，继续执行后续操作")
    except TimeoutException:
        print("等待登录超时，请手动完成登录")

def extract_product_info(driver, product_link):
    """
    进入商品详情页后，等待页面加载一段时间，再通过性能日志查找调用 mtop.taobao.pcdetail.data.get 的请求，
    解析返回的 JSONP 数据，并返回解析后的结果。
    """
    product_info = {
        "product_link": product_link,
        "data": None  # 最终保存接口返回的数据
    }

    # 等待页面加载并触发接口调用（根据实际情况调整等待时间）
    time.sleep(5)

    logs = driver.get_log("performance")
    for entry in logs:
        try:
            message = json.loads(entry["message"])["message"]
            # 筛选目标请求（可以根据 URL 中的特定关键词判断）
            if "Network.responseReceived" in message["method"]:
                response_url = message["params"]["response"]["url"]
                if "mtop.taobao.pcdetail.data.get" in response_url:
                    request_id = message["params"]["requestId"]
                    response = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                    response_text = response.get("body", "")
                    # 如果接口返回的是 JSONP，需要去掉回调包装
                    pattern = r"^[^(]+\((.*)\)$"
                    match = re.search(pattern, response_text)
                    if match:
                        json_str = match.group(1)
                    else:
                        json_str = response_text
                    data = json.loads(json_str)
                    product_info["data"] = data
                    print("解析后的数据：", data)
                    break  # 找到数据后退出循环
        except Exception as e:
            print(f"处理网络日志时出错: {e}")
    return product_info
    
def search_and_scrape():
    # 加载已爬取的商品ID
    scraped_ids = load_scraped_product_ids()

    # 转化搜索内容为URL可识别格式
    search_term = "鞋"
    search_term_encoded = urllib.parse.quote(search_term)

    # 初始搜索页面
    page_number = 1
    while True:
        # 打开搜索页面
        search_url = f"https://s.taobao.com/search?commend=all&ie=utf8&initiative_id=tbindexz_20170306&page={page_number}&q={search_term_encoded}&search_type=item&sourceId=tb.index&spm=a21bo.tmall%2Fa.201867-main.d1_2_1.6614c3d5WmI8Dx&ssid=s5-e&tab=mall"
        driver.get(search_url)

        # 等待商品列表出现
        content_items_wrapper = driver.find_elements(By.ID, "content_items_wrapper")
        if content_items_wrapper:
            print(f"第 {page_number} 页元素已出现")
        else:
            print(f"第 {page_number} 页元素未出现")
            break  # 如果没有元素，则结束循环

        # 获取商品列表元素
        product_list = driver.find_elements(By.CSS_SELECTOR, ".tbpc-col.search-content-col")

        # 提取商品链接并保存
        product_links = []
        for product in product_list:
            product_link = product.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
            product_links.append(product_link)

        while product_links:
            # 随机选择一个商品链接
            product_link = random.choice(product_links)
            # 提取商品ID
            product_id = product_link.split("id=")[-1].split("&")[0]

            # 如果商品ID已经爬取过，则跳过
            if product_id in scraped_ids:
                print(f"商品 {product_id} 已经爬取过，跳过该商品。")
                # 删除已爬取的商品链接
                product_links.remove(product_link)
                continue

            # 跳转到商品详情页
            driver.get(product_link)

            # 等待商品详情加载
            time.sleep(random.randint(3, 5))  # 等待3到5秒，模拟人类浏览的速度

            # 提取商品详情信息
            product_info = extract_product_info(driver, product_link)

            # 保存商品信息
            save_product_info(product_info, product_id)

            # 更新已爬取商品ID列表
            update_scraped_product_ids(product_id)

            # 删除已爬取的商品链接
            product_links.remove(product_link)

        # 进入下一页
        page_number += 1
        time.sleep(random.randint(3, 5))  # 等待3到5秒后跳转到下一页
            

# 执行登录和抓取操作
login_process()
search_and_scrape()
