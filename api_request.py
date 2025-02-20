import platform
import uuid
import time
import requests
import traceback
import json

def send_error_to_server(exception_message, traceback_str):
    # 获取操作系统信息
    os_info = platform.system() + " " + platform.release()
    
    # 获取当前时间
    report_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    # 获取MAC地址
    mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                            for elements in range(0,2*6,2)][::-1])
    
    # 构造异常数据
    error_data = {
        "exception_title": f"{os_info} - {report_time} - {mac_address}",
        "exception_message": exception_message,
        "traceback": traceback_str,
        "report_time": report_time,
        "mac_address": mac_address,
        "os_info": os_info
    }

    # 设置服务器地址
    url = "http://localhost:5001/log_error"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=error_data, headers=headers)
        if response.status_code == 200:
            print("Error logged successfully to the server")
        else:
            print(f"Failed to log error to the server: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error in sending data to server: {e}")
