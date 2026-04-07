import subprocess
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox, QApplication
from PySide6.QtGui import QIcon, QAction, QPixmap, QColor
from PySide6.QtCore import QPoint, QSize


class SystemTrayManager:
    """Менеджер системного трея для Blitz Game Launcher"""

    def __init__(self, parent, main_window):
        self.parent = parent
        self.main_window = main_window
        self.tray_icon = None
        self.setup_tray()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self.parent)
        icon = QIcon()
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(88, 166, 255))
        icon.addPixmap(pixmap)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Blitz Game Launcher")

        tray_menu = QMenu()
        show_action = QAction("⚡ Показать окно", self.parent)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        exit_action = QAction("Выход", self.parent)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            self.show_window()

    def show_window(self):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def hide_window(self):
        self.main_window.hide()

    def exit_app(self):
        result = subprocess.run(["pgrep", "-f", "umu-run"], capture_output=True)
        if result.stdout:
            reply = QMessageBox.question(
                self.main_window,
                "Подтверждение выхода",
                "Есть запущенные игры. Вы уверены, что хотите выйти?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.tray_icon.hide()
                QApplication.quit()
        else:
            self.tray_icon.hide()
            QApplication.quit()
