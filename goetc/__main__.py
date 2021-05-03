import sys
from PyQt5.QtWidgets import QApplication
from goetc.mainwindow import MainWindow


if __name__ == '__main__':
    app = QApplication(sys.argv)
    frame = MainWindow()
    frame.show()
    app.exec_()
