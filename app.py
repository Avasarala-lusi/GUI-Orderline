import sys
from PyQt6.QtWidgets import QApplication,QMainWindow, QFileDialog
from mainwindow_ui import Ui_MainWindow
from importdata import ImportData

# Subclass QMainWindow to customise your application's main window
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.importButton.setVisible(True)
        self.groupButton.setVisible(False)
        self.importButton.clicked.connect(self.import_csv)
        self.groupButton.clicked.connect(self.calculate_result)
        self.downloadButton.clicked.connect(self.download_excel)
        self.lineEdit.setVisible(True)
        self.lineEdit_2.setVisible(False)
        self.label.setVisible(True)
        self.progressBar.setVisible(False)
        self.label_2.setVisible(False)
        self.label_4.setVisible(False)
        self.tableView.setVisible(False)
        self.table_view = self.tableView
        self.export_tableview = self.exporttableView
        self.multiSelect.setVisible(False)
        self.multi_select = self.multiSelect

        self.import_data = ImportData(self.table_view, self.export_tableview, self.multi_select)

        self.final_ex = None

    def import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Open CSV File", "", "CSV Files (*.csv)")
        if file_path: 

            self.import_data.clear_data()
            businiess_type = self.lineEdit.text()
            self.progressBar.setVisible(True)
            
            self.import_data.import_from_excel(self.progressBar, businiess_type, file_path)
            self.import_data.store_master(self.import_data.master_data())

            self.progressBar.setVisible(False)
            self.tableView.setVisible(True)
            self.label_2.setVisible(True)
            self.multiSelect.setVisible(True)
            self.groupButton.setVisible(True)
            self.lineEdit_2.setVisible(True)
            self.label_4.setVisible(True)

    def calculate_result(self): 
        #  Get the list of selected items, include business type
        selected_positions = [self.multi_select.row(item)  for item in self.multi_select.selectedItems()]
        
        self.import_data.store_order(self.import_data.order_data(selected_positions))

        capacity = int(self.lineEdit_2.text())
        self.import_data.store_orderline(self.import_data.orderline_data(capacity))
        self.final_ex = self.import_data.export_excel()

    def download_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Excel File", "", "Excel Files (*.xlsx)")
        if file_path:
            self.final_ex.to_excel(file_path, index=False)

        
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


