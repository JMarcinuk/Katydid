import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QStandardPaths

from katydid.ui.main_window import MainWindow
from katydid.ui.theme import apply_theme
from katydid.storage.repository import MarkdownFolderRepository

def main():
    app = QApplication(sys.argv)

    app.setApplicationName("Katydid")
    theme = apply_theme(app, "default-dark")

    library_folder = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    repo = MarkdownFolderRepository(library_folder)
    try:
        library = repo.load_library()
    except ValueError as err:
        QMessageBox.critical(None, "Couldn't open your library", str(err))
        sys.exit(1)

    window = MainWindow(repo=repo, library=library)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()