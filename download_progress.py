from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import QTimer


class DownloadProgress(QWidget):
    """Виджет отображения прогресса загрузки для Blitz"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.setFixedHeight(80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)

        self.status_label = QLabel("Загрузка...")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        self.percent_label = QLabel("0%")
        status_layout.addWidget(self.percent_label)

        layout.addLayout(status_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

    def update_progress(self, title: str, percent: int):
        self.title_label.setText(title)
        self.progress_bar.setValue(percent)
        self.percent_label.setText(f"{percent}%")

        if percent >= 100:
            self.status_label.setText("Загрузка завершена")
            QTimer.singleShot(2000, self.hide)
        else:
            self.status_label.setText("Загрузка...")

        if not self.isVisible():
            self.show()

    def reset(self):
        self.title_label.setText("")
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self.status_label.setText("Загрузка...")
        self.hide()
