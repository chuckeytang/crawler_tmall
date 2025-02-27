import traceback
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from driver_manager import DriverManager 

import logging

import time
import random
import urllib.parse
import json
import os
import re
import csv
import simpleaudio as sa
import datetime
import pandas as pd
import threading

from server_api import send_error_to_server, send_sku_info_to_server
from db_manager import DBManager, db_manager  # 使用全局实例


class CrawlerBaseException(Exception):
    """爬虫异常基类"""
    def __init__(self, msg, original_exception=None):
        super().__init__(msg)
        self.original_exception = original_exception
        
stop_alert = False
last_save_time = None  # 用于记录上次调用时间

# 模拟键盘向下箭头键滚动页面
def keyboard_scroll(num_of_scrolls, pause_time):
    driver = DriverManager.get_driver()
    for _ in range(num_of_scrolls):
        ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform()
        time.sleep(random.random()*(pause_time/2)+pause_time/2)

# 模拟鼠标滚轮滚动
def mouse_wheel_scroll(num_of_scrolls, pause_time):
    driver = DriverManager.get_driver()
    body = driver.find_element_by_css_selector('body')
    for _ in range(num_of_scrolls):
        ActionChains(driver).move_to_element(body).click().send_keys(Keys.PAGE_DOWN).perform()
        time.sleep(random.random()*(pause_time/2)+pause_time/2)

def save_tmall_sku_info(local_db_manager, product_info, rate_info):
    global last_save_time
    global stop_alert
    if product_info.get("data", {}) == None:
        return 2
    
    data = product_info.get("data", {}).get("data", {})
    skuBase = data.get("skuBase", {})

    if not skuBase:
        print("skuBase 为空，商品提取异常，需要人工处理。")
        return 0

    skuInfoDict = data.get("skuCore", {}).get("sku2info", {})
    sku_skus = skuBase.get("skus", [])
    sku_props = skuBase.get("props", [])
    
    total_comments = 0
    if rate_info.get("data", {}):
        total_comments = rate_info.get("data", {}).get("feedAllCountFuzzy", "")
        
    seller = data.get("seller", {})
    item_info = data.get("item", {})
    delivery_info = data.get("componentsVO", {}).get("deliveryVO", {})
    
    # 记录当前时间，计算时间间隔
    current_time = time.time()
    
    if last_save_time is not None:
        interval = current_time - last_save_time
        if interval < 6:  # 如果时间间隔小于 6 秒，认为有问题
            print(f"警告：两次保存时间间隔过短（{interval}秒），可能出现未检测到的错误。")
            
            # 启动报警线程
            alert_thread = threading.Thread(target=play_alert_sound, daemon=True)
            alert_thread.start()

            # 保存日志
            logging.error(f"两次保存时间间隔过短（{interval}秒），可能出现未检测到的错误。产品ID: {item_info.get('itemId', '')}, SKU ID: {sku_id}")

            # 等待用户确认继续
            print("提取信息失败，请处理页面验证后按任意键继续...")
            input()  # 等待用户输入
            stop_alert = True
            time.sleep(0.5)  # 等待线程安全退出
            return 0  # 终止当前操作

    # 更新 last_save_time 为当前时间
    last_save_time = current_time
    records = []
    # 遍历 SKU 数据并保存到 SQLite
    for sku in sku_skus:
        sku_id = sku.get("skuId")
        sku_name = ""
        propPath = sku.get("propPath", "")
        
        first_group = propPath.split(";")[0]
        parts = first_group.split(":")
        vid = parts[1] if len(parts) >= 2 else ""
        
        for prop in sku_props:
            for value in prop.get("values", []):
                if value.get("vid") == vid:
                    sku_name = value.get("name", "")
                    break
            if sku_name:
                break

        price = sku.get("price", {}).get("priceText", "")
        quantity = sku.get("quantity", 0)
        sale_status = "在售" if int(quantity) != 0 else "无货"
        
        # 参数信息，多个参数拼接
        basePropsDict = {}
        extension_infos = data.get("componentsVO", {}).get("extensionInfoVO", {}).get("infos", [])
        for info in extension_infos:
            if info.get("type") == "BASE_PROPS":
                for item in info.get("items", []):
                    title = item.get("title", "")
                    texts = item.get("text", [])
                    if isinstance(texts, list):
                        basePropsDict[title] = " ".join(texts)
                    else:
                        basePropsDict[title] = texts

        parameter_info = json.dumps(basePropsDict, ensure_ascii=False)
        
        # 构造采集记录
        record = {
            "collection_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "check_date": "",
            "platform": "天猫",
            "shop_id": seller.get("shopId", ""),
            "shop_name": seller.get("sellerNick", ""),
            "spu_url": f"https://item.taobao.com/item.htm?id={item_info.get('itemId', '')}",
            "product_url": f"https://detail.tmall.com/item.htm?id={item_info.get('itemId', '')}&skuId={sku_id}",
            "category_level_1": "留待完善",
            "category_level_2": "留待完善",
            "category_level_3": "留待完善",
            "brand_name": basePropsDict.get("品牌", ""),
            "spu_code": item_info.get("itemId", ""),
            "spu_name": item_info.get("title", ""),
            "sku_code": sku_id,
            "sku_name": sku_name,
            "sku_sale_status": sale_status,
            "specification": sku_name,
            "parameter_info": parameter_info,
            "total_comments": total_comments,
            "sales": item_info.get("vagueSellCount", ""),
            "marked_price": sku.get("price", {}).get("priceText", ""),
            "final_price": sku.get("subPrice", {}).get("priceText", ""),
            "discount_info": "优惠信息待抓取",
            "delivery_area": delivery_info.get("deliveryFromAddr", ""),
            "product_image": "",
            "crawl_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 添加到记录列表
        records.append(record)

        # 保存到本地数据库
        local_db_manager.save_product_info(**record)

    # **批量发送到服务器**
    if send_sku_info_to_server(records):
        print("商品信息已 保存到SQLite 并 上传到服务器")
    else:
        print("商品信息已保存上传失败")
    return 2

def save_tmall_sku_info_toexcel(product_info, rate_info):
    data = product_info.get("data", {}).get("data", {})

    # 判断 skuBase 是否为空或为 None
    skuBase = data.get("skuBase", {})
    if not skuBase:
        # 返回状态 0 表示提取失败，可能需要人工处理
        print("skuBase 为空，商品提取异常，需要人工处理。")
        return 0

    # 1. 从 extensionInfoVO.infos 中提取 BASE_PROPS 和 DAILY_COUPON 信息
    basePropsDict = {}
    couponArray = []
    extension_infos = data.get("componentsVO", {}) \
                          .get("extensionInfoVO", {}) \
                          .get("infos", [])
    for info in extension_infos:
        if info.get("type") == "BASE_PROPS":
            # 遍历 items 数组，构造字典：key为 title，value 为 text（数组拼接成字符串）
            for item in info.get("items", []):
                title = item.get("title", "")
                texts = item.get("text", [])
                if isinstance(texts, list):
                    basePropsDict[title] = " ".join(texts)
                else:
                    basePropsDict[title] = texts
        elif info.get("type") == "DAILY_COUPON":
            # 将 DAILY_COUPON 的 items 数组直接存入 couponArray
            couponArray = info.get("items", [])

    # 2. 构造 skuInfoDict，先取出 skuCore.sku2info 字典
    skuInfoDict = data.get("skuCore", {}).get("sku2info", {})

    # 3. 为每个 sku 增加 skuName（规格名称）
    #    遍历 data.skuBase.skus，利用 propPath 获取第一组的 vid，再遍历 data.skuBase.props 找到对应的 name
    skuBase = data.get("skuBase", {})
    sku_skus = skuBase.get("skus", [])
    sku_props = skuBase.get("props", [])
    
    total_comments = 0
    # 从评论数据中获取“总评论数量”（对所有 sku 均相同）
    if (rate_info.get("data", {})):
        total_comments = rate_info.get("data", {}).get("feedAllCountFuzzy", "")
        
    for sku in sku_skus:
        sku_id = sku.get("skuId")
        propPath = sku.get("propPath", "")
        # propPath 示例："1627207:60092;20122:368194910"，取第一个分号前的部分
        first_group = propPath.split(";")[0]
        parts = first_group.split(":")
        vid = parts[1] if len(parts) >= 2 else ""
        sku_name = ""
        # 遍历所有 props 中的 values，寻找匹配的 vid
        for prop in sku_props:
            for value in prop.get("values", []):
                if value.get("vid") == vid:
                    sku_name = value.get("name", "")
                    break
            if sku_name:
                break
        # 将 skuName 写入 skuInfoDict 对应的 sku 数据中
        if sku_id in skuInfoDict:
            skuInfoDict[sku_id]["skuName"] = sku_name
        else:
            skuInfoDict[sku_id] = {"skuName": sku_name}

    coupon_texts = []
    for item in couponArray:
        texts = item.get("text", [])
        # texts 可能是列表，将列表中的字符串加入 coupon_texts
        coupon_texts.extend(texts)
    优惠信息_str = ",".join(coupon_texts)
    
    # 4. 根据 skuBase.skus 中每个 sku 构造一条记录
    records = []
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    seller = data.get("seller", {})
    item_info = data.get("item", {})
    delivery_info = data.get("componentsVO", {}).get("deliveryVO", {})

    for sku in sku_skus:
        sku_id = sku.get("skuId")
        sku_data = skuInfoDict.get(sku_id, {})
        # 判断库存：若 quantity 为 "0" 则判定为“无货”，否则“在售”
        quantity = sku_data.get("quantity", "0")
        try:
            sale_status = "在售" if int(quantity) != 0 else "无货"
        except Exception:
            sale_status = "在售"
        
        record = {
            "收录日期": today_str,
            "核查日期": "",
            "平台": "天猫",
            "店铺ID": seller.get("shopId", ""),
            "店铺名称": seller.get("sellerNick", ""),
            "SPU链接": f"https://item.taobao.com/item.htm?id={item_info.get('itemId', '')}",
            "商品链接": f"https://detail.tmall.com/item.htm?id={item_info.get('itemId', '')}&skuId={sku_id}",
            "平台一级类目": "留待完善",
            "平台二级类目": "留待完善",
            "平台三级类目": "留待完善",
            "品牌名称": basePropsDict.get("品牌", ""),
            "spu编码": item_info.get("itemId", ""),
            "spu名称": item_info.get("title", ""),
            "sku编码": sku_id,
            "sku名称": sku_data.get("skuName", ""),
            "sku销售状态": sale_status,
            "规格": sku_data.get("skuName", ""),
            "参数信息": json.dumps(basePropsDict, ensure_ascii=False),
            "总评论数量": total_comments,
            "销量": item_info.get("vagueSellCount", ""),
            "标价": sku_data.get("price", {}).get("priceText", ""),
            "到手价": sku_data.get("subPrice", {}).get("priceText", ""),
            "优惠信息": 优惠信息_str,
            "发货地区": delivery_info.get("deliveryFromAddr", ""),
            "商品主图": ""
        }

        # 保存json
        # filename = f"product_info/{product_id}.json"
        # os.makedirs("product_info", exist_ok=True)  # 确保目录存在
        # with open(filename, "w", encoding="utf-8") as f:
        #     json.dump(product_info, f, ensure_ascii=False, indent=4)
        # print(f"商品信息已保存: {filename}")

        records.append(record)
        
    send_sku_info_to_server(records)

    # 5. 利用 pandas 导出为 Excel 文件
    df = pd.DataFrame(records)
    output_file = "productInfo.xlsx"

    # 判断文件是否存在
    if os.path.exists(output_file):
        # 如果存在，则读取现有数据
        existing_df = pd.read_excel(output_file)
        # 合并新数据与原有数据
        final_df = pd.concat([existing_df, df], ignore_index=True)
    else:
        final_df = df

    # 保存合并后的数据
    final_df.to_excel(output_file, index=False)
    print(f"Excel 已保存到 {output_file}")
    return 1
    
def login_process():
    # 打开淘宝登录页面
    driver = DriverManager.get_driver()
    driver.get("https://login.taobao.com/member/login.jhtml")

    # 等待扫码登录成功后，用户名元素出现
    try:
        WebDriverWait(driver, 3600*24).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[class^='myAccountName']"))
        )
        print("用户已登录，继续执行后续操作")
    except TimeoutException:
        print("等待登录超时，请手动完成登录")

def play_alert_sound():
    """
    持续播放报警声音，直到 stop_alert 变为 True
    """
    global stop_alert
    wave_obj = sa.WaveObject.from_wave_file("./alert.wav")

    while not stop_alert:  # 只要 stop_alert 还是 False，就继续播放
        play_handle = wave_obj.play()
        play_handle.wait_done()  # 等待当前播放完成
        time.sleep(0.5)  # 控制播放间隔，避免高 CPU 占用

# 返回值
# 0 - 需要人工处理的错误
# 1 - 有错误但重试
# 2 - 无错误
def extract_product_and_rate_info(product_link):
    """
    进入商品详情页后，等待页面加载一段时间，
    一次性从性能日志中捕获：
      1. mtop.taobao.pcdetail.data.get 的返回数据，存入 product_info["data"]
      2. mtop.taobao.rate.detaillist.get 的返回数据，存入 rate_info["data"]
    最后返回 product_info, rate_info 以及成功标记。
    """
    global stop_alert
    product_info = {
        "product_link": product_link,
        "data": None  # 最终保存接口返回的数据
    }
    rate_info = {
        "data": None   # 评论接口返回的数据（取其中 data 字段）
    }

    # 等待页面加载并触发接口调用（根据实际情况调整等待时间）
    time.sleep(random.randint(6, 8)) 

    driver = DriverManager.get_driver()
    logs = driver.get_log("performance")
    for entry in logs:
        message = json.loads(entry["message"])["message"]
        if "Network.responseReceived" not in message["method"]:
            continue
        if "Network.responseReceivedExtraInfo" in message["method"]:
            continue

        response_url = message["params"]["response"]["url"]
        request_id = message["params"]["requestId"]
        
        # 若为商品详情接口
        if "mtop.taobao.pcdetail.data.get" in response_url:
            response = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
            response_text = response.get("body", "")
            # 去除 JSONP 回调包装
            pattern = r"^[^(]+\((.*)\)$"
            match = re.search(pattern, response_text)
            if match:
                json_str = match.group(1)
            else:
                json_str = response_text
            data = json.loads(json_str)
            product_info["data"] = data
            
            # 错误处理
            if isinstance(data, dict) and 'ret' in data:
                if any('FAIL_SYS_TOKEN_EMPTY' in s for s in data['ret']):
                    print("检测到 FAIL_SYS_TOKEN_EMPTY 错误")
                    return product_info, rate_info, 1
                if any('FAIL_SYS_USER_VALIDATE' in s for s in data['ret']):
                    print("检测到 FAIL_SYS_USER_VALIDATE 错误")
                    # 先重置 stop_alert 为 False
                    stop_alert = False
                    return product_info, rate_info, 0
            print("解析后的商品详情数据：", data)
        
        # 若为评论数据接口
        elif "mtop.taobao.rate.detaillist.get" in response_url:
            response = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
            response_text = response.get("body", "")
            pattern = r"^[^(]+\((.*)\)$"
            match = re.search(pattern, response_text)
            if match:
                json_str = match.group(1)
            else:
                json_str = response_text
            data = json.loads(json_str)
            # 评论接口返回数据格式一般为：{"api": ..., "data": { ... }, ...}
            # 取出 data.data 中的内容（如果需要调整，请根据实际数据结构修改）
            rate_info["data"] = data.get("data", {})
            print("解析后的评论数据：", rate_info["data"])
            
    return product_info, rate_info, 2

def process_product_links(date_filter=None):
    """
    处理数据库中的商品链接，仅提取筛选日期内的商品。
    :param date_filter: 筛选日期，格式 'YYYY-MM-DD'，默认为 None（不过滤）
    """
    global stop_alert
    
    local_db_manager = DBManager(db_manager.db_path)
    conn = local_db_manager.conn
    cursor = conn.cursor()
    
    rows = local_db_manager.query_ids_by_date(date_filter, only_not_crawled=True)
    row_index = 0
    while row_index < len(rows):
        row = rows[row_index]
        row_urlid = row[0]
        product_link = row[1]
        if not product_link:
            row_index += 1
            continue
        
        # 提取商品ID
        product_id = product_link.split("id=")[-1].split("&")[0]
        try:
            # 跳转到商品详情页
            driver = DriverManager.get_driver()
            driver.get(product_link)
            
            # 提取商品详情信息
            product_info, rate_info, status = extract_product_and_rate_info(product_link)
            if status == 0:  # 需要人工处理的错误
                alert_thread = threading.Thread(target=play_alert_sound, daemon=True)
                alert_thread.start()
                print("提取信息失败，请处理页面验证后按任意键继续...")
                input()  # 等待用户输入
                stop_alert = True
                time.sleep(0.5)
                continue  # **不增加 row_index，重新提取当前商品**
            elif status == 1:  # 有错误但重试
                print("提取信息失败，正在重试...")
                continue  # **不增加 row_index，重新提取当前商品**
            local_db_manager.mark_as_crawled(row_urlid)

            # 保存商品信息到 SQLite（save_tmall_sku_info 返回 1 成功，0 表示错误）
            status2 = save_tmall_sku_info(local_db_manager, product_info, rate_info)
            if status2 == 0:
                alert_thread = threading.Thread(target=play_alert_sound, daemon=True)
                alert_thread.start()
                print("提取信息失败，请处理登录异常后按任意键继续...")
                input()  # 等待用户输入
                stop_alert = True
                time.sleep(0.5)
                continue # **不增加 row_index，重新提取当前商品**
            local_db_manager.mark_as_uploaded(row_urlid)
            
            print(f"商品 {product_id} 提取成功")

        except Exception as e:
            # 处理异常并发送到服务器
            error_message = str(e)
            error_traceback = traceback.format_exc()

            # 将异常信息发送到 Flask 服务器
            send_error_to_server(error_message, error_traceback)

            # 处理断网错误
            if "net::ERR_INTERNET_DISCONNECTED" in error_message:
                # 启动一个新线程来播放声音，并让用户处理断网情况
                alert_thread = threading.Thread(target=play_alert_sound, daemon=True)
                alert_thread.start()
                print(f"商品 {product_id} 发生断网错误，请检查网络连接后按任意键继续...")
                input()  # 等待用户输入
                stop_alert = True
                time.sleep(0.5)  # 等待线程安全退出
                continue  # **不增加 row_index，重新提取当前商品**

            # 处理其他异常
            print(f"商品 {product_id} 发生错误，跳过: {e}")
            # 通用异常转换
            raise CrawlerBaseException(
                f"商品 {product_id} 处理失败 | {error_message}",
                original_exception=e
            ) from e
        
        row_index += 1  # 处理下一行
