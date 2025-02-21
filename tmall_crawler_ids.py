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
import csv

from driver_manager import DriverManager

# 设置 Chrome 启动参数
chrome_options = Options()
chrome_options.add_argument("--blink-settings=imagesEnabled=false")
# # 禁用视频和插件
chrome_options.add_argument("--disable-web-security")
chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")

driver = uc.Chrome(use_subprocess=True, version_main=128, options=chrome_options)
driver.implicitly_wait(10)

# 模拟键盘向下箭头键滚动页面
def keyboard_scroll(num_of_scrolls, pause_time):
    driver = DriverManager.get_driver()
    for _ in range(num_of_scrolls):
        ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform()
        time.sleep(random.random()*(pause_time/2)+pause_time/2)

# 模拟鼠标滚轮滚动
def mouse_wheel_scroll(num_of_scrolls, pause_time):
    driver = DriverManager.get_driver()
    body = driver.find_element(By.CSS_SELECTOR, 'body')
    for _ in range(num_of_scrolls):
        ActionChains(driver).move_to_element(body).click().send_keys(Keys.PAGE_DOWN).perform()
        time.sleep(random.random()*(pause_time/2)+pause_time/2)

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

def search_and_scrape():
    # 搜索关键词列表
    search_terms = ["鞋", "衣服", "裤子", "手机", "电脑", "零食", "水果", "家居", "美妆", "护肤",
                   "电器", "数码", "运动", "户外", "母婴", "玩具", "书籍", "乐器", "办公", "文具",
                   "箱包", "鞋靴", "配饰", "家纺", "家具", "建材", "装修", "汽车", "摩托车", "自行车",
                   "旅行", "酒店", "餐饮", "娱乐", "教育", "培训", "金融", "投资", "理财", "保险"]  # 您可以自行添加关键词

    all_product_links = []

    for search_term in search_terms:
        # 转化搜索内容为URL可识别格式
        search_term_encoded = urllib.parse.quote(search_term)

        page_number = 1
        product_links = []

        while len(product_links) < 50:
            search_url = f"https://s.taobao.com/search?commend=all&ie=utf8&initiative_id=tbindexz_20170306&page={page_number}&q={search_term_encoded}&search_type=item&sourceId=tb.index&spm=a21bo.tmall%2Fa.201867-main.d1_2_1.6614c3d5WmI8Dx&ssid=s5-e&tab=mall"
            driver.get(search_url)

            content_items_wrapper = driver.find_elements(By.ID, "content_items_wrapper")
            if content_items_wrapper:
                print(f"搜索词: {search_term}, 第 {page_number} 页元素已出现")
            else:
                print(f"搜索词: {search_term}, 第 {page_number} 页元素未出现")
                break

            product_list = driver.find_elements(By.CSS_SELECTOR, ".tbpc-col.search-content-col")

            for product in product_list:
                product_link = product.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                product_links.append(product_link)

                if len(product_links) >= 50:
                    break  # 达到50个链接，跳出当前页面循环

            if len(product_links) < 50 and product_list:  # 检查是否还有下一页
                page_number += 1
                time.sleep(random.randint(3, 9))
            else:
                break  # 没有下一页或达到50个链接，跳出循环

        all_product_links.extend(product_links[:50])

    # 打乱 all_product_links 列表的顺序
    random.shuffle(all_product_links)

    with open("id_list.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        for link in all_product_links:
            writer.writerow([link, 0])  # 写入链接和标志位 0

    print(f"共抓取 {len(all_product_links)} 个商品链接，已保存到 id_list.csv 文件中。")

# 执行登录和抓取操作
login_process()
search_and_scrape()