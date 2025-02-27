# gui_pyqt5.py
import sys
import os
import datetime
import threading
import time
import subprocess
import sys
import multiprocessing
import logging

# 确保 macOS 上 `multiprocessing` 使用 `fork` 避免重复执行进程
multiprocessing.set_start_method("spawn", force=True)

# ✅ 设置日志文件
# log_file = os.path.expanduser("~/tmall_crawler_debug.log")
# logging.basicConfig(filename=log_file, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# print("🚀 [START] GUI 启动中...", file=sys.stderr)
# logging.debug("🚀 [START] GUI 启动中...")

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QFileDialog, QCheckBox,
                             QTableWidget, QTableWidgetItem, QMessageBox, QStackedWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication

# print("✅ [INFO] PyQt5 模块加载成功", file=sys.stderr)
# logging.debug("✅ [INFO] PyQt5 模块加载成功")

from tmall_crawler import login_process, process_product_links
# print("✅ [INFO] tmall_crawler 模块加载成功", file=sys.stderr)
# logging.debug("✅ [INFO] tmall_crawler 模块加载成功")

# 创建全局数据库管理实例
from db_manager import db_manager  # 使用全局实例
from driver_manager import DriverManager

# 检测操作系统，进行不同的配置
def configure_os_environment():
    if sys.platform == "darwin":
        # MacOS 相关配置
        os.environ["QT_MAC_WANTS_LAYER"] = "1"
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        logging.debug("✅ [INFO] 配置 MacOS 环境变量")
    elif sys.platform == "win32":
        # Windows 相关配置
        logging.debug("✅ [INFO] 配置 Windows 环境变量")

# print("✅ [INFO] db_manager 和 driver_manager 加载成功", file=sys.stderr)
# logging.debug("✅ [INFO] db_manager 和 driver_manager 加载成功")
def is_browser_open(driver):
    try:
        driver.title  # 尝试获取页面标题
        return True
    except:
        logging.error(f"浏览器检查失败: {e}")
        return False
    
class ImportOperationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # logging.debug("✅ [INFO] ImportOperationPage 初始化中...")
        layout = QVBoxLayout(self)
        
        # ---------------- 导入ID列表部分 ----------------
        title = QLabel("导入ID列表")
        title.setStyleSheet("font-size: 18pt;")
        layout.addWidget(title)
        # print("✅ [INFO] ImportOperationPage 导入ID列表完成", file=sys.stderr)
        # logging.debug("✅ [INFO] ImportOperationPage 导入ID列表完成")
        
        file_layout = QHBoxLayout()
        self.file_path_line = QLineEdit()
        self.file_path_line.setPlaceholderText("选择ID列表文件路径...")
        file_layout.addWidget(self.file_path_line)
        select_button = QPushButton("选择文件")
        select_button.clicked.connect(self.select_file)
        file_layout.addWidget(select_button)
        import_button = QPushButton("导入")
        import_button.clicked.connect(self.import_ids)
        file_layout.addWidget(import_button)
        layout.addLayout(file_layout)
        
        self.msg_label = QLabel("")
        self.msg_label.setStyleSheet("color: red;")
        layout.addWidget(self.msg_label)
        
        # ---------------- 提取/上传操作部分 ----------------
        op_title = QLabel("提取/上传操作")
        op_title.setStyleSheet("font-size: 18pt;")
        layout.addWidget(op_title)
        
        filter_layout = QHBoxLayout()
        filter_label = QLabel("筛选日期 (YYYY-MM-DD):")
        filter_layout.addWidget(filter_label)
        self.date_line = QLineEdit(datetime.date.today().isoformat())
        filter_layout.addWidget(self.date_line)
        filter_button = QPushButton("筛选")
        filter_button.clicked.connect(self.refresh_table)
        filter_layout.addWidget(filter_button)
        layout.addLayout(filter_layout)
        
        # ---------------- 数据表格 ----------------
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["商品id", "商品url", "导入时间", "已提取", "已上传"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.table.setColumnWidth(0, 150)  # 商品id
        self.table.setColumnWidth(1, 600)  # 商品url（较宽）
        self.table.setColumnWidth(2, 150)  # 导入时间
        self.table.setColumnWidth(3, 80)   # 已提取
        self.table.setColumnWidth(4, 80)   # 已上传

        self.refresh_table()
        
        # ---------------- 复选框区域 ----------------
        # checkbox_layout = QHBoxLayout()
        # self.ignore_faults_checkbox = QCheckBox("重新提取故障项")
        # checkbox_layout.addWidget(self.ignore_faults_checkbox)
        # self.recrawl_checkbox = QCheckBox("重新提取全部项")
        # checkbox_layout.addWidget(self.recrawl_checkbox)
        # layout.addLayout(checkbox_layout)
        
        # ---------------- 操作按钮区域 ----------------
        btn_layout = QHBoxLayout()
        self.crawl_button = QPushButton("提取")
        self.crawl_button.clicked.connect(self.crawl)
        btn_layout.addWidget(self.crawl_button)
        upload_button = QPushButton("上传")
        upload_button.clicked.connect(self.upload)
        btn_layout.addWidget(upload_button)
        layout.addLayout(btn_layout)
        
        # ---------------- 清空当日导入按钮 ----------------
        clear_button = QPushButton("清空当日导入")
        clear_button.clicked.connect(self.clear_today_imports)
        layout.addWidget(clear_button)

        QGuiApplication.setQuitOnLastWindowClosed(False)
        # print("✅ [INFO] ImportOperationPage 组件初始化完成", file=sys.stderr)
        # logging.debug("✅ [INFO] ImportOperationPage 组件初始化完成")
    
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择ID列表文件", os.getcwd(), "Text Files (*.txt)")
        if file_path:
            self.file_path_line.setText(file_path)
    
    def import_ids(self):
        file_path = self.file_path_line.text().strip()
        if not file_path:
            QMessageBox.critical(self, "错误", "请先选择文件！")
            return
        try:
            count, duplicate_count = db_manager.import_ids_from_file(file_path)
            self.msg_label.setText(f"成功导入 {count} 条记录，其中 {duplicate_count} 条是重复的")
            self.refresh_table()
        except Exception as e:
            logging.error(f"导入失败：{e}")
            QMessageBox.critical(self, "错误", f"导入失败：{e}")
    
    def refresh_table(self):
        self.table.setRowCount(0)
        date_str = self.date_line.text().strip()
        try:
            rows = db_manager.query_ids_by_date(date_str, order_desc=True)
        except Exception as e:
            logging.error(f"查询数据库失败：{e}")
            QMessageBox.critical(self, "错误", f"查询数据库出错：{e}")
            return
        
        for row in rows:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(row[0])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(row[1])))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(row[2])))
            crawled = "已提取" if row[3] == 1 else "否"
            self.table.setItem(row_idx, 3, QTableWidgetItem(crawled))
            uploaded = "已上传" if row[4] == 1 else "否"
            self.table.setItem(row_idx, 4, QTableWidgetItem(uploaded))
            fault = "有故障" if row[5] == 1 else "无"
            self.table.setItem(row_idx, 5, QTableWidgetItem(fault))
            # 操作列暂时为空
            self.table.setItem(row_idx, 6, QTableWidgetItem(""))
    
    def clear_today_imports(self):
        today = datetime.date.today().isoformat()
        try:
            cursor = db_manager.conn.cursor()
            cursor.execute("DELETE FROM id_list WHERE import_time LIKE ?", (f"{today}%",))
            db_manager.conn.commit()
            self.refresh_table()
        except Exception as e:
            logging.error(f"清空记录失败：{e}")
            QMessageBox.critical(self, "错误", f"清空记录失败：{e}")
    
    def crawl(self):
        self.crawl_button.setEnabled(False)
        
        date_str = self.date_line.text().strip()
        ignore_faults = self.ignore_faults_checkbox.isChecked()
        recrawl = self.recrawl_checkbox.isChecked()
        
        def crawl_thread():
            try:
                driver = DriverManager.get_driver()  # 获取 driver

                # 检查浏览器是否已关闭`
                if not is_browser_open(driver):
                    raise Exception("浏览器未开启或已关闭")
                
                login_process()
                process_product_links(date_str)
                QMessageBox.information(self, "完成", "提取操作完成")
            except Exception as e:
                logging.error(f"提取时出错: {e}")
                DriverManager.close_driver()
            finally:
                self.crawl_button.setEnabled(True)
        t = threading.Thread(target=crawl_thread, daemon=True)
        t.start()
    
    def upload(self):
        QMessageBox.information(self, "上传", "开始上传操作")

class DuplicatePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("重复ID列表")
        title.setStyleSheet("font-size: 18pt;")
        layout.addWidget(title)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["编号", "urlid", "导入时间"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        
        clear_button = QPushButton("清空列表")
        clear_button.clicked.connect(self.clear_duplicate_list)
        layout.addWidget(clear_button)
        
        self.refresh_duplicate_list()
    
    def refresh_duplicate_list(self):
        self.table.setRowCount(0)
        try:
            rows = db_manager.query_duplicate_ids()
            for row in rows:
                row_idx = self.table.rowCount()
                self.table.insertRow(row_idx)
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(row[0])))
                self.table.setItem(row_idx, 1, QTableWidgetItem(str(row[1])))
                self.table.setItem(row_idx, 2, QTableWidgetItem(str(row[2])))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询重复ID列表出错：{e}")
    
    def clear_duplicate_list(self):
        db_manager.clear_duplicate_ids()
        self.refresh_duplicate_list()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # logging.debug("✅ [INFO] MainWindow 初始化中...")
        self.setWindowTitle("天猫数据抓取工具")
        self.resize(1500, 800)
        
        # 创建堆叠页面
        self.stacked_widget = QStackedWidget()
        self.import_op_page = ImportOperationPage()
        self.duplicate_page = DuplicatePage()
        self.stacked_widget.addWidget(self.import_op_page)
        self.stacked_widget.addWidget(self.duplicate_page)
        
        # 菜单按钮区域
        button_layout = QHBoxLayout()
        btn_data = QPushButton("数据采集")
        btn_data.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.import_op_page))
        button_layout.addWidget(btn_data)
        btn_dup = QPushButton("查看重复ID列表")
        btn_dup.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.duplicate_page))
        button_layout.addWidget(btn_dup)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.stacked_widget)
        
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # print("✅ [INFO] MainWindow 初始化完成", file=sys.stderr)
        # logging.debug("✅ [INFO] MainWindow 初始化完成")

if __name__ == "__main__":
    multiprocessing.freeze_support()  # 确保 PyInstaller 兼容 `multiprocessing`

    # print("✅ [INFO] 启动 QApplication...", file=sys.stderr)
    logging.debug("✅ [INFO] 启动 QApplication...")

    configure_os_environment()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
