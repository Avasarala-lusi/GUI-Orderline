import pandas as pd
from PyQt6.QtWidgets import QProgressBar, QTableView, QListWidget, QListWidgetItem, QAbstractItemView
from PyQt6.QtCore import QAbstractTableModel, Qt, QVariant
import sqlite3


class ImportData:
    def __init__(self, table_view: QTableView, multi_select: QListWidget):
        self.table_view = table_view
        self.multi_select = multi_select
        self.multi_select.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)


    def import_from_excel(self, progress_bar: QProgressBar, business_input: str, file_path: str):
        if file_path:
            with open(file_path, encoding='gbk') as file:
                total_lines = sum(1 for line in file)

            chunk_size = 1000
            chunks_read = 0
            df_chunks = []

            for chunk in pd.read_csv(file_path, encoding='gbk', chunksize=chunk_size):
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
    

    def master_data(self, df):
        master_df = df.drop_duplicates(subset=['货号'])
        master_df = master_df.rename(columns={'货号': 'product_code', '长': 'length_cm', '宽': 'width_cm', '高': 'height_cm'})
        master_df.loc[:, 'volume_cm3'] = master_df['length_cm'] * master_df['width_cm'] * master_df['height_cm']
        master_df = master_df[['product_code', 'length_cm', 'width_cm', 'height_cm', 'volume_cm3']]
        return master_df
    
    def order_data(self, df):
        order_df = df.rename(columns={'日期': 'order_date', '订单编号': 'order_number', '店铺号': 'shop_number', '货号': 'product_code',
                                      '订货数量': 'quantity', '业务类型':'business_type'}, errors='ignore')
        # order_df = order_df.groupby(selected_items)['quantity'].sum()

    def orderline_data(self,df):
        pass

    def store_data(self, df1):
        conn = sqlite3.connect('mydatabase.db')
        conn.execute('PRAGMA foreign_keys = ON;')
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

        create_order_sql = """
        CREATE TABLE IF NOT EXISTS orderData(
            order_id PRIMARY KEY AUTOINCREMENT,
            order_number TEXT,
            shop_number TEXT,
            FOREIGN KEY (product_code) REFERENCES masterData(product_code) NOT NULL,
            quantity INTEGER NOT NULL,
            order_date DATE NOT NULL,
            business_type TEXT NOT NULL
        )"""

        create_orderline_sql = """
        CREATE TABLE IF NOT EXISTS orderlineData(
            detail_id PRIMARY KEY AUTOINCREMENT,
            order_date DATE NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orderData(order_id) NOT NULL,
            order_number TEXT,
            shop_number TEXT,
            FOREIGN KEY (product_code) REFERENCES masterData(product_code) NOT NULL,
            product_quantity INTEGER NOT NULL,
            volume_cm3 REAL NOT NULL,
            capacity_factor INTEGER NOT NULL,
            orderline_quantity INTEGER NOT NULL,
            business_type TEXT NOT NULL
        )"""

        conn.execute(create_master_sql)
        # conn.execute(create_order_sql)
        # conn.execute(create_orderline_sql)

        try:
            df1.to_sql('masterData', conn, if_exists='append', index=False)
            # df2.to_sql('orderData', conn, if_exists='append', index=False)
            # df3.to_sql('orderlineData', conn, if_exists='append', index=False)
            print("Success!")
        except sqlite3.IntegrityError as e:
            print(f"Error: {e}. Duplicate product code found, record not inserted.")
        conn.close

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
    
        