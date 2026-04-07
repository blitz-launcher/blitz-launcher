from PySide6.QtCore import QPoint, QPropertyAnimation, QParallelAnimationGroup, QTimer, QEasingCurve, QRect, Qt
from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor
from icon_factory import IconFactory


class Notification(QFrame):

    def __init__(
        self,
        parent: QWidget,
        title: str,
        message: str,
        kind: str = "info",
        icon_code: str = "",
        action_text: str = "",
        action_callback=None,
    ):
        super().__init__(parent)
        self.setObjectName("steam_notification")
        self.setProperty("kind", kind)
        self.setFixedSize(340, 84)

        self._target_pos = QPoint()
        self._progress_anim = None
        self._life_timer = QTimer(self)
        self._life_timer.setSingleShot(True)
        self._life_timer.timeout.connect(self.hide_animated)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 140))
        self.setGraphicsEffect(shadow)

        self.setWindowOpacity(0.0)

        self._action_callback = action_callback
        self._build_ui(title, message, icon_code, action_text)
        self.hide()

    def _build_ui(self, title: str, message: str, icon_code: str, action_text: str):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        if icon_code:
            icon = QLabel(icon_code)
            icon.setObjectName("notification_icon")
            icon.setFont(IconFactory.get_font(16))
            icon.setFixedWidth(18)
            layout.addWidget(icon)
        else:
            accent = QLabel("●")
            accent.setObjectName("notification_accent")
            accent.setFixedWidth(14)
            layout.addWidget(accent)

        text_layout = QHBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(10)

        body = QFrame()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("notification_title")
        title_label.setWordWrap(False)
        body_layout.addWidget(title_label)

        sep = QLabel("—")
        sep.setObjectName("notification_sep")
        body_layout.addWidget(sep)

        message_label = QLabel(message)
        message_label.setObjectName("notification_message")
        message_label.setWordWrap(True)
        body_layout.addWidget(message_label, 1)

        text_layout.addWidget(body, 1)
        if action_text:
            action_btn = QPushButton(action_text)
            action_btn.setObjectName("notification_action")
            action_btn.setCursor(Qt.PointingHandCursor)
            action_btn.setFlat(True)
            action_btn.clicked.connect(self._on_action_clicked)
            text_layout.addWidget(action_btn, 0)
        layout.addLayout(text_layout, 1)
        root_layout.addLayout(layout, 1)

        self.progress_bar = QFrame()
        self.progress_bar.setObjectName("notification_progress")
        self.progress_bar.setFixedHeight(3)
        root_layout.addWidget(self.progress_bar)

    def _calc_position(self) -> QPoint:
        parent_rect = self.parent().rect()
        margin = 16
        return QPoint(
            parent_rect.width() - self.width() - margin,
            parent_rect.height() - self.height() - margin
        )

    def show_animated(self, duration_ms: int = 2600):
        self._target_pos = self._calc_position()
        start_pos = QPoint(self._target_pos.x() + 22, self._target_pos.y() + 20)
        self.move(start_pos)
        self.show()
        self.raise_()

        pos_anim = QPropertyAnimation(self, b"pos")
        pos_anim.setDuration(240)
        pos_anim.setStartValue(start_pos)
        pos_anim.setEndValue(self._target_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)

        opacity_in = QPropertyAnimation(self, b"windowOpacity")
        opacity_in.setDuration(240)
        opacity_in.setStartValue(0.0)
        opacity_in.setEndValue(1.0)
        opacity_in.setEasingCurve(QEasingCurve.OutCubic)

        in_group = QParallelAnimationGroup(self)
        in_group.addAnimation(pos_anim)
        in_group.addAnimation(opacity_in)
        in_group.start()

        self._start_progress(duration_ms)
        self._life_timer.start(duration_ms)

    def _start_progress(self, duration_ms: int):
        bar_height = self.progress_bar.height()
        start_rect = QRect(0, 0, self.width(), bar_height)
        end_rect = QRect(0, 0, 0, bar_height)
        self.progress_bar.setGeometry(start_rect)

        self._progress_anim = QPropertyAnimation(self.progress_bar, b"geometry", self)
        self._progress_anim.setDuration(duration_ms)
        self._progress_anim.setStartValue(start_rect)
        self._progress_anim.setEndValue(end_rect)
        self._progress_anim.setEasingCurve(QEasingCurve.Linear)
        self._progress_anim.start()

    def hide_animated(self):
        if not self.isVisible():
            return
        self._life_timer.stop()
        if self._progress_anim:
            self._progress_anim.stop()

        end_pos = QPoint(self._target_pos.x() + 16, self._target_pos.y() + 14)

        pos_anim = QPropertyAnimation(self, b"pos")
        pos_anim.setDuration(200)
        pos_anim.setStartValue(self.pos())
        pos_anim.setEndValue(end_pos)
        pos_anim.setEasingCurve(QEasingCurve.InCubic)

        opacity_out = QPropertyAnimation(self, b"windowOpacity")
        opacity_out.setDuration(200)
        opacity_out.setStartValue(self.windowOpacity())
        opacity_out.setEndValue(0.0)
        opacity_out.setEasingCurve(QEasingCurve.InCubic)

        out_group = QParallelAnimationGroup(self)
        out_group.addAnimation(pos_anim)
        out_group.addAnimation(opacity_out)
        out_group.finished.connect(self.deleteLater)
        out_group.start()

    def mousePressEvent(self, event):
        self.hide_animated()
        event.accept()

    def _on_action_clicked(self):
        if callable(self._action_callback):
            self._action_callback()
        self.hide_animated()
