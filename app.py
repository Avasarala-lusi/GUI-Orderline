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
        self.lineEdit.setVisible(True)
        self.label.setVisible(True)
        self.progressBar.setVisible(False)
        self.label_2.setVisible(False)
        self.tableView.setVisible(False)
        self.table_view = self.tableView
        self.multiSelect.setVisible(False)
        self.multi_select = self.multiSelect

        self.maindf = None


    def import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Open CSV File", "", "CSV Files (*.csv)")
        if file_path: 
            # self.importButton.setVisible(False)
            # self.lineEdit.setVisible(False)
            # self.label.setVisible(False)
            import_data = ImportData(self.table_view, self.multi_select)
            # GeT the text from the QLineEdit widget
            businiess_type = self.lineEdit.text()
            self.progressBar.setVisible(True)
            
            import_data.import_from_excel(self.progressBar, businiess_type, file_path)
            self.maindf = import_data.df
            import_data.store_master(import_data.master_data(self.maindf))

            self.progressBar.setVisible(False)
            self.tableView.setVisible(True)
            self.label_2.setVisible(True)
            self.multiSelect.setVisible(True)
            self.groupButton.setVisible(True)

    def calculate_result(self):
        #  Get the list of selected items, include business type
        selected_items = [item.text() for item in self.multi_select.selectedItems()] 
        import_data = ImportData(self.table_view, self.multi_select)
        import_data.store_order(import_data.order_data(self.maindf, selected_items))
        import_data.store_orderline(import_data.orderline_data(self.maindf))



        
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


