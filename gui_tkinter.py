# gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import datetime
import threading

from db_manager import DBManager
# 引入爬虫模块中的 login_process 和 process_product_links
from tmall_crawler import login_process, process_product_links

# 创建全局数据库管理实例
db_path = "./data/mydatabase.db"
db_manager = DBManager(db_path)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("天猫爬虫工具")
        self.geometry("1500x800")
        
        # 页面容器
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        for F in (ImportOperationPage, DuplicatePage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        self.create_menu()
        self.show_frame(ImportOperationPage)

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        page_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="页面", menu=page_menu)
        page_menu.add_command(label="数据采集", command=lambda: self.show_frame(ImportOperationPage))
        page_menu.add_command(label="查看重复ID列表", command=lambda: self.show_frame(DuplicatePage))

    def show_frame(self, page_class):
        frame = self.frames[page_class]
        frame.tkraise()

class ImportOperationPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        def global_click(event):
            print(f"全局点击: x={event.x}, y={event.y}")
        self.winfo_toplevel().bind_all("<Button-1>", global_click)
        self.controller = controller
        
        # 导入ID列表的部分
        title = tk.Label(self, text="导入ID列表", font=("Arial", 18))
        title.pack(pady=10)
        
        # 文件选择区域
        file_frame = tk.Frame(self)
        file_frame.pack(pady=10)
        
        self.file_path_var = tk.StringVar()
        file_entry = tk.Entry(file_frame, textvariable=self.file_path_var, width=60)
        file_entry.pack(side="left", padx=5)
        
        select_button = tk.Button(file_frame, text="选择文件", command=self.select_file)
        select_button.pack(side="left", padx=5)
        
        import_button = tk.Button(self, text="导入", width=15, command=self.import_ids)
        import_button.pack(pady=10)
        
        self.msg_label = tk.Label(self, text="", fg="red")
        self.msg_label.pack(pady=5)

        # 爬取/上传操作部分
        operation_title = tk.Label(self, text="爬取/上传操作", font=("Arial", 18))
        operation_title.pack(pady=10)

        # 日期筛选区域
        filter_frame = tk.Frame(self)
        filter_frame.pack(pady=5)
        tk.Label(filter_frame, text="筛选日期 (YYYY-MM-DD): ").pack(side="left")
        self.date_var = tk.StringVar(value=datetime.date.today().isoformat())
        self.date_entry = tk.Entry(filter_frame, textvariable=self.date_var, width=15)
        self.date_entry.pack(side="left", padx=5)
        filter_button = tk.Button(filter_frame, text="筛选", command=self.refresh_table)
        filter_button.pack(side="left", padx=5)

        # Treeview 展示导入记录
        columns = ("编号", "商品id", "上皮url", "导入时间", "已爬取", "已上传", "故障", "操作")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="center")
        self.tree.pack(pady=10, padx=10, fill="both", expand=True)
        self.refresh_table()
        
        # 复选框区域
        check_frame = tk.Frame(self)
        check_frame.pack(pady=10)
        self.ignore_faults_var = tk.BooleanVar(value=False)
        self.re_crawl_var = tk.BooleanVar(value=False)
        tk.Checkbutton(check_frame, text="忽略故障", variable=self.ignore_faults_var).pack(side="left", padx=20)
        tk.Checkbutton(check_frame, text="重新爬取", variable=self.re_crawl_var).pack(side="left", padx=20)
        
        # 操作按钮区域
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=20)
        crawl_btn = tk.Button(btn_frame, text="爬取", width=15, height=2, command=self.crawl)
        upload_btn = tk.Button(btn_frame, text="上传", width=15, height=2, command=self.upload)
        crawl_btn.grid(row=0, column=0, padx=30)
        upload_btn.grid(row=0, column=1, padx=30)

        # 清空当日导入的按钮
        clear_button = tk.Button(self, text="清空当日导入", command=self.clear_today_imports)
        clear_button.pack(pady=10)

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="选择ID列表文件",
            filetypes=[("Text Files", "*.txt")],
            initialdir=os.getcwd()
        )
        if file_path:
            self.file_path_var.set(file_path)
    
    def import_ids(self):
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showerror("错误", "请先选择文件！")
            return
        
        try:
            count, duplicate_count = db_manager.import_ids_from_file(file_path)
            self.msg_label.config(text=f"成功导入 {count} 条记录，其中 {duplicate_count} 条是重复的")
            # 导入后刷新操作页面列表
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("错误", f"导入失败：{e}")

    def refresh_table(self):
        # 清空当前列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 使用日期筛选条件
        date_str = self.date_var.get()
        try:
            # 调用 DBManager 查询当天记录，按 id 倒序排列
            rows = db_manager.query_ids_by_date(date_str, order_desc=True)
        except Exception as e:
            messagebox.showerror("错误", f"查询数据库出错：{e}")
            return
        
        # 将查询结果插入到 Treeview 中
        for row in rows:
            crawled = "是" if row[4] == 1 else "否"
            uploaded = "是" if row[5] == 1 else "否"
            fault = "有故障" if row[6] == 1 else "无故障"
            # 使用 `lambda` 捕获 `row` 的值，而不是引用
            self.tree.insert("", "end", values=(row[0], row[1], row[2], row[3], crawled, uploaded, fault), tags="row", open=False)
    
    def clear_today_imports(self):
        """
        清空今天导入的所有记录
        """
        today = datetime.date.today().isoformat()
        try:
            cursor = db_manager.conn.cursor()
            cursor.execute("DELETE FROM id_list WHERE import_time LIKE ?", (f"{today}%",))
            db_manager.conn.commit()
            messagebox.showinfo("清空", "今天的导入记录已清空")
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("错误", f"清空记录失败：{e}")

    def crawl(self):
        ignore_faults = self.ignore_faults_var.get()
        recrawl = self.re_crawl_var.get()
        answer = messagebox.askyesno("确认", f"开始爬取？\n忽略故障：{ignore_faults}\n重新爬取：{recrawl}")
        if not answer:
            return

        def crawl_thread():
            try:
                login_process()
                process_product_links()
                messagebox.showinfo("完成", "爬取操作完成")
                self.refresh_table()
            except Exception as e:
                messagebox.showerror("爬取错误", str(e))
        
        t = threading.Thread(target=crawl_thread)
        t.start()

    def upload(self):
        messagebox.showinfo("上传", "开始上传操作")

class DuplicatePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        title = tk.Label(self, text="重复ID列表", font=("Arial", 18))
        title.pack(pady=10)

        self.tree = ttk.Treeview(self, columns=("编号", "urlid", "导入时间"), show="headings", height=15)
        for col in ("编号", "urlid", "导入时间"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="center")
        self.tree.pack(pady=10, padx=10, fill="both", expand=True)

        clear_button = tk.Button(self, text="清空列表", command=self.clear_duplicate_list)
        clear_button.pack(pady=10)

    def refresh_duplicate_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            rows = db_manager.query_duplicate_ids()
            for row in rows:
                self.tree.insert("", "end", values=(row[0], row[1], row[2]))
        except Exception as e:
            messagebox.showerror("错误", f"查询重复ID列表出错：{e}")
    
    def clear_duplicate_list(self):
        db_manager.clear_duplicate_ids()
        self.refresh_duplicate_list()

if __name__ == "__main__":
    app = App()
    app.mainloop()
