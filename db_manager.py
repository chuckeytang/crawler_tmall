# db_manager.py
import sqlite3
import os
import datetime

class DBManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self._create_db()

    def _create_db(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        self.conn = sqlite3.connect(self.db_path)
        self._create_table_id_list()
        self._create_table_duplicate_ids()

    def _create_table_id_list(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS id_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urlid TEXT NOT NULL,
                url TEXT NOT NULL,
                import_time TEXT NOT NULL,
                crawled INTEGER DEFAULT 0,
                uploaded INTEGER DEFAULT 0,
                has_fault INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    def _create_table_duplicate_ids(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS duplicate_ids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urlid TEXT NOT NULL,
                import_time TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def import_ids_from_file(self, file_path):
        """
        从txt文件中读取id，每行一个id，
        自动拼接生成天猫商品链接，并记录当前导入时间。
        检查是否重复，若重复，则存入重复id表。
        返回导入成功的记录数。
        """
        count = 0
        duplicate_count = 0
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today_date = datetime.datetime.now().strftime("%Y-%m-%d")  # 用于判断是否是同一天的重复id

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                id_val = line.strip()
                if id_val:
                    url = f"https://detail.tmall.com/item.htm?id={id_val}"
                    # 检查该 id 是否在同一天内已存在
                    if self._is_duplicate_id(id_val, today_date):
                        # 将重复 id 插入重复 id 表
                        self.insert_duplicate_id(urlid=id_val, import_time=now_str)
                        duplicate_count += 1
                    else:
                        self.insert_id(urlid=id_val, url=url, import_time=now_str)
                    count += 1
        self.conn.commit()
        return count, duplicate_count

    def insert_id(self, urlid, url, import_time):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO id_list (urlid, url, import_time, crawled, uploaded, has_fault)
            VALUES (?, ?, ?, 0, 0, 0)
        ''', (urlid, url, import_time))
        self.conn.commit()

    def insert_duplicate_id(self, urlid, import_time):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO duplicate_ids (urlid, import_time)
            VALUES (?, ?)
        ''', (urlid, import_time))
        self.conn.commit()

    def _is_duplicate_id(self, urlid, date_str):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM id_list
            WHERE urlid = ? AND import_time LIKE ?
        ''', (urlid, f"{date_str}%"))
        count = cursor.fetchone()[0]
        return count > 0  # 如果返回值大于 0，则说明该 id 已经在同一天出现过

    def query_ids_by_date(self, date_str, order_desc=False):
        """
        根据日期筛选记录，date_str 格式为 'YYYY-MM-DD'。
        参数 order_desc 为 True 时按 import_time 倒序排列，默认为 False。
        """
        cursor = self.conn.cursor()
        like_pattern = f"{date_str}%"
        order = "DESC" if order_desc else "ASC"
        cursor.execute(f'''
            SELECT id, urlid, url, import_time, crawled, uploaded, has_fault
            FROM id_list
            WHERE import_time LIKE ?
            ORDER BY id {order}
        ''', (like_pattern,))
        return cursor.fetchall()

    def query_duplicate_ids(self):
        """
        查询重复 id 列表
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, urlid, import_time
            FROM duplicate_ids
            ORDER BY id DESC
        ''')
        return cursor.fetchall()

    def clear_duplicate_ids(self):
        """
        清空重复 id 列表
        """
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM duplicate_ids')
        self.conn.commit()

    def _create_table_product_info(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_date TEXT NOT NULL,
                check_date TEXT,
                platform TEXT NOT NULL,
                shop_id TEXT NOT NULL,
                shop_name TEXT NOT NULL,
                spu_url TEXT NOT NULL,
                product_url TEXT NOT NULL,
                category_level_1 TEXT,
                category_level_2 TEXT,
                category_level_3 TEXT,
                brand_name TEXT,
                spu_code TEXT,
                spu_name TEXT,
                sku_code TEXT,
                sku_name TEXT,
                sku_sale_status TEXT,
                specification TEXT,
                parameter_info TEXT,
                total_comments INTEGER,
                sales INTEGER,
                marked_price TEXT,
                final_price TEXT,
                discount_info TEXT,
                delivery_area TEXT,
                product_image TEXT,
                crawl_time TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def save_product_info(self, collection_date, check_date, platform, shop_id, shop_name, spu_url, product_url, 
                           category_level_1, category_level_2, category_level_3, brand_name, spu_code, spu_name, 
                           sku_code, sku_name, sku_sale_status, specification, parameter_info, total_comments, sales, 
                           marked_price, final_price, discount_info, delivery_area, product_image):
        crawl_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO product_info (
                collection_date, check_date, platform, shop_id, shop_name, spu_url, product_url, category_level_1, 
                category_level_2, category_level_3, brand_name, spu_code, spu_name, sku_code, sku_name, sku_sale_status, 
                specification, parameter_info, total_comments, sales, marked_price, final_price, discount_info, 
                delivery_area, product_image, crawl_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (collection_date, check_date, platform, shop_id, shop_name, spu_url, product_url, category_level_1, 
              category_level_2, category_level_3, brand_name, spu_code, spu_name, sku_code, sku_name, sku_sale_status, 
              specification, parameter_info, total_comments, sales, marked_price, final_price, discount_info, 
              delivery_area, product_image, crawl_time))
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()

    def close(self):
        if self.conn:
            self.conn.close()

db_manager = DBManager("./data/mydatabase.db")