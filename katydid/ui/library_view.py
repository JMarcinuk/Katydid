from PySide6.QtWidgets import QWidget, QPushButton, QLineEdit, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from katydid.model.library import Library
from katydid.storage.repository import MarkdownFolderRepository
from katydid.ui.new_collection_slide import NewCollectionSlide

class LibraryView(QWidget):
    def __init__(self, library: Library, repo: MarkdownFolderRepository):
        super().__init__()
        self._library = library
        self._repo = repo

        # ------------- sidebar: navigation and filtering ---------------
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(12)

        # --------- logo: persistent across views in top left ----------
        self._logo = QLabel("Katydid")
        self._logo.setObjectName("Logo")
        sidebar_layout.addWidget(self._logo)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search collections")
        sidebar_layout.addWidget(self._search)

        sidebar_layout.addStretch()

        # ----------------- top bar: context actions -------------------
        self._top_bar = QWidget()
        self._top_bar.setObjectName("TopBar")
 
        top_layout = QHBoxLayout(self._top_bar)
        top_layout.setContentsMargins(16, 10, 16, 10)
        top_layout.setSpacing(12)
 
        title = QLabel("Library")
        title.setObjectName("ScreenTitle")
 
        self._new_button = QPushButton("New Collection")
 
        top_layout.addWidget(title)
        top_layout.addStretch()
        top_layout.addWidget(self._new_button)

        # --------- content: placeholder for collection cards ----------
        content = QLabel("Your collections will appear here")
        content.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # -------- main area: top bar stacked above the content --------
        self._main_area = QWidget()
        main_layout = QVBoxLayout(self._main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._top_bar)
        main_layout.addWidget(content, stretch=1)

        # ------------ root: sidebar beside the main area ------------
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(sidebar)
        root.addWidget(self._main_area, stretch=1)

        # -------- collection slide panel: add a new collection -------
        self._new_panel = NewCollectionSlide(self._library, self._repo, parent=self._main_area)
        self._new_panel.hide()
        self._new_button.clicked.connect(self._open_panel)

    def _dock_panel(self):
        y = self._top_bar.height()
        x = self._main_area.width() - self._new_panel.width()
        self._new_panel.setGeometry(x, y, self._new_panel.width(), self._main_area.height() - y)

    def _open_panel(self):
        self._dock_panel()
        self._new_panel.show()
        self._new_panel.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._new_panel.isVisible():
            self._dock_panel()