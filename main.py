import sys
import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QFileDialog, QDialog, QStackedWidget,
    QMessageBox, QSystemTrayIcon
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase

from theme import THEME
from game_database import GameDatabase
from game_grid_view import GameGridView
from game_details_page import GameDetailsPage
from add_game_dialog import AddGameDialog
from proton_manager import UMUManager, ProtonManagerPage, SystemChecker
from settings_page import SettingsPage
from download_progress import DownloadProgress
from system_tray import SystemTrayManager
from icon_factory import IconFactory
from notification import Notification


# ============================================================
# ЗАГРУЗКА ШРИФТОВ
# ============================================================

def load_application_fonts() -> bool:
    """Загрузка шрифтов Inter из папки assets/fonts/"""
    app_dir = Path(__file__).parent
    fonts_dir = app_dir / "assets" / "fonts"

    if not fonts_dir.exists():
        print(f"⚠️ Папка со шрифтами не найдена: {fonts_dir}")
        return False

    loaded_fonts = []

    regular_path = fonts_dir / "Inter-Regular.otf"
    if regular_path.exists():
        font_id = QFontDatabase.addApplicationFont(str(regular_path))
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            loaded_fonts.extend(families)
            print(f"✅ Загружен шрифт: Inter Regular")
        else:
            print(f"❌ Ошибка загрузки: {regular_path}")
    else:
        print(f"⚠️ Файл не найден: {regular_path}")

    bold_path = fonts_dir / "Inter-Bold.otf"
    if bold_path.exists():
        font_id = QFontDatabase.addApplicationFont(str(bold_path))
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            loaded_fonts.extend(families)
            print(f"✅ Загружен шрифт: Inter Bold")
        else:
            print(f"❌ Ошибка загрузки: {bold_path}")
    else:
        print(f"⚠️ Файл не найден: {bold_path}")

    return len(loaded_fonts) > 0


# ============================================================
# ГЛАВНОЕ ОКНО
# ============================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blitz Launcher")
        self.setMinimumSize(1000, 700)
        self.setStatusBar(None)
        
        app_dir = Path(__file__).parent
        db_path = app_dir / "library.db"
        self.db = GameDatabase(db_path)
        self.db.scan_proton_versions()
        
        central = QWidget()
        central.setObjectName("central_widget")
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Сначала создаем download_progress
        self.download_progress = DownloadProgress()
        
        self.stacked_widget = QStackedWidget()
        
        # Страницы
        self.all_games_page = GameGridView(self.db)
        self.all_games_page.game_launch_requested.connect(self.show_game_details)
        
        self.favorites_page = GameGridView(self.db)
        self.favorites_page.game_launch_requested.connect(self.show_game_details)
        
        self.recent_page = GameGridView(self.db)
        self.recent_page.game_launch_requested.connect(self.show_game_details)
        
        self.game_details_page = GameDetailsPage(self.db)
        self.game_details_page.set_available_proton_versions(self.scan_installed_proton_versions())
        self.game_details_page.back_clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.game_details_page.play_clicked.connect(self.launch_current_game)
        
        # Страница Proton Manager
        self.proton_page = ProtonManagerPage(self.download_progress, self)
        
        # Страница настроек
        self.settings_page = SettingsPage(self.db, self)
        self.settings_page.settings_changed.connect(self.apply_settings)
        
        self.stacked_widget.addWidget(self.all_games_page)      # index 0
        self.stacked_widget.addWidget(self.favorites_page)      # index 1
        self.stacked_widget.addWidget(self.recent_page)         # index 2
        self.stacked_widget.addWidget(self.game_details_page)   # index 3
        self.stacked_widget.addWidget(self.proton_page)         # index 4
        self.stacked_widget.addWidget(self.settings_page)       # index 5
        
        self.setup_sidebar(main_layout)
        main_layout.addWidget(self.stacked_widget)
        
        self.tray_manager = SystemTrayManager(self, self)
        
        self.select_sidebar_button(self.btn_library)
        self.current_details_game_id = None
        self.current_process = None
        self.current_history_id = None
        self.current_game_id = None
        self.session_start = None
        self.process_timer = None
        self.play_restore_timer = QTimer(self)
        self.play_restore_timer.setSingleShot(True)
        self.play_restore_timer.timeout.connect(self._set_play_in_game_state)
        self.play_spinner_timer = QTimer(self)
        self.play_spinner_timer.timeout.connect(self._update_play_spinner)
        self.play_spinner_frames = ["\uf110", "\uf021", "\uf2f1", "\uf01e"]
        self.play_spinner_index = 0
        self.is_play_loading = False
        self.launch_cancel_deadline_timer = QTimer(self)
        self.launch_cancel_deadline_timer.setSingleShot(True)
        self.launch_cancel_deadline_timer.timeout.connect(self._end_launch_cancel_window)
        self.pending_launch_timer = QTimer(self)
        self.pending_launch_timer.setSingleShot(True)
        self.pending_launch_timer.timeout.connect(self._run_pending_launch)
        self.launch_cancel_requested = False
        self.launch_cancel_window_active = False
        self.pending_launch_payload = None
        self.pending_launch_game_id = None
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()
    
    def load_fonts(self):
        app_dir = Path(__file__).parent
        fonts_dir = app_dir / "assets" / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)
        
        fa_font_path = fonts_dir / "fontawesome.otf"
        if fa_font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(fa_font_path))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                self.fa_font_family = families[0] if families else "Font Awesome 7 Free"
            else:
                self.fa_font_family = "Font Awesome 7 Free"
        else:
            print(f"⚠️ Шрифт Font Awesome не найден: {fa_font_path}")
            self.fa_font_family = "Font Awesome 7 Free"
        
        self.fa_font = QFont(self.fa_font_family)
        self.fa_font.setPixelSize(16)
        
        self.text_font = QFont("Inter", 13)
        self.text_font.setWeight(QFont.Weight.Medium)
        
        print(f"✅ Шрифты загружены: FA={self.fa_font_family}, Text=Inter")
    
    def create_sidebar_button(self, icon_code: str, text: str, icon_size: int = 18) -> QPushButton:
        button = QPushButton()
        button.setProperty("class", "sidebar-btn")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(button)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        icon_label = QLabel(icon_code)
        icon_label.setFont(self.fa_font)
        icon_label.setFixedWidth(icon_size + 4)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(icon_label)
        
        text_label = QLabel(text)
        text_label.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(text_label)
        
        layout.addStretch()
        
        return button
    
    def setup_sidebar(self, parent_layout):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        logo = QLabel("BLITZ LAUNCHER")
        logo.setObjectName("logo")
        sidebar_layout.addWidget(logo)
        
        self.load_fonts()
        
        self.add_btn = self.create_sidebar_button("\uf067", "Добавить игру")
        self.add_btn.setObjectName("add_btn")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.show_add_options_dialog)
        sidebar_layout.addWidget(self.add_btn)
        
        self.btn_library = self.create_sidebar_button("\uf015", "Библиотека")
        self.btn_library.clicked.connect(lambda: self.on_sidebar_clicked(self.btn_library, 0))
        sidebar_layout.addWidget(self.btn_library)
        
        self.btn_favorites = self.create_sidebar_button("\uf005", "Избранное")
        self.btn_favorites.clicked.connect(lambda: self.on_sidebar_clicked(self.btn_favorites, 1))
        sidebar_layout.addWidget(self.btn_favorites)
        
        self.btn_recent = self.create_sidebar_button("\uf017", "Недавние")
        self.btn_recent.clicked.connect(lambda: self.on_sidebar_clicked(self.btn_recent, 2))
        sidebar_layout.addWidget(self.btn_recent)
        
        self.btn_proton = self.create_sidebar_button("\uf5d2", "Proton")
        self.btn_proton.clicked.connect(lambda: self.on_sidebar_clicked(self.btn_proton, 4))
        sidebar_layout.addWidget(self.btn_proton)
        
        self.btn_settings = self.create_sidebar_button("\uf013", "Настройки")
        self.btn_settings.clicked.connect(lambda: self.on_sidebar_clicked(self.btn_settings, 5))
        sidebar_layout.addWidget(self.btn_settings)
        
        sidebar_layout.addStretch()
        
        # Добавляем существующий download_progress
        sidebar_layout.addWidget(self.download_progress)
        
        spacer = QWidget()
        spacer.setFixedHeight(8)
        sidebar_layout.addWidget(spacer)
        
        self.btn_exit = self.create_sidebar_button("\uf08b", "Выход")
        self.btn_exit.setObjectName("exit_btn")
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.clicked.connect(self.exit_app)
        sidebar_layout.addWidget(self.btn_exit)
        
        parent_layout.addWidget(sidebar)
    
    def select_sidebar_button(self, active_button):
        sidebar_buttons = [
            self.btn_library,
            self.btn_favorites,
            self.btn_recent,
            self.btn_proton,
            self.btn_settings
        ]

        for btn in sidebar_buttons:
            if btn is active_button:
                btn.setProperty("active", True)
            else:
                btn.setProperty("active", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def on_sidebar_clicked(self, button, index):
        self.select_sidebar_button(button)
        self.stacked_widget.setCurrentIndex(index)

        if index == 0:
            self.stacked_widget.widget(index).load_games()
        elif index == 1:
            self.stacked_widget.widget(index).load_favorites()
        elif index == 2:
            self.stacked_widget.widget(index).load_recent()

    def show_add_options_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить игру")
        dialog.setModal(True)
        dialog.setMinimumSize(460, 260)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        install_btn = QPushButton("\uf019  Установить новую игру")
        install_btn.setFont(IconFactory.get_font(12))
        install_btn.clicked.connect(lambda: (dialog.accept(), self.install_game()))
        layout.addWidget(install_btn)

        add_existing_btn = QPushButton("\uf07c  Добавить установленную игру")
        add_existing_btn.setFont(IconFactory.get_font(12))
        add_existing_btn.clicked.connect(lambda: (dialog.accept(), self.add_existing_game()))
        layout.addWidget(add_existing_btn)

        scan_btn = QPushButton("\uf002  Сканировать папку с играми")
        scan_btn.setFont(IconFactory.get_font(12))
        scan_btn.clicked.connect(lambda: (dialog.accept(), self.scan_folder()))
        layout.addWidget(scan_btn)

        cancel_btn = QPushButton("\uf00d  Отмена")
        cancel_btn.setFont(IconFactory.get_font(12))
        cancel_btn.clicked.connect(dialog.reject)
        layout.addWidget(cancel_btn)

        dialog.exec()

    def install_game(self):
        print("📥 Установка новой игры (функция будет реализована позже)")

    def add_existing_game(self):
        self.add_game_dialog()

    def scan_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сканирования")
        if folder:
            folder_path = Path(folder)
            exe_files = list(folder_path.rglob("*.exe"))

            if exe_files:
                added = 0
                for exe in exe_files:
                    existing = self.db.get_games(search_query=exe.stem)
                    if not existing:
                        self.db.add_game(
                            name=exe.stem,
                            install_path=str(exe.parent),
                            executable=exe.name,
                            store='local'
                        )
                        added += 1

                print(f"🔍 Сканирование завершено: найдено {len(exe_files)} файлов, добавлено {added} игр")
                self.all_games_page.refresh()
                self.favorites_page.refresh()
                self.recent_page.refresh()
            else:
                print("🔍 Сканирование завершено: исполняемых файлов не найдено")

    def add_game_dialog(self):
        dialog = AddGameDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_game_data()
            try:
                game_id = self.db.add_game(
                    name=data['title'],
                    install_path=str(Path(data['exe_path']).parent),
                    executable=Path(data['exe_path']).name,
                    cover_path=data.get('cover_path'),
                    proton_version=data.get('proton_version')
                )
                print(f"✅ Игра добавлена: {data['title']} (ID: {game_id})")
                self.all_games_page.refresh()
                self.favorites_page.refresh()
                self.recent_page.refresh()
                self.show_notification("Библиотека", f"Игра «{data['title']}» добавлена", kind="success")
            except Exception as e:
                print(f"❌ Ошибка добавления игры: {e}")
                self.show_notification("Ошибка", "Не удалось добавить игру", kind="error")

    def show_game_details(self, game_id: int, game_name: str):
        self.current_details_game_id = game_id
        self.game_details_page.set_game(game_id)
        self.stacked_widget.setCurrentIndex(3)

    def launch_current_game(self):
        if self.current_details_game_id:
            if hasattr(self, 'current_process') and self.current_process and self.current_process.poll() is None:
                reply = QMessageBox.question(
                    self,
                    "Игра уже запущена",
                    "Другая игра уже запущена. Запустить новую?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

            if self.is_play_loading:
                return

            game = self.db.get_game(self.current_details_game_id)
            if game:
                extra_env = self.game_details_page.get_launch_env()
                profile_id = self.game_details_page.get_selected_profile_id()
                self._start_play_loading()

                QTimer.singleShot(
                    0,
                    lambda gid=self.current_details_game_id,
                           gname=game.get('name', ''),
                           env=extra_env,
                           pid=profile_id: self._launch_game_async(gid, gname, env, pid)
                )

    def _launch_game_async(self, game_id: int, game_name: str, extra_env=None, profile_id=None):
        self.launch_cancel_requested = False
        self.launch_cancel_window_active = True
        self.pending_launch_game_id = game_id
        self.pending_launch_payload = (game_id, game_name, extra_env, profile_id)
        self.show_notification(
            "Запуск",
            f"Запуск {game_name}...",
            kind="info",
            icon_code="\uf144",
            duration_ms=3000,
            action_text="ОТМЕНИТЬ",
            action_callback=self.cancel_launch_request
        )
        self.pending_launch_timer.start(150)
        self.launch_cancel_deadline_timer.start(3000)

    def _run_pending_launch(self):
        if self.launch_cancel_requested or not self.pending_launch_payload:
            self._reset_play_button_state()
            return

        game_id, game_name, extra_env, profile_id = self.pending_launch_payload
        launched = self.launch_game(game_id, game_name, extra_env=extra_env, profile_id=profile_id)
        if launched:
            self.play_restore_timer.start(3000)
        else:
            self._reset_play_button_state()
        self.pending_launch_payload = None

    def cancel_launch_request(self):
        if not self.launch_cancel_window_active:
            return
        self.launch_cancel_requested = True

        if self.pending_launch_timer.isActive():
            self.pending_launch_timer.stop()
            self.pending_launch_payload = None

        if self.current_process and self.current_process.poll() is None:
            if self.pending_launch_game_id is None or self.current_game_id == self.pending_launch_game_id:
                self.current_process.terminate()

        self.show_notification("Отмена", "Запуск игры отменен", kind="warning", duration_ms=1600)
        self._reset_play_button_state()

    def _end_launch_cancel_window(self):
        self.launch_cancel_window_active = False
        self.launch_cancel_requested = False
        self.pending_launch_game_id = None

    def _start_play_loading(self):
        self.is_play_loading = True
        self.play_spinner_index = 0
        self._set_play_button_property("loading", True)
        self._set_play_button_property("in_game", False)
        self.game_details_page.play_btn.setEnabled(False)
        self._update_play_spinner()
        self.play_spinner_timer.start(150)

    def _update_play_spinner(self):
        if not self.is_play_loading:
            return
        frame = self.play_spinner_frames[self.play_spinner_index % len(self.play_spinner_frames)]
        self.play_spinner_index += 1
        self.game_details_page.play_btn.setText(f"{frame}  Запуск...")

    def _set_play_in_game_state(self):
        self.is_play_loading = False
        self.play_spinner_timer.stop()
        self._set_play_button_property("loading", False)
        self._set_play_button_property("in_game", True)
        self.game_details_page.play_btn.setText("\uf04b  В ИГРЕ")
        self.game_details_page.play_btn.setEnabled(True)

    def _reset_play_button_state(self):
        self.is_play_loading = False
        self.play_spinner_timer.stop()
        self.play_restore_timer.stop()
        self.pending_launch_timer.stop()
        self._set_play_button_property("loading", False)
        self._set_play_button_property("in_game", False)
        self.game_details_page.play_btn.setText("\uf04b  ИГРАТЬ")
        self.game_details_page.play_btn.setEnabled(True)

    def _set_play_button_property(self, name: str, value: bool):
        self.game_details_page.play_btn.setProperty(name, value)
        self.game_details_page.play_btn.style().unpolish(self.game_details_page.play_btn)
        self.game_details_page.play_btn.style().polish(self.game_details_page.play_btn)

    def launch_game(self, game_id: int, game_name: str, extra_env=None, profile_id=None):
        if self.launch_cancel_requested:
            return False
        game = self.db.get_game(game_id)
        if not game:
            QMessageBox.warning(self, "Ошибка", f"Игра не найдена: {game_name}")
            self.show_notification("Ошибка", f"Не удалось запустить {game_name}", kind="error", icon_code="\uf06a")
            return False

        install_path = game.get('install_path', '')
        executable = game.get('executable', '')
        proton_version = game.get('proton_version')
        exe_path = Path(install_path) / executable

        if not exe_path.exists():
            QMessageBox.warning(self, "Ошибка", f"Файл не найден:\n{exe_path}")
            self.show_notification("Ошибка", "Файл игры не найден", kind="error", icon_code="\uf06a")
            return False

        umu_manager = UMUManager()
        clean_version = GameDatabase.clean_proton_version(proton_version) if proton_version else None
        history_id = self.db.add_launch_record(game_id, profile_id=profile_id)
        launch_settings = self.db.get_launch_settings(game_id)
        selected_proton = launch_settings.get("proton_version", "System Default")
        if selected_proton and selected_proton != "System Default":
            clean_version = selected_proton
        env_from_db = self._build_env_from_launch_settings(launch_settings)
        env_from_db["UMU_PROTON_VERSION"] = selected_proton if selected_proton else "System Default"
        if extra_env:
            for key, value in extra_env.items():
                if key not in env_from_db or key.startswith("VKBASALT"):
                    env_from_db[key] = value

        if self.launch_cancel_requested:
            return False
        process = umu_manager.launch_with_options(
            exe_path=str(exe_path),
            game_id=game_id,
            game_title=game_name,
            proton_version=clean_version,
            parent=self,
            db=self.db,
            extra_env=env_from_db
        )

        if process:
            print(f"⚡ Запущена игра: {game_name}")
            self.current_process = process
            self.current_history_id = history_id
            self.current_game_id = game_id
            self.session_start = datetime.now()
            self.process_timer = QTimer()
            self.process_timer.timeout.connect(self.check_process)
            self.process_timer.start(1000)
            return True
        return False

    def _build_env_from_launch_settings(self, settings: dict) -> dict:
        """Преобразовать настройки игры из БД в переменные окружения запуска."""
        env = {}
        if settings.get('gamemode'):
            env["GAMEMODERUN"] = "1"
        if settings.get('esync') or settings.get('esunc'):
            env["WINEESYNC"] = "1"
        if settings.get('fsync') or settings.get('fsunc'):
            env["WINEFSYNC"] = "1"
        if settings.get('ntsync'):
            env["WINE_NTSYNC"] = "1"
        if settings.get('dxvk'):
            env["DXVK"] = "1"
            dxvk_version = settings.get('dxvk_version', '2.5.3 (стабильная)').split()[0]
            env["DXVK_VERSION"] = dxvk_version
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
        if settings.get('dlss'):
            env["__GL_NV_DLSS"] = "1"
        if settings.get('vkbasalt'):
            env["VKBASALT"] = "1"
        return env

    def scan_installed_proton_versions(self):
        """Сканировать стандартные папки Steam/compatibilitytools.d на Linux."""
        versions = []
        search_paths = [
            Path.home() / ".local/share/Steam/compatibilitytools.d",
            Path.home() / ".steam/root/compatibilitytools.d",
            Path.home() / ".steam/steam/compatibilitytools.d",
            Path.home() / ".local/share/Steam/steamapps/common",
            Path.home() / ".steam/root/steamapps/common",
        ]

        for base in search_paths:
            if not base.exists():
                continue
            try:
                for item in base.iterdir():
                    if not item.is_dir():
                        continue
                    name = item.name
                    lowered = name.lower()
                    if "proton" in lowered or "ge-" in lowered:
                        versions.append(name)
            except Exception:
                continue

        unique = []
        seen = set()
        for version in sorted(versions, key=lambda v: v.lower()):
            if version not in seen:
                unique.append(version)
                seen.add(version)
        return unique

    def check_process(self):
        if hasattr(self, 'current_process') and self.current_process and self.current_process.poll() is not None:
            if hasattr(self, 'process_timer') and self.process_timer:
                self.process_timer.stop()

            session_duration = int((datetime.now() - self.session_start).total_seconds()) if hasattr(self, 'session_start') and self.session_start else 0
            exit_code = self.current_process.returncode

            if hasattr(self, 'current_history_id') and self.current_history_id:
                self.db.update_game_session(self.current_history_id, session_duration, exit_code)

            if hasattr(self, 'current_game_id') and self.current_game_id:
                game = self.db.get_game(self.current_game_id)
                if game:
                    self.db.update_game(self.current_game_id, playtime=game.get('playtime', 0) + session_duration)

            print(f"✅ Игра завершена. Код: {exit_code}, Время: {session_duration} сек")
            self.current_process = None
            self.current_history_id = None
            self.current_game_id = None
            self.session_start = None
            self._reset_play_button_state()

    def open_proton_manager(self):
        """Открыть менеджер Proton"""
        self.stacked_widget.setCurrentIndex(4)
        self.select_sidebar_button(self.btn_proton)

    def open_settings(self):
        """Открыть страницу настроек"""
        self.stacked_widget.setCurrentIndex(5)
        self.select_sidebar_button(self.btn_settings)

    def apply_settings(self, settings: dict):
        """Применить настройки из SettingsPage"""
        print(f"✅ Применены настройки: {settings}")
        
        if 'card_size' in settings:
            card_size = settings['card_size']
            for page in [self.all_games_page, self.favorites_page, self.recent_page]:
                if hasattr(page, 'set_card_size'):
                    page.set_card_size(card_size)
        
        if 'columns' in settings:
            columns = settings['columns']
            for page in [self.all_games_page, self.favorites_page, self.recent_page]:
                if hasattr(page, 'set_columns'):
                    page.set_columns(columns)
        
        self.refresh_current_view()

    def refresh_current_view(self):
        """Обновить текущую страницу"""
        current_index = self.stacked_widget.currentIndex()
        current_page = self.stacked_widget.widget(current_index)
        
        if current_index == 0 and hasattr(current_page, 'load_games'):
            current_page.load_games()
        elif current_index == 1 and hasattr(current_page, 'load_favorites'):
            current_page.load_favorites()
        elif current_index == 2 and hasattr(current_page, 'load_recent'):
            current_page.load_recent()

    def exit_app(self):
        self.tray_manager.exit_app()

    def show_notification(
        self,
        title: str,
        message: str,
        kind: str = "info",
        duration_ms: int = 2600,
        icon_code: str = "",
        action_text: str = "",
        action_callback=None,
    ):
        notification = Notification(
            self,
            title=title,
            message=message,
            kind=kind,
            icon_code=icon_code,
            action_text=action_text,
            action_callback=action_callback,
        )
        notification.show_animated(duration_ms=duration_ms)


# ============================================================
# ЗАПУСК
# ============================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Blitz")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Blitz")

    app.setStyleSheet(THEME)

    if load_application_fonts():
        default_font = QFont("Inter", 10)
        app.setFont(default_font)
        print("✅ Inter установлен как шрифт по умолчанию")
    else:
        print("⚠️ Используется системный шрифт по умолчанию")

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("⚠️ Системный трей не поддерживается")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
