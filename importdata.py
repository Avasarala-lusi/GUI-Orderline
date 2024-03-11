import pandas as pd
from PyQt6.QtWidgets import QProgressBar, QTableView, QListWidget, QListWidgetItem, QAbstractItemView
from PyQt6.QtCore import QAbstractTableModel, Qt, QVariant
import sqlite3


class ImportData:
    def __init__(self, table_view: QTableView, export_tableview: QTableView, multi_select: QListWidget):
        self.table_view = table_view
        self.export_tableview = export_tableview
        self.multi_select = multi_select
        self.multi_select.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.df = None


    def import_from_excel(self, progress_bar: QProgressBar, business_input: str, file_path: str):
        if file_path:
            with open(file_path, encoding='utf-8') as file:
                total_lines = sum(1 for line in file)

            chunk_size = 1000
            chunks_read = 0
            df_chunks = []

            for chunk in pd.read_csv(file_path, encoding='utf-8', chunksize=chunk_size):
                chunks_read += len(chunk)
                progress = int(chunks_read / total_lines * 100)
                if progress >= 100:
                     progress_bar.setValue(100)
                else:
                    progress_bar.setValue(progress)
                df_chunks.append(chunk)
            if progress < 100:
                progress_bar.setValue(100)
            self.df = pd.concat(df_chunks, ignore_index=True)
            self.df['业务类型'] = business_input
            columns = self.df.columns.tolist()

            model = PandasModel(self.df.head())
            self.table_view.setModel(model)

             # Display the column names in the QListWidget
            self.multi_select.clear()
            for column in columns:
                item = QListWidgetItem(column)
                self.multi_select.addItem(item)


            self.df.columns =  ['order_date', 'order_number', 'shop_number',
                                'product_code','quantity', 'length_cm', 'width_cm',
                                'height_cm' ,'business_type']

    def master_data(self):
        master_df = self.df.copy()
        master_df = master_df.drop_duplicates(subset=['product_code'])
        master_df.loc[:, 'volume_cm3'] = master_df['length_cm'] * master_df['width_cm'] * master_df['height_cm']
        master_df = master_df[['product_code', 'length_cm', 'width_cm', 'height_cm', 'volume_cm3']]
        return master_df
    
    def order_data(self,selected_pos):
        group_list = [self.df.columns[i] for i in selected_pos]
        order_df = self.df.groupby(group_list)['quantity'].sum().reset_index()

        if 'shop_number' not in order_df.columns:
            order_df['shop_number'] = None
        if 'order_number' not in order_df.columns:
            order_df['order_number'] = None

        order_df = order_df[['order_date', 'order_number', 'shop_number',
                             'product_code', 'quantity', 'business_type']]

        return order_df

    def orderline_data(self, capacity):
        conn = sqlite3.connect('mydatabase.db')
        cursor = conn.cursor()
        
        cursor.execute("""
           SELECT od.order_id, od.order_date, od.product_code, 
                  od.order_number, 
                  od.shop_number,
                  md.volume_cm3 * od.quantity as product_volume,
                  od.quantity, od.business_type
            FROM orderData od
            LEFT JOIN masterData md
            ON od.product_code = md.product_code   
                       """)
        orderline_data = cursor.fetchall()
        conn.close()

        orderline_df = pd.DataFrame(orderline_data, columns=[
            'order_id', 'order_date', 'product_code', 
            'order_number', 
            'shop_number',
            'product_volume',
            'product_quantity', 
            'business_type'
        ])
        orderline_df['capacity_factor'] = capacity
        orderline_df['orderline_quantity'] = orderline_df['product_volume'].apply(lambda x: 1
            if x <= (24000000 *  capacity / 100) 
            else -(- x // (24000000 * capacity / 100)))
        
        return orderline_df

    def store_master(self, df1):
        conn = sqlite3.connect('mydatabase.db')
        cursor = conn.cursor()
        # Define the SQL CREATE TABLE statement with column names and data types
        create_master_sql = """
        CREATE TABLE IF NOT EXISTS masterData (
            product_code TEXT PRIMARY KEY,
            length_cm REAL NOT NULL CHECK(length_cm > 0),
            width_cm REAL  NOT NULL CHECK(width_cm > 0),
            height_cm REAL NOT NULL CHECK(height_cm > 0),
            volume_cm3 REAL NOT NULL CHECK(volume_cm3 > 0) 
        );
        """
        conn.execute(create_master_sql)

        df1['product_code'] = df1['product_code'].astype(str)
        existing_product_codes = set(pd.read_sql_query("SELECT product_code FROM masterData", conn)['product_code'])
        new_data = df1.loc[~df1['product_code'].isin(existing_product_codes)]
        new_data.to_sql('masterData', conn, if_exists='append', index=False)
        
        conn.close


    def store_order(self, df):
        conn = sqlite3.connect('mydatabase.db')
        conn.execute('PRAGMA foreign_keys = ON;')

        create_order_sql = """
        CREATE TABLE IF NOT EXISTS orderData(
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT,
            shop_number TEXT,
            product_code TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            order_date DATE NOT NULL,
            business_type TEXT NOT NULL,
            FOREIGN KEY (product_code) REFERENCES masterData(product_code)
        );
        """
        conn.execute(create_order_sql)

        try:
            df.to_sql('orderData', conn, if_exists='append', index=False)
        except sqlite3.IntegrityError as e:
            print(f"发现了重复的商品编码, 未插入重复的记录")
        conn.close

    def store_orderline(self, df):
        conn = sqlite3.connect('mydatabase.db')
        conn.execute('PRAGMA foreign_keys = ON;')

        create_orderline_sql = """
        CREATE TABLE IF NOT EXISTS orderlineData(
            detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date DATE NOT NULL,
            product_code TEXT NOT NULL,
            order_number TEXT,
            shop_number TEXT,
            order_id INTEGER NOT NULL,
            product_quantity INTEGER NOT NULL,
            product_volume REAL NOT NULL,
            capacity_factor INTEGER NOT NULL,
            orderline_quantity INTEGER NOT NULL,
            business_type TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orderData(order_id),
            FOREIGN KEY (product_code) REFERENCES masterData(product_code)
        )"""

        conn.execute(create_orderline_sql)

        try:
            df.to_sql('orderlineData', conn, if_exists='append', index=False)
        except sqlite3.IntegrityError as e:
            print(f"Error: {e}. Duplicate order found, record not inserted.")
        conn.close
    
    def export_excel(self):
        conn = sqlite3.connect('mydatabase.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT order_date,
            business_type,
            capacity_factor,
            orderline_quantity
            FROM orderlineData
            """)
        exported_object = cursor.fetchall()
        conn.close()

        df = pd.DataFrame(exported_object, columns=[
            '日期',
            '业务类型',
            '容纳系数',
            '订单行数量'])
        
        exported_df = df.groupby(['日期', '业务类型'])['订单行数量'].sum().reset_index()
        exported_df['容纳系数'] = df['容纳系数'][0]
        model_2 = PandasModel(exported_df)
        self.export_tableview.setModel(model_2)

        return exported_df
    
    def clear_data(self):
        self.df = None


class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        QAbstractTableModel.__init__(self)
        self._data = data
        self.header_labels = data.columns.tolist()

    def rowCount(self, parent=None):
        return len(self._data.values)
    
    def columnCount(self, parent=None):
        return self._data.columns.size
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.header_labels[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole:
                return str(self._data.values[index.row()][index.column()])
        return QVariant()
    
    
        