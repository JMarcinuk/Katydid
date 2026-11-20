from PySide6.QtWidgets import QWidget, QMainWindow, QStackedWidget, QLabel
from PySide6.QtCore import Qt

from katydid.model.library import Library
from katydid.storage.repository import MarkdownFolderRepository

class MainWindow(QMainWindow):

    def __init__(self, repo: MarkdownFolderRepository, library: Library):
        super().__init__()
        self._library = library
        self._repo = repo

        self.setWindowTitle("Katydid")
        self.resize(1200, 800)
        self.setMinimumSize(800, 500)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._library_view = QLabel("Library placeholder")
        self._library_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stack.addWidget(self._library_view)

    def show_library(self):
        self._stack.setCurrentWidget(self._library_view)

    def open_collection():
        raise NotImplementedError