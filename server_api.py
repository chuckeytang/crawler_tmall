import platform
import uuid
import time
import requests
import json
import traceback

# 服务器 API 地址
SERVER_URL = "http://localhost:5001"

def get_mac_address():
    """获取当前设备的 MAC 地址"""
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                    for elements in range(0, 2 * 6, 2)][::-1])
    return mac

def get_os_info():
    """获取当前设备的操作系统信息"""
    return platform.system() + " " + platform.release()

def send_error_to_server(exception_message, traceback_str):
    """
    将异常日志发送到服务器
    :param exception_message: 异常简要信息
    :param traceback_str: 完整的错误堆栈信息
    """
    # 生成错误报告数据
    report_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    mac_address = get_mac_address()
    os_info = get_os_info()

    error_data = {
        "exception_title": f"{os_info} - {report_time} - {mac_address}",
        "exception_message": exception_message,
        "traceback": traceback_str,
        "report_time": report_time,
        "mac_address": mac_address,
        "os_info": os_info
    }

    # 发送请求
    url = f"{SERVER_URL}/log_error"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=error_data, headers=headers)
        if response.status_code == 200:
            print("Error logged successfully to the server")
        else:
            print(f"Failed to log error to the server: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error in sending data to server: {e}")

def send_sku_info_to_server(records):
    """
    批量发送 SKU 采集数据到服务器
    :param records: 包含多个商品详细信息的列表
    """
    url = f"{SERVER_URL}/api/save_tmall_sku_info"
    headers = {"Content-Type": "application/json"}

    # 追加 MAC 地址和浏览器信息到每个记录
    mac_address = get_mac_address()
    browser_info = "Chrome 128.0.6613.138"

    for record in records:
        record["mac_address"] = mac_address
        record["browser_info"] = browser_info

    try:
        response = requests.post(url, json={"sku_records": records}, headers=headers)
        if response.status_code == 200:
            print("SKU data batch uploaded successfully:", response.json())
        else:
            print("Failed to upload SKU data batch:", response.text)
    except requests.exceptions.RequestException as e:
        print("Network error or timeout:", e)