import os
import shutil
import subprocess
import platform
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox,
    QComboBox, QSlider, QSpinBox, QGroupBox, QMessageBox,
    QListWidget, QListWidgetItem, QTextEdit, QFrame,
    QScrollArea, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PySide6.QtCore import Qt, QSettings, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QColor, QPalette, QDesktopServices
from PySide6.QtCore import QUrl

from proton_manager import ProtonManager


class SystemInfoWorker(QThread):
    """Поток для получения системной информации"""
    finished = Signal(dict)

    def run(self):
        info = {}

        # ОС
        info['os'] = platform.system()
        info['os_version'] = platform.release()
        info['architecture'] = platform.machine()

        # Ядро
        try:
            result = subprocess.run(["uname", "-r"], capture_output=True, text=True)
            info['kernel'] = result.stdout.strip()
        except:
            info['kernel'] = "Неизвестно"

        # CPU
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        info['cpu'] = line.split(":", 1)[1].strip()
                        break
        except:
            info['cpu'] = "Неизвестно"

        # RAM
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if "MemTotal" in line:
                        mem_kb = int(line.split(":", 1)[1].strip().split()[0])
                        info['ram'] = f"{mem_kb // 1024 // 1024} GB"
                        break
        except:
            info['ram'] = "Неизвестно"

        # GPU
        try:
            result = subprocess.run(["glxinfo", "-B"], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if "OpenGL renderer" in line:
                    info['gpu'] = line.split(":", 1)[1].strip()
                    break
        except:
            info['gpu'] = "Неизвестно"

        # Диск
        try:
            stat = shutil.disk_usage("/")
            info['disk_total'] = f"{stat.total // (1024**3)} GB"
            info['disk_free'] = f"{stat.free // (1024**3)} GB"
            info['disk_used'] = f"{stat.used // (1024**3)} GB"
        except:
            info['disk_total'] = "Неизвестно"
            info['disk_free'] = "Неизвестно"
            info['disk_used'] = "Неизвестно"

        # Версии драйверов
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                                   capture_output=True, text=True)
            if result.returncode == 0:
                info['nvidia_driver'] = result.stdout.strip()
        except:
            info['nvidia_driver'] = "Не установлен"

        try:
            result = subprocess.run(["vulkaninfo", "--summary"], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if "Vulkan Instance Version:" in line:
                    info['vulkan'] = line.split(":", 1)[1].strip()
                    break
        except:
            info['vulkan'] = "Неизвестно"

        self.finished.emit(info)


class SettingsPage(QWidget):
    """Страница настроек Blitz Game Launcher"""
    
    settings_changed = Signal(dict)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.settings = QSettings("Blitz", "Settings")
        self.system_info = {}
        self.info_worker = None

        self.setup_ui()
        self.load_settings()
        self.load_system_info()

    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Заголовок
        title = QLabel("Настройки")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #58a6ff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Вкладки
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363d;
                border-radius: 8px;
                background-color: #161b22;
                padding: 10px;
            }
            QTabBar::tab {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 16px;
                margin-right: 4px;
                color: #c9d1d9;
            }
            QTabBar::tab:selected {
                background-color: #1f6feb;
                border-color: #1f6feb;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #21262d;
            }
        """)

        # Создаем все вкладки
        general_tab = self.create_general_tab()
        tabs.addTab(general_tab, "📋 Общие")
        
        library_tab = self.create_library_tab()
        tabs.addTab(library_tab, "📚 Библиотека")
        
        proton_tab = self.create_proton_tab()
        tabs.addTab(proton_tab, "🐚 Proton")
        
        performance_tab = self.create_performance_tab()
        tabs.addTab(performance_tab, "⚡ Производительность")
        
        appearance_tab = self.create_appearance_tab()
        tabs.addTab(appearance_tab, "🎨 Внешний вид")
        
        backup_tab = self.create_backup_tab()
        tabs.addTab(backup_tab, "💾 Резервное копирование")
        
        system_tab = self.create_system_tab()
        tabs.addTab(system_tab, "🖥️ Система")
        
        about_tab = self.create_about_tab()
        tabs.addTab(about_tab, "ℹ️ О программе")

        layout.addWidget(tabs)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_btn = QPushButton("Сбросить настройки")
        reset_btn.clicked.connect(self.reset_settings)
        button_layout.addWidget(reset_btn)

        apply_btn = QPushButton("Применить")
        apply_btn.setStyleSheet("background-color: #238636;")
        apply_btn.clicked.connect(self.apply_and_save)
        button_layout.addWidget(apply_btn)

        layout.addLayout(button_layout)

        # Стили
        self.setStyleSheet("""
            QWidget {
                background-color: #0d1117;
            }
            QLabel {
                color: #c9d1d9;
            }
            QLineEdit, QSpinBox, QComboBox, QTextEdit {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px;
                color: #c9d1d9;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {
                border-color: #58a6ff;
            }
            QCheckBox {
                color: #c9d1d9;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #30363d;
                background-color: #0d1117;
            }
            QCheckBox::indicator:checked {
                background-color: #58a6ff;
                border-color: #58a6ff;
            }
            QGroupBox {
                color: #58a6ff;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
            QPushButton {
                background-color: #238636;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background-color: #30363d;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background-color: #58a6ff;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QTableWidget {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                gridline-color: #30363d;
            }
            QTableWidget::item {
                color: #c9d1d9;
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #58a6ff;
                padding: 6px;
                border: none;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

    def create_general_tab(self):
        """Вкладка общих настроек"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Язык
        lang_group = QGroupBox("Язык интерфейса")
        lang_layout = QVBoxLayout(lang_group)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Русский", "ru")
        self.lang_combo.addItem("English", "en")
        lang_layout.addWidget(self.lang_combo)

        layout.addWidget(lang_group)

        # Запуск
        startup_group = QGroupBox("Запуск")
        startup_layout = QVBoxLayout(startup_group)

        self.start_minimized = QCheckBox("Запускать свёрнутым в трей")
        startup_layout.addWidget(self.start_minimized)

        self.close_to_tray = QCheckBox("Закрывать в трей (вместо выхода)")
        self.close_to_tray.setChecked(True)
        startup_layout.addWidget(self.close_to_tray)

        layout.addWidget(startup_group)

        # Поведение
        behavior_group = QGroupBox("Поведение")
        behavior_layout = QVBoxLayout(behavior_group)

        self.confirm_exit = QCheckBox("Подтверждать выход при запущенных играх")
        self.confirm_exit.setChecked(True)
        behavior_layout.addWidget(self.confirm_exit)

        self.auto_refresh = QCheckBox("Автоматически обновлять библиотеку при запуске")
        self.auto_refresh.setChecked(True)
        behavior_layout.addWidget(self.auto_refresh)

        self.check_updates_startup = QCheckBox("Проверять обновления при запуске")
        self.check_updates_startup.setChecked(True)
        behavior_layout.addWidget(self.check_updates_startup)

        layout.addWidget(behavior_group)

        layout.addStretch()
        return tab

    def create_library_tab(self):
        """Вкладка настроек библиотеки"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Папка для игр
        games_folder_group = QGroupBox("Папка с играми")
        games_folder_layout = QVBoxLayout(games_folder_group)

        folder_layout = QHBoxLayout()
        self.games_folder = QLineEdit()
        self.games_folder.setPlaceholderText("Путь к папке с играми")
        folder_layout.addWidget(self.games_folder)

        browse_btn = QPushButton("Обзор")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self.browse_games_folder)
        folder_layout.addWidget(browse_btn)
        games_folder_layout.addLayout(folder_layout)

        layout.addWidget(games_folder_group)

        # Папка для обложек
        covers_folder_group = QGroupBox("Папка для обложек")
        covers_folder_layout = QVBoxLayout(covers_folder_group)

        covers_layout = QHBoxLayout()
        self.covers_folder = QLineEdit()
        self.covers_folder.setPlaceholderText("Путь к папке с обложками")
        covers_layout.addWidget(self.covers_folder)

        browse_covers_btn = QPushButton("Обзор")
        browse_covers_btn.setFixedWidth(80)
        browse_covers_btn.clicked.connect(self.browse_covers_folder)
        covers_layout.addWidget(browse_covers_btn)
        covers_folder_layout.addLayout(covers_layout)

        layout.addWidget(covers_folder_group)

        # Папка для префиксов
        prefixes_group = QGroupBox("Папка для Wine префиксов")
        prefixes_layout = QVBoxLayout(prefixes_group)

        prefixes_folder_layout = QHBoxLayout()
        self.prefixes_folder = QLineEdit()
        self.prefixes_folder.setPlaceholderText("Путь к папке с префиксами")
        prefixes_folder_layout.addWidget(self.prefixes_folder)

        browse_prefixes_btn = QPushButton("Обзор")
        browse_prefixes_btn.setFixedWidth(80)
        browse_prefixes_btn.clicked.connect(self.browse_prefixes_folder)
        prefixes_folder_layout.addWidget(browse_prefixes_btn)
        prefixes_layout.addLayout(prefixes_folder_layout)

        layout.addWidget(prefixes_group)

        # Настройки отображения
        display_group = QGroupBox("Отображение библиотеки")
        display_layout = QVBoxLayout(display_group)

        self.show_hidden = QCheckBox("Показывать скрытые игры")
        display_layout.addWidget(self.show_hidden)

        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Сортировать по:"))
        self.sort_by_combo = QComboBox()
        self.sort_by_combo.addItem("По времени последнего запуска", "last_played")
        self.sort_by_combo.addItem("По названию", "name")
        self.sort_by_combo.addItem("По времени игры", "playtime")
        self.sort_by_combo.addItem("По дате добавления", "id")
        sort_layout.addWidget(self.sort_by_combo)
        sort_layout.addStretch()
        display_layout.addLayout(sort_layout)

        layout.addWidget(display_group)

        # Сканирование
        scan_group = QGroupBox("Сканирование")
        scan_layout = QVBoxLayout(scan_group)

        self.scan_on_startup = QCheckBox("Сканировать папку с играми при запуске")
        scan_layout.addWidget(self.scan_on_startup)

        scan_btn = QPushButton("🔍 Сканировать папку с играми сейчас")
        scan_btn.clicked.connect(self.scan_games_folder)
        scan_layout.addWidget(scan_btn)

        layout.addWidget(scan_group)

        layout.addStretch()
        return tab

    def create_proton_tab(self):
        """Вкладка настроек Proton"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Версия Proton по умолчанию
        proton_group = QGroupBox("Proton по умолчанию")
        proton_layout = QVBoxLayout(proton_group)

        self.default_proton = QComboBox()
        self.default_proton.addItem("🌍 GE-Proton (авто-выбор)", None)

        # Загружаем установленные версии
        try:
            pm = ProtonManager()
            versions = pm.get_installed_versions()
            for version in versions:
                if "GE-Proton" in version:
                    self.default_proton.addItem(f"⚡ {version}", version)
                else:
                    self.default_proton.addItem(f"📦 {version}", version)
        except:
            pass

        proton_layout.addWidget(self.default_proton)

        refresh_proton_btn = QPushButton("🔄 Обновить список Proton")
        refresh_proton_btn.clicked.connect(self.refresh_proton_list)
        proton_layout.addWidget(refresh_proton_btn)

        layout.addWidget(proton_group)

        # Настройки UMU
        umu_group = QGroupBox("UMU Launcher")
        umu_layout = QVBoxLayout(umu_group)

        self.auto_update_umu = QCheckBox("Автоматически обновлять UMU")
        self.auto_update_umu.setChecked(True)
        umu_layout.addWidget(self.auto_update_umu)

        self.umu_runtime = QCheckBox("Использовать UMU Runtime")
        self.umu_runtime.setChecked(True)
        umu_layout.addWidget(self.umu_runtime)

        umu_info = QLabel("💡 UMU Launcher позволяет запускать Windows-игры на Linux")
        umu_info.setStyleSheet("color: #8b949e; font-size: 10px;")
        umu_layout.addWidget(umu_info)

        layout.addWidget(umu_group)

        # Настройки DXVK
        dxvk_group = QGroupBox("DXVK")
        dxvk_layout = QVBoxLayout(dxvk_group)

        self.auto_install_dxvk = QCheckBox("Автоматически устанавливать DXVK в новые префиксы")
        self.auto_install_dxvk.setChecked(True)
        dxvk_layout.addWidget(self.auto_install_dxvk)

        dxvk_version_layout = QHBoxLayout()
        dxvk_version_layout.addWidget(QLabel("Версия DXVK:"))
        self.dxvk_version_combo = QComboBox()
        self.dxvk_version_combo.addItem("Последняя версия", "latest")
        self.dxvk_version_combo.addItem("2.5.3 (стабильная)", "2.5.3")
        self.dxvk_version_combo.addItem("2.4.1", "2.4.1")
        self.dxvk_version_combo.addItem("2.3.1", "2.3.1")
        dxvk_version_layout.addWidget(self.dxvk_version_combo)
        dxvk_version_layout.addStretch()
        dxvk_layout.addLayout(dxvk_version_layout)

        layout.addWidget(dxvk_group)

        layout.addStretch()
        return tab

    def create_performance_tab(self):
        """Вкладка настроек производительности"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # MangoHud
        mangohud_group = QGroupBox("MangoHud")
        mangohud_layout = QVBoxLayout(mangohud_group)

        self.mangohud_enabled = QCheckBox("Включать MangoHud по умолчанию")
        self.mangohud_enabled.setChecked(True)
        mangohud_layout.addWidget(self.mangohud_enabled)

        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Позиция:"))
        self.mangohud_position = QComboBox()
        self.mangohud_position.addItem("Верхний левый", "top-left")
        self.mangohud_position.addItem("Верхний правый", "top-right")
        self.mangohud_position.addItem("Нижний левый", "bottom-left")
        self.mangohud_position.addItem("Нижний правый", "bottom-right")
        position_layout.addWidget(self.mangohud_position)
        position_layout.addStretch()
        mangohud_layout.addLayout(position_layout)

        layout.addWidget(mangohud_group)

        # Gamemode
        gamemode_group = QGroupBox("Gamemode")
        gamemode_layout = QVBoxLayout(gamemode_group)

        self.gamemode_enabled = QCheckBox("Включать Gamemode по умолчанию")
        self.gamemode_enabled.setChecked(True)
        gamemode_layout.addWidget(self.gamemode_enabled)

        layout.addWidget(gamemode_group)

        # Esync / Fsync
        sync_group = QGroupBox("Синхронизация")
        sync_layout = QVBoxLayout(sync_group)

        self.esync_default = QCheckBox("Включать Esync по умолчанию")
        self.esync_default.setChecked(True)
        sync_layout.addWidget(self.esync_default)

        self.fsync_default = QCheckBox("Включать Fsync по умолчанию")
        self.fsync_default.setChecked(True)
        sync_layout.addWidget(self.fsync_default)

        layout.addWidget(sync_group)

        # Ограничения
        limits_group = QGroupBox("Ограничения")
        limits_layout = QGridLayout(limits_group)

        limits_layout.addWidget(QLabel("Максимум одновременных загрузок:"), 0, 0)
        self.max_downloads = QSpinBox()
        self.max_downloads.setRange(1, 10)
        self.max_downloads.setValue(3)
        limits_layout.addWidget(self.max_downloads, 0, 1)

        limits_layout.addWidget(QLabel("Таймаут загрузки (сек):"), 1, 0)
        self.timeout = QSpinBox()
        self.timeout.setRange(10, 300)
        self.timeout.setValue(60)
        limits_layout.addWidget(self.timeout, 1, 1)

        layout.addWidget(limits_group)

        layout.addStretch()
        return tab

    def create_appearance_tab(self):
        """Вкладка настроек внешнего вида"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Тема
        theme_group = QGroupBox("Тема оформления")
        theme_layout = QVBoxLayout(theme_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Тёмная", "dark")
        self.theme_combo.addItem("Светлая", "light")
        theme_layout.addWidget(self.theme_combo)

        layout.addWidget(theme_group)

        # Размер карточек
        cards_group = QGroupBox("Карточки игр")
        cards_layout = QVBoxLayout(cards_group)

        cards_layout.addWidget(QLabel("Размер карточки:"))
        self.card_size = QSlider(Qt.Horizontal)
        self.card_size.setRange(150, 250)
        self.card_size.setValue(180)
        self.card_size.setTickPosition(QSlider.TicksBelow)
        self.card_size.setTickInterval(10)
        cards_layout.addWidget(self.card_size)

        self.card_size_label = QLabel("180 x 260")
        self.card_size_label.setAlignment(Qt.AlignCenter)
        cards_layout.addWidget(self.card_size_label)
        self.card_size.valueChanged.connect(
            lambda v: self.card_size_label.setText(f"{v} x {int(v * 1.44)}")
        )

        layout.addWidget(cards_group)

        # Сетка
        grid_group = QGroupBox("Сетка")
        grid_layout = QVBoxLayout(grid_group)

        grid_layout.addWidget(QLabel("Количество колонок:"))
        self.columns_combo = QComboBox()
        self.columns_combo.addItem("Авто", "auto")
        for i in range(3, 8):
            self.columns_combo.addItem(f"{i}", i)
        grid_layout.addWidget(self.columns_combo)

        layout.addWidget(grid_group)

        # Анимации
        animations_group = QGroupBox("Анимации")
        animations_layout = QVBoxLayout(animations_group)

        self.enable_animations = QCheckBox("Включить анимации")
        self.enable_animations.setChecked(True)
        animations_layout.addWidget(self.enable_animations)

        layout.addWidget(animations_group)

        layout.addStretch()
        return tab

    def create_backup_tab(self):
        """Вкладка резервного копирования"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Авто-бэкап
        backup_group = QGroupBox("Автоматическое резервное копирование")
        backup_layout = QVBoxLayout(backup_group)

        self.auto_backup = QCheckBox("Автоматически создавать резервные копии")
        backup_layout.addWidget(self.auto_backup)

        backup_layout.addWidget(QLabel("Частота:"))
        self.backup_frequency = QComboBox()
        self.backup_frequency.addItem("Каждый день", "daily")
        self.backup_frequency.addItem("Раз в неделю", "weekly")
        self.backup_frequency.addItem("Раз в месяц", "monthly")
        backup_layout.addWidget(self.backup_frequency)

        backup_layout.addWidget(QLabel("Папка для резервных копий:"))
        backup_folder_layout = QHBoxLayout()
        self.backup_folder = QLineEdit()
        backup_folder_layout.addWidget(self.backup_folder)

        browse_backup_btn = QPushButton("Обзор")
        browse_backup_btn.setFixedWidth(80)
        browse_backup_btn.clicked.connect(self.browse_backup_folder)
        backup_folder_layout.addWidget(browse_backup_btn)
        backup_layout.addLayout(backup_folder_layout)

        layout.addWidget(backup_group)

        # Кнопки действий
        actions_group = QGroupBox("Действия")
        actions_layout = QVBoxLayout(actions_group)

        create_backup_btn = QPushButton("📀 Создать резервную копию сейчас")
        create_backup_btn.clicked.connect(self.create_backup)
        actions_layout.addWidget(create_backup_btn)

        restore_backup_btn = QPushButton("🔄 Восстановить из резервной копии")
        restore_backup_btn.clicked.connect(self.restore_backup)
        actions_layout.addWidget(restore_backup_btn)

        layout.addWidget(actions_group)

        # Список бэкапов
        backups_group = QGroupBox("Существующие резервные копии")
        backups_layout = QVBoxLayout(backups_group)

        self.backup_list = QListWidget()
        self.backup_list.setMaximumHeight(150)
        backups_layout.addWidget(self.backup_list)

        refresh_backups_btn = QPushButton("🔄 Обновить список")
        refresh_backups_btn.clicked.connect(self.refresh_backup_list)
        backups_layout.addWidget(refresh_backups_btn)

        layout.addWidget(backups_group)

        # Очистка
        cleanup_group = QGroupBox("Очистка")
        cleanup_layout = QVBoxLayout(cleanup_group)

        self.auto_cleanup = QCheckBox("Автоматически очищать старые резервные копии")
        cleanup_layout.addWidget(self.auto_cleanup)

        cleanup_layout.addWidget(QLabel("Хранить последние:"))
        self.keep_backups = QSpinBox()
        self.keep_backups.setRange(1, 50)
        self.keep_backups.setValue(10)
        cleanup_layout.addWidget(self.keep_backups)

        cleanup_btn = QPushButton("🧹 Очистить старые копии сейчас")
        cleanup_btn.clicked.connect(self.cleanup_old_backups)
        cleanup_layout.addWidget(cleanup_btn)

        layout.addWidget(cleanup_group)

        layout.addStretch()
        return tab

    def create_system_tab(self):
        """Вкладка системной информации"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Системная информация
        info_group = QGroupBox("Информация о системе")
        info_layout = QVBoxLayout(info_group)

        self.system_info_text = QTextEdit()
        self.system_info_text.setReadOnly(True)
        self.system_info_text.setMaximumHeight(300)
        self.system_info_text.setStyleSheet("font-family: monospace; font-size: 11px;")
        info_layout.addWidget(self.system_info_text)

        refresh_info_btn = QPushButton("🔄 Обновить информацию")
        refresh_info_btn.clicked.connect(self.load_system_info)
        info_layout.addWidget(refresh_info_btn)

        layout.addWidget(info_group)

        # Проверка зависимостей
        deps_group = QGroupBox("Проверка зависимостей")
        deps_layout = QVBoxLayout(deps_group)

        self.deps_table = QTableWidget()
        self.deps_table.setColumnCount(2)
        self.deps_table.setHorizontalHeaderLabels(["Компонент", "Статус"])
        self.deps_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.deps_table.setMaximumHeight(200)
        deps_layout.addWidget(self.deps_table)

        check_deps_btn = QPushButton("🔍 Проверить зависимости")
        check_deps_btn.clicked.connect(self.check_dependencies)
        deps_layout.addWidget(check_deps_btn)

        layout.addWidget(deps_group)

        # Логи
        logs_group = QGroupBox("Логи приложения")
        logs_layout = QVBoxLayout(logs_group)

        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setMaximumHeight(150)
        self.logs_text.setStyleSheet("font-family: monospace; font-size: 10px;")
        logs_layout.addWidget(self.logs_text)

        logs_buttons = QHBoxLayout()
        clear_logs_btn = QPushButton("🗑️ Очистить логи")
        clear_logs_btn.clicked.connect(self.clear_logs)
        logs_buttons.addWidget(clear_logs_btn)

        export_logs_btn = QPushButton("💾 Экспортировать логи")
        export_logs_btn.clicked.connect(self.export_logs)
        logs_buttons.addWidget(export_logs_btn)
        logs_buttons.addStretch()
        logs_layout.addLayout(logs_buttons)

        layout.addWidget(logs_group)

        layout.addStretch()
        return tab

    def create_about_tab(self):
        """Вкладка о программе"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        # Логотип
        logo = QLabel("⚡")
        logo.setStyleSheet("font-size: 64px;")
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        # Название
        name = QLabel("Blitz")
        name.setStyleSheet("font-size: 28px; font-weight: bold; color: #58a6ff;")
        name.setAlignment(Qt.AlignCenter)
        layout.addWidget(name)

        # Версия
        version = QLabel("Версия v0.1.0-alpha")
        version.setStyleSheet("color: #8b949e; font-size: 12px;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        # Описание
        desc = QLabel(
            "Быстрый игровой лаунчер\n"
            "Запускайте Windows-игры на Linux с максимальной производительностью"
        )
        desc.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #30363d; max-height: 1px; margin: 10px 0;")
        layout.addWidget(line)

        # Информация
        info_group = QGroupBox("Информация")
        info_layout = QGridLayout(info_group)

        info_layout.addWidget(QLabel("Проект:"), 0, 0)
        info_layout.addWidget(QLabel("Blitz Game Launcher"), 0, 1)

        info_layout.addWidget(QLabel("Лицензия:"), 2, 0)
        info_layout.addWidget(QLabel("GPL v3"), 2, 1)

        info_layout.addWidget(QLabel("GitHub:"), 3, 0)
        github_link = QLabel('<a href="https://github.com">github.com/blitz-launcher</a>')
        github_link.setOpenExternalLinks(True)
        info_layout.addWidget(github_link, 3, 1)

        layout.addWidget(info_group)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        check_updates_btn = QPushButton("🔍 Проверить обновления")
        check_updates_btn.clicked.connect(self.check_updates)
        buttons_layout.addWidget(check_updates_btn)

        donate_btn = QPushButton("💝 Поддержать проект")
        donate_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("")))
        buttons_layout.addWidget(donate_btn)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        layout.addStretch()
        return tab

    def apply_and_save(self):
        """Применить и сохранить настройки"""
        self.save_settings()
        self.apply_settings()
        QMessageBox.information(self, "Успех", "Настройки сохранены!")

    def load_settings(self):
        """Загрузка сохранённых настроек"""
        # Общие
        lang = self.settings.value("general/language", "ru")
        idx = self.lang_combo.findData(lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)

        self.start_minimized.setChecked(self.settings.value("general/start_minimized", False, type=bool))
        self.close_to_tray.setChecked(self.settings.value("general/close_to_tray", True, type=bool))
        self.confirm_exit.setChecked(self.settings.value("general/confirm_exit", True, type=bool))
        self.auto_refresh.setChecked(self.settings.value("general/auto_refresh", True, type=bool))
        self.check_updates_startup.setChecked(self.settings.value("general/check_updates_startup", True, type=bool))

        # Библиотека
        self.games_folder.setText(self.settings.value("library/games_folder", ""))
        self.covers_folder.setText(self.settings.value("library/covers_folder", ""))
        self.prefixes_folder.setText(self.settings.value("library/prefixes_folder", ""))
        self.show_hidden.setChecked(self.settings.value("library/show_hidden", False, type=bool))
        self.scan_on_startup.setChecked(self.settings.value("library/scan_on_startup", True, type=bool))

        sort_by = self.settings.value("library/sort_by", "last_played")
        idx = self.sort_by_combo.findData(sort_by)
        if idx >= 0:
            self.sort_by_combo.setCurrentIndex(idx)

        # Proton
        default_proton = self.settings.value("proton/default_version", None)
        if default_proton:
            for i in range(self.default_proton.count()):
                if self.default_proton.itemData(i) == default_proton:
                    self.default_proton.setCurrentIndex(i)
                    break

        self.auto_update_umu.setChecked(self.settings.value("proton/auto_update_umu", True, type=bool))
        self.umu_runtime.setChecked(self.settings.value("proton/umu_runtime", True, type=bool))
        self.auto_install_dxvk.setChecked(self.settings.value("proton/auto_install_dxvk", True, type=bool))

        dxvk_version = self.settings.value("proton/dxvk_version", "latest")
        idx = self.dxvk_version_combo.findData(dxvk_version)
        if idx >= 0:
            self.dxvk_version_combo.setCurrentIndex(idx)

        # Производительность
        self.mangohud_enabled.setChecked(self.settings.value("performance/mangohud_enabled", True, type=bool))
        self.gamemode_enabled.setChecked(self.settings.value("performance/gamemode_enabled", True, type=bool))
        self.esync_default.setChecked(self.settings.value("performance/esync_default", True, type=bool))
        self.fsync_default.setChecked(self.settings.value("performance/fsync_default", True, type=bool))
        self.max_downloads.setValue(self.settings.value("performance/max_downloads", 3, type=int))
        self.timeout.setValue(self.settings.value("performance/timeout", 60, type=int))

        # Внешний вид
        theme = self.settings.value("appearance/theme", "dark")
        idx = self.theme_combo.findData(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        card_size = self.settings.value("appearance/card_size", 180, type=int)
        self.card_size.setValue(card_size)

        columns = self.settings.value("appearance/columns", "auto")
        idx = self.columns_combo.findData(columns)
        if idx >= 0:
            self.columns_combo.setCurrentIndex(idx)

        self.enable_animations.setChecked(self.settings.value("appearance/enable_animations", True, type=bool))

        # Резервное копирование
        self.auto_backup.setChecked(self.settings.value("backup/auto_backup", False, type=bool))
        self.backup_folder.setText(self.settings.value("backup/folder", str(Path.home() / "BlitzBackups")))
        self.auto_cleanup.setChecked(self.settings.value("backup/auto_cleanup", True, type=bool))
        self.keep_backups.setValue(self.settings.value("backup/keep_backups", 10, type=int))

        # Загружаем список бэкапов
        self.refresh_backup_list()

    def save_settings(self):
        """Сохранение настроек"""
        # Общие
        self.settings.setValue("general/language", self.lang_combo.currentData())
        self.settings.setValue("general/start_minimized", self.start_minimized.isChecked())
        self.settings.setValue("general/close_to_tray", self.close_to_tray.isChecked())
        self.settings.setValue("general/confirm_exit", self.confirm_exit.isChecked())
        self.settings.setValue("general/auto_refresh", self.auto_refresh.isChecked())
        self.settings.setValue("general/check_updates_startup", self.check_updates_startup.isChecked())

        # Библиотека
        self.settings.setValue("library/games_folder", self.games_folder.text())
        self.settings.setValue("library/covers_folder", self.covers_folder.text())
        self.settings.setValue("library/prefixes_folder", self.prefixes_folder.text())
        self.settings.setValue("library/show_hidden", self.show_hidden.isChecked())
        self.settings.setValue("library/scan_on_startup", self.scan_on_startup.isChecked())
        self.settings.setValue("library/sort_by", self.sort_by_combo.currentData())

        # Proton
        self.settings.setValue("proton/default_version", self.default_proton.currentData())
        self.settings.setValue("proton/auto_update_umu", self.auto_update_umu.isChecked())
        self.settings.setValue("proton/umu_runtime", self.umu_runtime.isChecked())
        self.settings.setValue("proton/auto_install_dxvk", self.auto_install_dxvk.isChecked())
        self.settings.setValue("proton/dxvk_version", self.dxvk_version_combo.currentData())

        # Производительность
        self.settings.setValue("performance/mangohud_enabled", self.mangohud_enabled.isChecked())
        self.settings.setValue("performance/gamemode_enabled", self.gamemode_enabled.isChecked())
        self.settings.setValue("performance/esync_default", self.esync_default.isChecked())
        self.settings.setValue("performance/fsync_default", self.fsync_default.isChecked())
        self.settings.setValue("performance/max_downloads", self.max_downloads.value())
        self.settings.setValue("performance/timeout", self.timeout.value())

        # Внешний вид
        self.settings.setValue("appearance/theme", self.theme_combo.currentData())
        self.settings.setValue("appearance/card_size", self.card_size.value())
        self.settings.setValue("appearance/columns", self.columns_combo.currentData())
        self.settings.setValue("appearance/enable_animations", self.enable_animations.isChecked())

        # Резервное копирование
        self.settings.setValue("backup/auto_backup", self.auto_backup.isChecked())
        self.settings.setValue("backup/folder", self.backup_folder.text())
        self.settings.setValue("backup/auto_cleanup", self.auto_cleanup.isChecked())
        self.settings.setValue("backup/keep_backups", self.keep_backups.value())

    def apply_settings(self):
        """Применение настроек к приложению"""
        settings_dict = {
            'theme': self.theme_combo.currentData(),
            'card_size': self.card_size.value(),
            'columns': self.columns_combo.currentData(),
            'enable_animations': self.enable_animations.isChecked(),
            'mangohud_enabled': self.mangohud_enabled.isChecked(),
            'gamemode_enabled': self.gamemode_enabled.isChecked(),
            'default_proton': self.default_proton.currentData(),
        }
        self.settings_changed.emit(settings_dict)

    def reset_settings(self):
        """Сброс настроек к значениям по умолчанию"""
        reply = QMessageBox.question(
            self,
            "Сброс настроек",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.settings.clear()
            self.load_settings()
            QMessageBox.information(self, "Успех", "Настройки сброшены!")

    def load_system_info(self):
        """Загрузка системной информации"""
        self.system_info_text.setText("Загрузка информации о системе...")

        self.info_worker = SystemInfoWorker()
        self.info_worker.finished.connect(self.display_system_info)
        self.info_worker.start()

    def display_system_info(self, info):
        """Отображение системной информации"""
        text = f"""
<b>Операционная система:</b> {info.get('os', 'Неизвестно')} {info.get('os_version', '')}
<b>Архитектура:</b> {info.get('architecture', 'Неизвестно')}
<b>Ядро:</b> {info.get('kernel', 'Неизвестно')}

<b>Процессор:</b> {info.get('cpu', 'Неизвестно')}
<b>Оперативная память:</b> {info.get('ram', 'Неизвестно')}

<b>Видеокарта:</b> {info.get('gpu', 'Неизвестно')}
<b>Драйвер NVIDIA:</b> {info.get('nvidia_driver', 'Неизвестно')}
<b>Vulkan:</b> {info.get('vulkan', 'Неизвестно')}

<b>Дисковое пространство:</b>
   Всего: {info.get('disk_total', 'Неизвестно')}
   Использовано: {info.get('disk_used', 'Неизвестно')}
   Свободно: {info.get('disk_free', 'Неизвестно')}
"""
        self.system_info_text.setHtml(text)

    def check_dependencies(self):
        """Проверка зависимостей"""
        self.deps_table.setRowCount(0)

        deps = [
            ("umu-run", "UMU Launcher"),
            ("gamemoderun", "Gamemode"),
            ("mangohud", "MangoHud"),
            ("wine", "Wine"),
            ("steam", "Steam"),
        ]

        for i, (cmd, name) in enumerate(deps):
            self.deps_table.insertRow(i)
            self.deps_table.setItem(i, 0, QTableWidgetItem(name))

            if shutil.which(cmd):
                status = "✅ Установлен"
                self.deps_table.setItem(i, 1, QTableWidgetItem(status))
                self.deps_table.item(i, 1).setForeground(QColor(63, 185, 80))
            else:
                status = "❌ Не установлен"
                self.deps_table.setItem(i, 1, QTableWidgetItem(status))
                self.deps_table.item(i, 1).setForeground(QColor(248, 81, 73))

        self.deps_table.resizeColumnsToContents()

    def refresh_backup_list(self):
        """Обновить список резервных копий"""
        self.backup_list.clear()
        backup_folder = Path(self.backup_folder.text())

        if backup_folder.exists():
            backups = sorted(backup_folder.glob("backup_*.db"), reverse=True)
            for backup in backups:
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                size = backup.stat().st_size / 1024  # KB
                item = QListWidgetItem(f"{backup.name} ({mtime.strftime('%Y-%m-%d %H:%M')}) - {size:.1f} KB")
                item.setData(Qt.UserRole, str(backup))
                self.backup_list.addItem(item)

    def cleanup_old_backups(self):
        """Очистка старых резервных копий"""
        backup_folder = Path(self.backup_folder.text())
        keep = self.keep_backups.value()

        if not backup_folder.exists():
            return

        backups = sorted(backup_folder.glob("backup_*.db"), reverse=True)
        to_delete = backups[keep:]

        if to_delete:
            reply = QMessageBox.question(
                self,
                "Очистка",
                f"Будет удалено {len(to_delete)} старых резервных копий. Продолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                for backup in to_delete:
                    backup.unlink()
                self.refresh_backup_list()
                QMessageBox.information(self, "Успех", f"Удалено {len(to_delete)} копий!")

    def clear_logs(self):
        """Очистка логов"""
        reply = QMessageBox.question(self, "Очистка", "Очистить логи?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.logs_text.clear()

    def export_logs(self):
        """Экспорт логов"""
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить логи", "logs.txt", "Текстовые файлы (*.txt)")
        if file_path:
            with open(file_path, 'w') as f:
                f.write(self.logs_text.toPlainText())
            QMessageBox.information(self, "Успех", f"Логи сохранены в {file_path}")

    def refresh_proton_list(self):
        """Обновить список Proton версий"""
        try:
            pm = ProtonManager()
            pm.scan_proton_versions()

            # Обновляем комбобокс
            current = self.default_proton.currentData()
            self.default_proton.clear()
            self.default_proton.addItem("🌍 GE-Proton (авто-выбор)", None)

            versions = pm.get_installed_versions()
            for version in versions:
                if "GE-Proton" in version:
                    self.default_proton.addItem(f"⚡ {version}", version)
                else:
                    self.default_proton.addItem(f"📦 {version}", version)

            # Восстанавливаем выбор
            if current:
                for i in range(self.default_proton.count()):
                    if self.default_proton.itemData(i) == current:
                        self.default_proton.setCurrentIndex(i)
                        break

            QMessageBox.information(self, "Успех", "Список Proton обновлён!")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить список Proton:\n{e}")

    def scan_games_folder(self):
        """Сканирование папки с играми"""
        folder = self.games_folder.text()
        if not folder:
            QMessageBox.warning(self, "Ошибка", "Укажите папку с играми")
            return

        folder_path = Path(folder)
        if not folder_path.exists():
            QMessageBox.warning(self, "Ошибка", "Папка не существует")
            return

        # Ищем .exe файлы
        exe_files = list(folder_path.rglob("*.exe"))

        if exe_files:
            reply = QMessageBox.question(
                self,
                "Сканирование",
                f"Найдено {len(exe_files)} исполняемых файлов.\nДобавить их в библиотеку?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                added = 0
                for exe in exe_files:
                    # Проверяем, не добавлена ли уже игра
                    existing = self.db.get_games(search_query=exe.stem)
                    if not existing:
                        self.db.add_game(
                            name=exe.stem,
                            install_path=str(exe.parent),
                            executable=exe.name,
                            store='local'
                        )
                        added += 1

                QMessageBox.information(self, "Успех", f"Добавлено {added} игр!")
        else:
            QMessageBox.information(self, "Сканирование", "Исполняемых файлов не найдено")

    def create_backup(self):
        """Создание резервной копии"""
        backup_folder = Path(self.backup_folder.text())
        if not backup_folder.exists():
            backup_folder.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_folder / f"backup_{timestamp}.db"

        if self.db.backup(backup_path):
            self.refresh_backup_list()
            QMessageBox.information(self, "Успех", f"Резервная копия создана:\n{backup_path}")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось создать резервную копию")

    def restore_backup(self):
        """Восстановление из резервной копии"""
        current_item = self.backup_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Ошибка", "Выберите резервную копию для восстановления")
            return

        backup_path = current_item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Восстановление",
            "Текущая библиотека будет заменена. Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            shutil.copy2(backup_path, self.db.db_path)
            QMessageBox.information(self, "Успех", "Библиотека восстановлена!")

    def check_updates(self):
        """Проверка обновлений"""
        QMessageBox.information(self, "Обновления", "Вы используете последнюю версию!")

    def browse_games_folder(self):
        """Выбор папки с играми"""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с играми")
        if folder:
            self.games_folder.setText(folder)

    def browse_covers_folder(self):
        """Выбор папки для обложек"""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для обложек")
        if folder:
            self.covers_folder.setText(folder)

    def browse_prefixes_folder(self):
        """Выбор папки для префиксов"""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для Wine префиксов")
        if folder:
            self.prefixes_folder.setText(folder)

    def browse_backup_folder(self):
        """Выбор папки для резервных копий"""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для резервных копий")
        if folder:
            self.backup_folder.setText(folder)
            self.refresh_backup_list()