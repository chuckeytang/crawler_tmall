import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

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

def extract_product_and_rate_info(driver, product_link):
    product_info = {
        "product_link": product_link,
        "title": "",
        "details": [],
        "coupons": [],
        "pre_discount_price": "",
        "final_price": "",
        "pricelist": []
    }

    try:
        # 提取商品名称
        product_info["title"] = driver.find_element(By.XPATH, "//h1[contains(@class, 'mainTitle--')]").text

        # 提取商品参数信息（使用通用的class和结构避免随机值)
        param_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'infoItem--')]")
        params_list = []
        for param_elem in param_elements:
            key = param_elem.find_element(By.XPATH, ".//div[contains(@class, 'infoItemTitle--')]").text
            value = param_elem.find_element(By.XPATH, ".//div[contains(@class, 'infoItemContent--')]").text
            params_list.append({"key": key, "value": value})

        product_info["details"].append({
            "type": "参数",
            "value": params_list
        })
        
        # 提取优惠券信息
        coupon_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'couponText--')]")
        for coupon in coupon_elements:
            coupon_text = coupon.text
            if coupon_text:  # 如果有优惠券文本
                product_info["coupons"].append(coupon_text)

        # 获取所有SKU项，模拟点击以获取价格变化
        sku_items = driver.find_elements(By.XPATH, "//div[contains(@class, 'skuItem--')]")
        pricelist = []
        sku_item = sku_items[0]
        value_items = sku_item.find_elements(By.XPATH, ".//div[contains(@class, 'valueItem--')]")
        
        previous_location = None  # 用于存储前一个 value_item 的位置
        for index, value_item in enumerate(value_items):
            # 跳过已禁用的项
            if "isDisabled--" in value_item.get_attribute("class"):
                continue
            
            # 获取当前 value_item 的位置
            current_location = value_item.location
            
            # 判断是否需要滚动
            if previous_location is not None and current_location['y'] - previous_location['y'] > 10:
                keyboard_scroll(driver, 2, 0.3)  # 向下滚动

            # 获取SKU名称和状态
            sku_name = value_item.find_element(By.XPATH, ".//span[contains(@class, 'valueItemText--')]").text

            # 模拟点击选择该SKU项
            if "isSelected--" not in value_item.get_attribute("class"):
                # 滚动到目标元素
                actions = ActionChains(driver)
                actions.move_to_element(value_item).click().perform()
            time.sleep(random.uniform(0.3, 0.7))  # 模拟用户点击延迟

            final_price_after_click = None
            pre_discount_price_after_click = None
            # 提取券前价和到手价
            price_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'priceWrap--')]")
            for price_elem in price_elements:
                try:
                    # 获取整个文本内容
                    price_text = price_elem.text
                    if price_text == '':
                        continue

                    # 检查是否包含“后”字，或者“前”字
                    if "后" in price_text:
                        # 提取“后”字之后的第一个完整数字，作为最终价格
                        final_price_after_click = re.search(r'后.*?(\d+(?:\.\d+)?)', price_text, re.DOTALL)
                        if final_price_after_click:
                            final_price_after_click = final_price_after_click.group(1)
                        else:
                            final_price_after_click = None

                    if "前" in price_text:
                        # 提取“前”字之后的第一个完整数字，作为优惠前价格
                        pre_discount_price_after_click = re.search(r'前.*?(\d+(?:\.\d+)?)', price_text, re.DOTALL)
                        if pre_discount_price_after_click:
                            pre_discount_price_after_click = pre_discount_price_after_click.group(1)
                        else:
                            pre_discount_price_after_click = None

                    if "后" not in price_text and "前" not in price_text:
                        # 如果没有“前”或者“后”，则视为最终价格
                        final_price_after_click = re.search(r'(\d+(?:\.\d+)?)', price_text, re.DOTALL)
                        if final_price_after_click:
                            final_price_after_click = final_price_after_click.group(1)
                        else:
                            final_price_after_click = None

                    print(f"最终价格: {final_price_after_click}, 优惠前价格: {pre_discount_price_after_click}")

                except Exception as e:
                    print(f"价格提取出错: {e}")

            print(f"最终价格: {final_price_after_click}, 优惠前价格: {pre_discount_price_after_click}")
            previous_location = current_location  # 更新前一个 value_item 的位置

            # 保存该SKU对应的价格信息
            pricelist.append({
                "sku_name": sku_name,
                "final_price": final_price_after_click,
                "pre_discount_price": pre_discount_price_after_click
            })

        product_info["pricelist"] = pricelist

        # 将商品信息保存为JSON文件
        filename = f"{product_info['title']}.json"
        filename = filename.replace("/", "_")  # 替换文件名中的非法字符
        os.makedirs("product_info", exist_ok=True)  # 创建文件夹如果不存在
        with open(os.path.join("product_info", filename), "w", encoding="utf-8") as f:
            json.dump(product_info, f, ensure_ascii=False, indent=4)

        print(f"商品信息已保存到文件: {filename}")
        return product_info

    except Exception as e:
        print(f"提取商品信息时出错: {e}")
        return None
    
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
            product_info = extract_product_and_rate_info(driver, product_link)

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
