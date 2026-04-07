import os
import sys
import subprocess
import json
import urllib.parse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QMessageBox, QFileDialog, QDialog, QSystemTrayIcon, QMenu,
    QListView, QAbstractItemView, QStyledItemDelegate, QStyle, QStackedWidget,
    QProgressBar, QGraphicsBlurEffect, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsView, QCheckBox, QComboBox, QScrollArea, QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, QSize, QRect, QModelIndex, QPoint, Signal, QTimer,
    QAbstractListModel, QEvent, QUrl, QPropertyAnimation, QEasingCurve
)
from PySide6.QtGui import (
    QFont, QPixmap, QPainter, QColor, QBrush, QPen, QAction, QIcon,
    QFontMetrics, QPainterPath, QFontDatabase, QDesktopServices
)

from game_database import GameDatabase
from icon_factory import IconFactory
from profile_manager import ProfileManagerDialog
from proton_manager import SystemChecker


class GameDetailsPage(QWidget):
    """Страница с детальной информацией об игре в Blitz"""

    back_clicked = Signal()
    play_clicked = Signal()

    def __init__(self, db: GameDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_game_id = None
        self.blur_pixmap = None
        self.fa_font = None
        self.selected_profile_id = None
        self.selected_profile = None
        self.available_proton_versions = ["System Default"]
        self._loading = False
        self._block_save = False

        self.setup_ui()
        IconFactory.load_font()
        self.fa_font = IconFactory.get_font(16)
        self.settings_status_timer = QTimer(self)
        self.settings_status_timer.setSingleShot(True)
        self.settings_status_timer.timeout.connect(self._fade_settings_status)
        self.settings_status_animation = None

    def save_settings(self):
        """Сохранить текущие настройки в БД сразу при переключении."""
        if not self.current_game_id or self._loading or self._block_save:
            return

        settings = {
            'mangohud': self.mangohud_check.isChecked(),
            'gamemode': self.gamemode_check.isChecked(),
            'esync': self.esync_check.isChecked(),
            'fsync': self.fsync_check.isChecked(),
            'ntsync': self.ntsync_check.isChecked(),
            'dxvk': self.dxvk_check.isChecked(),
            'vkbasalt': self.vkbasalt_check.isChecked(),
            'fsr': self.fsr_check.isChecked(),
            'dlss': self.dlss_check.isChecked(),
            'proton_version': self.proton_version_combo.currentText(),
            'dxvk_version': self.dxvk_version_combo.currentText(),
            'fsr_level': self.fsr_level_combo.currentText(),
            'selected_profile_id': self.selected_profile_id
        }

        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO game_settings (
                    game_id, mangohud, gamemode, esync, fsync, esunc, fsunc, ntsync,
                    dxvk, vkbasalt, fsr, dlss, proton_version, dxvk_version, fsr_level,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
            """, (
                self.current_game_id,
                1 if settings['mangohud'] else 0,
                1 if settings['gamemode'] else 0,
                1 if settings['esync'] else 0,
                1 if settings['fsync'] else 0,
                1 if settings['esync'] else 0,
                1 if settings['fsync'] else 0,
                1 if settings['ntsync'] else 0,
                1 if settings['dxvk'] else 0,
                1 if settings['vkbasalt'] else 0,
                1 if settings['fsr'] else 0,
                1 if settings['dlss'] else 0,
                settings['proton_version'],
                settings['dxvk_version'],
                settings['fsr_level'],
            ))

        print(f"💾 Сохранены настройки для игры {self.current_game_id} в БД")
        self._show_settings_status("Сохранено...")

    def save_current_settings(self):
        """Совместимость со старыми подключениями сигналов."""
        self.save_settings()

    def load_settings_from_db(self):
        """Загрузить настройки из БД"""
        if not self.current_game_id:
            return

        self._loading = True
        toggle_widgets = [
            self.mangohud_check,
            self.gamemode_check,
            self.esync_check,
            self.fsync_check,
            self.ntsync_check,
            self.dxvk_check,
            self.vkbasalt_check,
            self.fsr_check,
            self.dlss_check,
        ]
        combo_widgets = [self.proton_version_combo, self.dxvk_version_combo, self.fsr_level_combo]
        try:
            settings = self.db.get_game_settings(self.current_game_id)

            for widget in toggle_widgets + combo_widgets:
                widget.blockSignals(True)

            self.mangohud_check.setChecked(bool(settings.get('mangohud', 0)))
            self.gamemode_check.setChecked(bool(settings.get('gamemode', 0)))
            self.esync_check.setChecked(bool(settings.get('esync', 0)))
            self.fsync_check.setChecked(bool(settings.get('fsync', 0)))
            self.ntsync_check.setChecked(bool(settings.get('ntsync', settings.get('ntsunc', 0))))
            self.dxvk_check.setChecked(bool(settings.get('dxvk', 0)))
            self.vkbasalt_check.setChecked(bool(settings.get('vkbasalt', 0)))
            self.fsr_check.setChecked(bool(settings.get('fsr', 0)))
            self.dlss_check.setChecked(bool(settings.get('dlss', 0)))

            proton_version = settings.get('proton_version', 'System Default')
            idx = self.proton_version_combo.findText(proton_version)
            if idx < 0:
                self.proton_version_combo.addItem(proton_version)
                idx = self.proton_version_combo.findText(proton_version)
            if idx >= 0:
                self.proton_version_combo.setCurrentIndex(idx)

            dxvk_version = settings.get('dxvk_version', '2.5.3 (стабильная)')
            idx = self.dxvk_version_combo.findText(dxvk_version)
            if idx >= 0:
                self.dxvk_version_combo.setCurrentIndex(idx)

            fsr_level = settings.get('fsr_level', 'Качество')
            idx = self.fsr_level_combo.findText(fsr_level)
            if idx >= 0:
                self.fsr_level_combo.setCurrentIndex(idx)

            self.selected_profile_id = settings.get('selected_profile_id')
            if self.selected_profile_id:
                idx = self.profile_combo.findData(self.selected_profile_id)
                if idx >= 0:
                    self.profile_combo.setCurrentIndex(idx)

            print(f"📁 Загружены настройки для игры {self.current_game_id} из БД")
        finally:
            for widget in toggle_widgets + combo_widgets:
                widget.blockSignals(False)
            self._loading = False

    def setup_ui(self):
        """Настройка интерфейса Blitz"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_widget.setAttribute(Qt.WA_TranslucentBackground)
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(60, 40, 60, 40)
        content_layout.setSpacing(40)

        # ========== ЛЕВАЯ ЧАСТЬ - ОБЛОЖКА ==========
        left_widget = QWidget()
        left_widget.setObjectName("left_widget")
        left_widget.setMinimumWidth(200)
        left_widget.setMaximumWidth(300)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)

        self.cover_label = QLabel()
        self.cover_label.setObjectName("cover_label")
        self.cover_label.setMinimumSize(150, 225)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setScaledContents(True)
        left_layout.addWidget(self.cover_label)

        self.back_btn = QPushButton()
        self.back_btn.setObjectName("back_btn")
        self.back_btn.setText("\uf060  Назад")
        self.back_btn.setFont(IconFactory.get_font(13))
        self.back_btn.clicked.connect(self.back_clicked.emit)
        left_layout.addWidget(self.back_btn)

        left_layout.addStretch()

        # ========== ПРАВАЯ ЧАСТЬ - ИНФОРМАЦИЯ ==========
        right_widget = QWidget()
        right_widget.setObjectName("right_widget")
        right_widget.setMinimumWidth(350)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(20)

        self.title_label = QLabel()
        self.title_label.setObjectName("title_label")
        self.title_label.setWordWrap(True)
        right_layout.addWidget(self.title_label)

        # Информационная панель
        info_frame = QFrame()
        info_frame.setObjectName("info_frame")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(16)
        info_layout.setContentsMargins(16, 16, 16, 16)

        # Время в игре
        playtime_layout = QHBoxLayout()
        playtime_layout.setSpacing(12)
        playtime_icon = QLabel("\uf017")
        playtime_icon.setFont(IconFactory.get_font(18))
        playtime_icon.setFixedWidth(24)
        playtime_layout.addWidget(playtime_icon)

        self.playtime_label = QLabel("0 часов")
        self.playtime_label.setWordWrap(True)
        playtime_layout.addWidget(self.playtime_label)
        playtime_layout.addStretch()
        info_layout.addLayout(playtime_layout)

        # Последний запуск
        last_played_layout = QHBoxLayout()
        last_played_layout.setSpacing(12)
        last_played_icon = QLabel("\uf017")
        last_played_icon.setFont(IconFactory.get_font(18))
        last_played_icon.setFixedWidth(24)
        last_played_layout.addWidget(last_played_icon)

        self.last_played_label = QLabel("Никогда")
        self.last_played_label.setWordWrap(True)
        last_played_layout.addWidget(self.last_played_label)
        last_played_layout.addStretch()
        info_layout.addLayout(last_played_layout)

        # Количество запусков
        launches_layout = QHBoxLayout()
        launches_layout.setSpacing(12)
        launches_icon = QLabel("\uf0c2")
        launches_icon.setFont(IconFactory.get_font(18))
        launches_icon.setFixedWidth(24)
        launches_layout.addWidget(launches_icon)

        self.launches_label = QLabel("0 запусков")
        self.launches_label.setWordWrap(True)
        launches_layout.addWidget(self.launches_label)
        launches_layout.addStretch()
        info_layout.addLayout(launches_layout)

        # Версия Proton
        proton_layout = QHBoxLayout()
        proton_layout.setSpacing(12)
        proton_icon = QLabel("\uf2db")
        proton_icon.setFont(IconFactory.get_font(18))
        proton_icon.setFixedWidth(24)
        proton_layout.addWidget(proton_icon)

        self.proton_label = QLabel("Не указана")
        self.proton_label.setWordWrap(True)
        proton_layout.addWidget(self.proton_label)
        proton_layout.addStretch()
        info_layout.addLayout(proton_layout)

        right_layout.addWidget(info_frame)

        # ========== ПАНЕЛЬ ПРОФИЛЕЙ ==========
        profile_frame = QFrame()
        profile_frame.setObjectName("profile_frame")
        profile_layout = QVBoxLayout(profile_frame)
        profile_layout.setSpacing(8)

        profile_header = QLabel("🎮 ПРОФИЛЬ ЗАПУСКА")
        profile_header.setObjectName("profile_header")
        profile_layout.addWidget(profile_header)

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumHeight(32)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        profile_layout.addWidget(self.profile_combo)

        profile_buttons = QHBoxLayout()
        profile_buttons.setSpacing(8)
        self.manage_profiles_btn = QPushButton("📁 Управление профилями")
        self.manage_profiles_btn.setFont(IconFactory.get_font(11))
        self.manage_profiles_btn.setMinimumHeight(28)
        self.manage_profiles_btn.clicked.connect(self.open_profile_manager)
        profile_buttons.addWidget(self.manage_profiles_btn)

        self.refresh_profiles_btn = QPushButton("🔄 Обновить")
        self.refresh_profiles_btn.setFont(IconFactory.get_font(11))
        self.refresh_profiles_btn.setMinimumHeight(28)
        self.refresh_profiles_btn.clicked.connect(self.load_profiles)
        profile_buttons.addWidget(self.refresh_profiles_btn)
        profile_buttons.addStretch()
        profile_layout.addLayout(profile_buttons)

        right_layout.addWidget(profile_frame)

        # ========== НАСТРОЙКИ ЗАПУСКА ==========
        settings_frame = QFrame()
        settings_frame.setObjectName("settings_frame")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setSpacing(8)

        settings_header = QLabel("⚙️ НАСТРОЙКИ ЗАПУСКА")
        settings_header.setObjectName("settings_header")
        settings_layout.addWidget(settings_header)

        self.settings_status_label = QLabel("")
        self.settings_status_label.setObjectName("settings_status_label")
        self.settings_status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.settings_status_opacity = QGraphicsOpacityEffect(self.settings_status_label)
        self.settings_status_opacity.setOpacity(0.0)
        self.settings_status_label.setGraphicsEffect(self.settings_status_opacity)
        settings_layout.addWidget(self.settings_status_label)

        # MangoHud
        mango_row = QHBoxLayout()
        mango_row.setSpacing(12)
        mango_icon = QLabel("\uf2db")
        mango_icon.setFont(IconFactory.get_font(14))
        mango_icon.setFixedWidth(24)
        mango_row.addWidget(mango_icon)

        mango_label = QLabel("MangoHud (оверлей производительности)")
        mango_label.setWordWrap(True)
        mango_row.addWidget(mango_label)
        mango_row.addStretch()

        self.mangohud_check = QCheckBox()
        self.mangohud_check.stateChanged.connect(self.save_settings)
        mango_row.addWidget(self.mangohud_check)
        settings_layout.addLayout(mango_row)

        # Gamemode
        gamemode_row = QHBoxLayout()
        gamemode_row.setSpacing(12)
        gamemode_icon = QLabel("\uf2db")
        gamemode_icon.setFont(IconFactory.get_font(14))
        gamemode_icon.setFixedWidth(24)
        gamemode_row.addWidget(gamemode_icon)

        gamemode_label = QLabel("Gamemode (автоматический режим производительности)")
        gamemode_label.setWordWrap(True)
        gamemode_row.addWidget(gamemode_label)
        gamemode_row.addStretch()

        self.gamemode_check = QCheckBox()
        self.gamemode_check.stateChanged.connect(self.save_settings)
        gamemode_row.addWidget(self.gamemode_check)
        settings_layout.addLayout(gamemode_row)

        # Esync
        esync_row = QHBoxLayout()
        esync_row.setSpacing(12)
        esync_label = QLabel("Esync (Eventfd синхронизация)")
        esync_label.setWordWrap(True)
        esync_label.setFixedWidth(200)
        esync_row.addWidget(esync_label)
        esync_row.addStretch()

        self.esync_check = QCheckBox()
        self.esync_check.stateChanged.connect(self.save_settings)
        esync_row.addWidget(self.esync_check)
        settings_layout.addLayout(esync_row)

        # Fsync
        fsync_row = QHBoxLayout()
        fsync_row.setSpacing(12)
        fsync_label = QLabel("Fsync (Futex синхронизация)")
        fsync_label.setWordWrap(True)
        fsync_label.setFixedWidth(280)
        fsync_row.addWidget(fsync_label)
        fsync_row.addStretch()

        self.fsync_check = QCheckBox()
        self.fsync_check.stateChanged.connect(self.save_settings)
        fsync_row.addWidget(self.fsync_check)
        settings_layout.addLayout(fsync_row)

        # NTSYNC
        ntsync_row = QHBoxLayout()
        ntsync_row.setSpacing(12)
        ntsync_label = QLabel("NTSYNC (новая синхронизация)")
        ntsync_label.setWordWrap(True)
        ntsync_label.setFixedWidth(280)
        ntsync_row.addWidget(ntsync_label)
        ntsync_row.addStretch()

        self.ntsync_check = QCheckBox()
        self.ntsync_check.stateChanged.connect(self.save_settings)
        ntsync_row.addWidget(self.ntsync_check)
        settings_layout.addLayout(ntsync_row)

        # DXVK
        dxvk_row = QHBoxLayout()
        dxvk_row.setSpacing(12)
        dxvk_label = QLabel("DXVK (DirectX → Vulkan)")
        dxvk_label.setWordWrap(True)
        dxvk_label.setFixedWidth(230)
        dxvk_row.addWidget(dxvk_label)
        dxvk_row.addStretch()

        self.dxvk_check = QCheckBox()
        self.dxvk_check.stateChanged.connect(self.save_settings)
        dxvk_row.addWidget(self.dxvk_check)
        settings_layout.addLayout(dxvk_row)

        # DXVK версия
        dxvk_version_layout = QHBoxLayout()
        dxvk_version_layout.setSpacing(12)
        dxvk_version_label = QLabel("Версия DXVK:")
        dxvk_version_label.setFixedWidth(100)
        dxvk_version_layout.addWidget(dxvk_version_label)

        self.dxvk_version_combo = QComboBox()
        self.dxvk_version_combo.addItems(["2.5.3 (стабильная)", "2.4.1", "2.3.1", "2.2.1"])
        self.dxvk_version_combo.setFixedWidth(150)
        self.dxvk_version_combo.currentIndexChanged.connect(self.save_settings)
        dxvk_version_layout.addWidget(self.dxvk_version_combo)
        dxvk_version_layout.addStretch()
        settings_layout.addLayout(dxvk_version_layout)

        # vkBasalt
        vkbasalt_row = QHBoxLayout()
        vkbasalt_row.setSpacing(12)
        vkbasalt_icon = QLabel("\uf1fc")
        vkbasalt_icon.setFont(IconFactory.get_font(14))
        vkbasalt_icon.setFixedWidth(24)
        vkbasalt_row.addWidget(vkbasalt_icon)

        vkbasalt_label = QLabel("vkBasalt (пост-обработка графики)")
        vkbasalt_label.setWordWrap(True)
        vkbasalt_row.addWidget(vkbasalt_label)
        vkbasalt_row.addStretch()

        self.vkbasalt_check = QCheckBox()
        self.vkbasalt_check.stateChanged.connect(self.save_settings)
        vkbasalt_row.addWidget(self.vkbasalt_check)
        settings_layout.addLayout(vkbasalt_row)

        # FSR
        fsr_row = QHBoxLayout()
        fsr_row.setSpacing(12)
        fsr_label = QLabel("FSR (FidelityFX Super Resolution)")
        fsr_label.setWordWrap(True)
        fsr_label.setFixedWidth(230)
        fsr_row.addWidget(fsr_label)
        fsr_row.addStretch()

        self.fsr_check = QCheckBox()
        self.fsr_check.stateChanged.connect(self.save_settings)
        fsr_row.addWidget(self.fsr_check)
        settings_layout.addLayout(fsr_row)

        # Уровень FSR
        fsr_level_layout = QHBoxLayout()
        fsr_level_layout.setSpacing(12)
        fsr_level_label = QLabel("Качество FSR:")
        fsr_level_label.setFixedWidth(100)
        fsr_level_layout.addWidget(fsr_level_label)

        self.fsr_level_combo = QComboBox()
        self.fsr_level_combo.addItems(["Ультра качество", "Качество", "Сбалансировано", "Производительность"])
        self.fsr_level_combo.setFixedWidth(150)
        self.fsr_level_combo.currentIndexChanged.connect(self.save_settings)
        fsr_level_layout.addWidget(self.fsr_level_combo)
        fsr_level_layout.addStretch()
        settings_layout.addLayout(fsr_level_layout)

        # NVIDIA DLSS
        dlss_row = QHBoxLayout()
        dlss_row.setSpacing(12)
        dlss_label = QLabel("NVIDIA DLSS (только для RTX карт)")
        dlss_label.setWordWrap(True)
        dlss_label.setFixedWidth(230)
        dlss_row.addWidget(dlss_label)
        dlss_row.addStretch()

        self.dlss_check = QCheckBox()
        self.dlss_check.stateChanged.connect(self.save_settings)
        dlss_row.addWidget(self.dlss_check)
        settings_layout.addLayout(dlss_row)

        right_layout.addWidget(settings_frame)

        # ========== СИСТЕМНЫЕ ДЕЙСТВИЯ ==========
        system_actions_frame = QFrame()
        system_actions_frame.setObjectName("system_actions_frame")
        system_actions_layout = QHBoxLayout(system_actions_frame)
        system_actions_layout.setContentsMargins(0, 12, 0, 0)
        system_actions_layout.setSpacing(18)

        # Открыть папку
        folder_action_layout = QHBoxLayout()
        folder_action_layout.setSpacing(8)
        self.folder_btn = QPushButton("\uf07b  Открыть папку")
        self.folder_btn.setObjectName("system_action_btn")
        self.folder_btn.setFont(IconFactory.get_font(11))
        self.folder_btn.setMinimumHeight(28)
        self.folder_btn.clicked.connect(self.open_game_folder)
        folder_action_layout.addWidget(self.folder_btn)
        system_actions_layout.addLayout(folder_action_layout)

        # Настройки Wine
        wine_action_layout = QHBoxLayout()
        wine_action_layout.setSpacing(8)
        self.wine_btn = QPushButton("\uf013  Настройки Wine")
        self.wine_btn.setObjectName("system_action_btn")
        self.wine_btn.setFont(IconFactory.get_font(11))
        self.wine_btn.setMinimumHeight(28)
        self.wine_btn.clicked.connect(self.open_wine_settings)
        wine_action_layout.addWidget(self.wine_btn)
        system_actions_layout.addLayout(wine_action_layout)

        # Версия Proton
        proton_action_layout = QHBoxLayout()
        proton_action_layout.setSpacing(8)
        self.proton_icon = QLabel("\uf726")
        self.proton_icon.setObjectName("system_action_icon")
        self.proton_icon.setFont(IconFactory.get_font(12))
        self.proton_icon.setFixedWidth(16)
        proton_action_layout.addWidget(self.proton_icon)
        self.proton_version_combo = QComboBox()
        self.proton_version_combo.setObjectName("proton_version_combo")
        self.proton_version_combo.setProperty("systemAction", True)
        self.proton_version_combo.setFixedWidth(220)
        self.proton_version_combo.setMinimumHeight(28)
        self.proton_version_combo.addItems(self.available_proton_versions)
        self.proton_version_combo.currentIndexChanged.connect(self.on_proton_version_changed)
        proton_action_layout.addWidget(self.proton_version_combo)
        system_actions_layout.addLayout(proton_action_layout)

        # Сброс настроек
        reset_action_layout = QHBoxLayout()
        reset_action_layout.setSpacing(8)
        self.reset_settings_btn = QPushButton("\uf2f1  Сбросить настройки")
        self.reset_settings_btn.setObjectName("system_action_btn")
        self.reset_settings_btn.setFont(IconFactory.get_font(11))
        self.reset_settings_btn.setMinimumHeight(28)
        self.reset_settings_btn.clicked.connect(self.reset_game_settings)
        reset_action_layout.addWidget(self.reset_settings_btn)
        system_actions_layout.addLayout(reset_action_layout)

        system_actions_layout.addStretch()
        right_layout.addWidget(system_actions_frame)

        # Кнопка "ИГРАТЬ"
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("play_btn")
        self.play_btn.setText("\uf04b  ИГРАТЬ")
        self.play_btn.setFont(IconFactory.get_font(16))
        self.play_btn.setMinimumHeight(60)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.clicked.connect(self.play_clicked.emit)
        right_layout.addWidget(self.play_btn)

        right_layout.addStretch()

        content_layout.addWidget(left_widget)
        content_layout.addWidget(right_widget, 1)

        scroll_area.setWidget(content_widget)
        self.main_layout.addWidget(scroll_area)

    def load_profiles(self):
        """Загрузка профилей для игры"""
        if not self.current_game_id:
            return

        self.profile_combo.clear()
        self.profile_combo.addItem("🚀 Быстрый запуск (настройки по умолчанию)", None)

        profiles = self.db.get_launch_profiles(self.current_game_id)
        for profile in profiles:
            name = profile['profile_name']
            if profile.get('is_default', 0) == 1:
                name = f"⚡ {name} (по умолчанию)"
            self.profile_combo.addItem(name, profile['id'])

    def on_profile_changed(self, index):
        """При выборе профиля загружаем его настройки"""
        if self._loading:
            return

        self.selected_profile_id = self.profile_combo.currentData()

        if self.selected_profile_id and self.current_game_id:
            profiles = self.db.get_launch_profiles(self.current_game_id)
            self.selected_profile = next(
                (p for p in profiles if p['id'] == self.selected_profile_id),
                None
            )

            if self.selected_profile:
                self._loading = True
                self._block_save = True
                try:
                    env = {}
                    if self.selected_profile.get('environment'):
                        try:
                            env = json.loads(self.selected_profile['environment'])
                        except:
                            pass

                    self.mangohud_check.setChecked(env.get('MANGOHUD') == '1')
                    self.gamemode_check.setChecked(env.get('GAMEMODERUN') == '1')
                    self.esync_check.setChecked(env.get('WINEESYNC') == '1')
                    self.fsync_check.setChecked(env.get('WINEFSYNC') == '1')
                    self.ntsync_check.setChecked(env.get('WINE_NTSYNC') == '1')
                    self.dxvk_check.setChecked(env.get('DXVK') == '1')
                    self.vkbasalt_check.setChecked(env.get('VKBASALT') == '1')
                    self.fsr_check.setChecked(env.get('WINE_FULLSCREEN_FSR') == '1')
                    self.dlss_check.setChecked(env.get('__GL_NV_DLSS') == '1')

                    dxvk_version = env.get('DXVK_VERSION', '2.5.3 (стабильная)')
                    idx = self.dxvk_version_combo.findText(dxvk_version)
                    if idx >= 0:
                        self.dxvk_version_combo.setCurrentIndex(idx)

                    fsr_level = env.get('WINE_FULLSCREEN_FSR_STRENGTH', 'Качество')
                    if fsr_level == '0.77':
                        fsr_level = 'Ультра качество'
                    elif fsr_level == '0.66':
                        fsr_level = 'Качество'
                    elif fsr_level == '0.58':
                        fsr_level = 'Сбалансировано'
                    elif fsr_level == '0.5':
                        fsr_level = 'Производительность'
                    idx = self.fsr_level_combo.findText(fsr_level)
                    if idx >= 0:
                        self.fsr_level_combo.setCurrentIndex(idx)

                    print(f"📋 Загружен профиль: {self.selected_profile['profile_name']}")
                finally:
                    self._block_save = False
                    self._loading = False
                if not self._loading and not self._block_save:
                    self.save_settings()
        else:
            self.selected_profile = None
            self.load_settings_from_db()

    def load_saved_settings(self):
        """Загрузка настроек по умолчанию"""
        self._loading = True
        self._block_save = True
        try:
            self.mangohud_check.setChecked(True)
            self.gamemode_check.setChecked(True)
            self.esync_check.setChecked(True)
            self.fsync_check.setChecked(True)
            self.ntsync_check.setChecked(False)
            self.dxvk_check.setChecked(True)
            self.vkbasalt_check.setChecked(False)
            self.fsr_check.setChecked(False)
            self.dlss_check.setChecked(False)
            self.proton_version_combo.setCurrentIndex(0)
            self.dxvk_version_combo.setCurrentIndex(0)
            self.fsr_level_combo.setCurrentIndex(1)
            self.selected_profile_id = None
            self.selected_profile = None
        finally:
            self._block_save = False
            self._loading = False

        self.save_settings()

    def reset_game_settings(self):
        """Сбросить сохранённые настройки игры в БД и обновить UI."""
        if not self.current_game_id:
            return

        with self.db.get_connection() as conn:
            conn.execute(
                "DELETE FROM game_settings WHERE game_id = ?",
                (self.current_game_id,),
            )

        self.selected_profile_id = None
        self.selected_profile = None
        self.load_settings_from_db()
        print(f"♻️ Настройки игры {self.current_game_id} сброшены")
        self._show_settings_status("Сброшено")

    def _show_settings_status(self, text: str):
        self.settings_status_timer.stop()
        if self.settings_status_animation:
            self.settings_status_animation.stop()
        self.settings_status_label.setText(text)
        self.settings_status_opacity.setOpacity(1.0)
        self.settings_status_timer.start(2000)

    def _fade_settings_status(self):
        self.settings_status_animation = QPropertyAnimation(self.settings_status_opacity, b"opacity", self)
        self.settings_status_animation.setDuration(320)
        self.settings_status_animation.setStartValue(1.0)
        self.settings_status_animation.setEndValue(0.0)
        self.settings_status_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.settings_status_animation.start()

    def set_available_proton_versions(self, versions):
        unique = []
        seen = set()
        for version in ["System Default", *versions]:
            if version and version not in seen:
                unique.append(version)
                seen.add(version)
        self.available_proton_versions = unique
        current = self.proton_version_combo.currentText() if hasattr(self, "proton_version_combo") else "System Default"
        if hasattr(self, "proton_version_combo"):
            self.proton_version_combo.blockSignals(True)
            self.proton_version_combo.clear()
            self.proton_version_combo.addItems(self.available_proton_versions)
            idx = self.proton_version_combo.findText(current)
            self.proton_version_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.proton_version_combo.blockSignals(False)

    def on_proton_version_changed(self):
        if self._loading or self._block_save:
            return
        self.save_settings()
        window = self.window()
        if window and hasattr(window, "show_notification"):
            window.show_notification("Proton", "Версия Proton обновлена", kind="info", duration_ms=1800)

    def open_profile_manager(self):
        """Открыть менеджер профилей"""
        if not self.current_game_id:
            return

        try:
            dialog = ProfileManagerDialog(
                game_id=self.current_game_id,
                game_title=self.title_label.text(),
                db=self.db,
                parent=self.window()
            )
            dialog.profile_changed.connect(self.load_profiles)
            dialog.exec()
        except ImportError:
            QMessageBox.warning(self, "Ошибка", "Модуль profile_manager не найден")

    def get_launch_env(self) -> dict:
        """Получить переменные окружения для запуска из БД"""
        env = {}

        if not self.current_game_id:
            return env

        settings = self.db.get_launch_settings(self.current_game_id)

        # MangoHud
        if settings.get('mangohud'):
            if SystemChecker.check_mangohud():
                SystemChecker.update_mangohud_config()
                SystemChecker.apply_mangohud_env(env, extended=True)
                print("✅ MangoHud активирован")
            else:
                print("⚠️ MangoHud не установлен")

        # Gamemode
        if settings.get('gamemode'):
            if SystemChecker.check_gamemode():
                env["GAMEMODERUN"] = "1"
                print("✅ Gamemode активирован")
            else:
                print("⚠️ Gamemode не установлен")

        # vkBasalt
        if settings.get('vkbasalt'):
            if SystemChecker.check_vkbasalt():
                SystemChecker.apply_vkbasalt_env(env)
                print("✅ vkBasalt активирован")
            else:
                print("⚠️ vkBasalt не установлен")

        if settings.get('esync'):
            env["WINEESYNC"] = "1"

        if settings.get('fsync'):
            env["WINEFSYNC"] = "1"

        if settings.get('ntsync') or settings.get('ntsunc'):
            env["WINE_NTSYNC"] = "1"

        if settings.get('dxvk'):
            env["DXVK"] = "1"
            dxvk_version = settings.get('dxvk_version', '2.5.3 (стабильная)').split()[0]
            env["DXVK_VERSION"] = dxvk_version
            print(f"✅ DXVK {dxvk_version} активирован")

        if settings.get('fsr'):
            env["WINE_FULLSCREEN_FSR"] = "1"
            fsr_level = settings.get('fsr_level', 'Качество')
            if fsr_level == "Ультра качество":
                env["WINE_FULLSCREEN_FSR_STRENGTH"] = "0.77"
            elif fsr_level == "Качество":
                env["WINE_FULLSCREEN_FSR_STRENGTH"] = "0.66"
            elif fsr_level == "Сбалансировано":
                env["WINE_FULLSCREEN_FSR_STRENGTH"] = "0.58"
            elif fsr_level == "Производительность":
                env["WINE_FULLSCREEN_FSR_STRENGTH"] = "0.5"
            print(f"✅ FSR активирован (уровень: {fsr_level})")

        if settings.get('dlss'):
            env["__GL_NV_DLSS"] = "1"
            print("✅ NVIDIA DLSS активирован")

        return env

    def get_selected_profile_id(self):
        """Получить ID выбранного профиля"""
        return self.selected_profile_id

    def set_game(self, game_id: int):
        """Установка данных игры для отображения"""
        self.current_game_id = game_id
        game = self.db.get_game(game_id)

        if not game:
            return

        title = game.get('name', 'Без названия')
        self.title_label.setText(title)

        playtime_seconds = game.get('playtime', 0)
        hours = playtime_seconds // 3600
        minutes = (playtime_seconds % 3600) // 60
        if hours > 0:
            self.playtime_label.setText(f"{hours} ч {minutes} мин")
        else:
            self.playtime_label.setText(f"{minutes} мин")

        launches = game.get('launch_count', 0)
        self.launches_label.setText(f"{launches} запусков")

        proton_version = game.get('proton_version')
        if proton_version:
            self.proton_label.setText(proton_version)
        else:
            self.proton_label.setText("По умолчанию")

        last_played = game.get('last_played', 0)
        if last_played > 0:
            date = datetime.fromtimestamp(last_played)
            self.last_played_label.setText(date.strftime("%d.%m.%Y %H:%M"))
        else:
            self.last_played_label.setText("Никогда")

        self.load_profiles()
        self.load_settings_from_db()

        cover_path = game.get('cover_path')
        if cover_path and Path(cover_path).exists():
            pixmap = QPixmap(cover_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.cover_label.width(),
                    self.cover_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.cover_label.setPixmap(scaled)
                self.create_blur_background(pixmap)
            else:
                self.set_default_cover()
        else:
            self.set_default_cover()

    def open_game_folder(self):
        """Открыть папку с игрой"""
        if not self.current_game_id:
            return

        game = self.db.get_game(self.current_game_id)
        if not game:
            return

        install_path = game.get('install_path', '')
        if install_path and Path(install_path).exists():
            subprocess.Popen(["xdg-open", install_path])
        else:
            QMessageBox.warning(self, "Ошибка", f"Папка не найдена:\n{install_path}")

    def open_wine_settings(self):
        """Открыть настройки Wine для префикса"""
        if not self.current_game_id:
            return

        game = self.db.get_game(self.current_game_id)
        if not game:
            return

        wine_prefix = game.get('wine_prefix')
        if not wine_prefix:
            wine_prefix = str(Path.home() / f"Games/prefix/{self.current_game_id}")

        if Path(wine_prefix).exists():
            env = os.environ.copy()
            env["WINEPREFIX"] = wine_prefix
            subprocess.Popen(["winecfg"], env=env)
        else:
            QMessageBox.warning(self, "Ошибка", f"Префикс Wine не найден:\n{wine_prefix}")

    def create_blur_background(self, pixmap: QPixmap):
        """Создание размытого фона из обложки"""
        if not pixmap or pixmap.isNull():
            return

        target_size = self.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            target_size = pixmap.size()

        blurred = pixmap.scaled(
            target_size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )

        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(30)

        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(blurred)
        item.setGraphicsEffect(blur_effect)
        scene.addItem(item)

        view = QGraphicsView(scene)
        view.setRenderHint(QPainter.SmoothPixmapTransform)
        view.resize(blurred.size())

        result = QPixmap(blurred.size())
        result.fill(Qt.transparent)
        painter = QPainter(result)
        view.render(painter)
        painter.end()

        self.blur_pixmap = result
        self.update()

    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)

        if self.current_game_id and self.cover_label.pixmap():
            game = self.db.get_game(self.current_game_id)
            if game:
                cover_path = game.get('cover_path')
                if cover_path and Path(cover_path).exists():
                    pixmap = QPixmap(cover_path)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(
                            self.cover_label.width(),
                            self.cover_label.height(),
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                        self.cover_label.setPixmap(scaled)

        if self.current_game_id:
            game = self.db.get_game(self.current_game_id)
            if game:
                cover_path = game.get('cover_path')
                if cover_path and Path(cover_path).exists():
                    pixmap = QPixmap(cover_path)
                    if not pixmap.isNull():
                        self.create_blur_background(pixmap)

    def set_default_cover(self):
        """Установка заглушки для обложки"""
        pixmap = QPixmap(300, 450)
        pixmap.fill(QColor(30, 30, 35))
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(100, 100, 110)))
        painter.setFont(QFont("Segoe UI Emoji", 64))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "🎮")
        painter.end()
        self.cover_label.setPixmap(pixmap)
        self.create_blur_background(pixmap)

    def paintEvent(self, event):
        """Отрисовка фона с размытием и слоем #0d1117"""
        if self.blur_pixmap:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.drawPixmap(0, 0, self.width(), self.height(), self.blur_pixmap)
            painter.fillRect(self.rect(), QBrush(QColor(13, 17, 23, 180)))

        super().paintEvent(event)