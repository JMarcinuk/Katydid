from PySide6.QtWidgets import QWidget, QCheckBox, QLineEdit, QPlainTextEdit, QFormLayout, QSpinBox, QLabel, QVBoxLayout, QHBoxLayout, QPushButton

from katydid.model.library import Library
from katydid.storage.repository import MarkdownFolderRepository

class NewCollectionSlide(QWidget):

    def __init__(self, library: Library, repo: MarkdownFolderRepository, parent):
        super().__init__(parent)
        self._library = library
        self._repo = repo
        self.setObjectName("SlidePanel")
        self.setFixedWidth(480)
        
        header = QLabel("New Collection")

        self._title_field = QLineEdit()
        self._title_field.setPlaceholderText("Add Title")
        self._title_field.setMaxLength(50)

        self._description_field = QPlainTextEdit()
        self._description_field.setPlaceholderText("Add description.")

        self._limit_check_box = QCheckBox("Character limit?")
        self._limit_spin_box = QSpinBox()
        self._limit_spin_box.setEnabled(False)
        self._limit_spin_box.setRange(1, 100000)
        self._limit_spin_box.setValue(500)

        form_layout = QFormLayout()
        form_layout.addRow("Title", self._title_field)
        form_layout.addRow("Description", self._description_field)
        form_layout.addRow(self._limit_check_box, self._limit_spin_box)

        self._error_label = QLabel("")
        self._error_label.setObjectName("Error")
        self._error_label.setWordWrap(True)

        cancel_button = QPushButton("Cancel")
        cancel_button.setProperty("role", "secondary") # test later whether color makes sense
        cancel_button.clicked.connect(self.hide) # TODO: Delete after testing, temporary line
        self._create_button = QPushButton("Create")
        self._create_button.setEnabled(False)

        button_row_layout = QHBoxLayout()
        button_row_layout.addStretch()
        button_row_layout.addWidget(cancel_button)
        button_row_layout.addWidget(self._create_button)

        panel_layout = QVBoxLayout(self)
        panel_layout.addWidget(header)
        panel_layout.addLayout(form_layout)
        panel_layout.addWidget(self._error_label)
        panel_layout.addStretch()
        panel_layout.addLayout(button_row_layout)
