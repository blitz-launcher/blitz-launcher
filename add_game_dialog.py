import re
import sys
import hashlib
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QComboBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal


def get_app_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


def get_safe_filename(game_title: str) -> str:
    safe = re.sub(r'[^\w\-_\. ]', '_', game_title)
    safe = safe.replace(' ', '_')
    safe = re.sub(r'_+', '_', safe)
    safe = safe.strip('_')

    if len(safe) > 50:
        hash_suffix = hashlib.md5(game_title.encode()).hexdigest()[:8]
        safe = safe[:42] + '_' + hash_suffix

    return safe + '.jpg'


class CoverDownloadWorker(QThread):
    finished = Signal(bool, str)
    log = Signal(str)

    def __init__(self, game_title: str, covers_dir: Path):
        super().__init__()
        self.game_title = game_title
        self.covers_dir = covers_dir
        self._is_running = True

    def stop(self):
        self._is_running = False

    def _try_download_cover(self, url: str, cover_path: Path) -> bool:
        try:
            import urllib.request

            req_cover = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

            with urllib.request.urlopen(req_cover, timeout=15) as response:
                if not self._is_running:
                    return False

                if response.getcode() != 200:
                    return False

                content = response.read()

                if len(content) < 1000:
                    return False

                with open(cover_path, 'wb') as f:
                    f.write(content)

                return True

        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.log.emit(f"  URL не найден (404): {url}")
            else:
                self.log.emit(f"  HTTP ошибка {e.code}: {url}")
            return False
        except Exception as e:
            self.log.emit(f"  Ошибка скачивания: {str(e)}")
            return False

    def run(self):
        try:
            import urllib.request
            import urllib.error
            import json
            from urllib.parse import quote

            if not self._is_running:
                return

            self.log.emit(f"🔍 Поиск обложки для: {self.game_title}")

            encoded_title = quote(self.game_title, safe='')
            search_url = f"https://steamcommunity.com/actions/SearchApps/{encoded_title}"

            req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})

            with urllib.request.urlopen(req, timeout=10) as response:
                if not self._is_running:
                    return

                data = json.loads(response.read().decode())

                if data and len(data) > 0:
                    app_id = data[0]['appid']
                    self.log.emit(f"✅ Найден Steam ID: {app_id}")

                    cover_urls = [
                        f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/library_600x900_2x.jpg",
                        f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/library_600x900.jpg",
                        f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/library_300x450.jpg",
                        f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/portrait.jpg",
                        f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/capsule_616x353.jpg",
                        f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/header.jpg",
                    ]

                    self.covers_dir.mkdir(parents=True, exist_ok=True)
                    cover_path = self.covers_dir / get_safe_filename(self.game_title)

                    self.log.emit("📥 Поиск вертикальной обложки...")

                    for i, url in enumerate(cover_urls, 1):
                        if not self._is_running:
                            return

                        self.log.emit(f"  Попытка {i}/{len(cover_urls)}: {url.split('/')[-1]}")

                        if self._try_download_cover(url, cover_path):
                            self.log.emit(f"✅ Обложка успешно скачана!")
                            self.finished.emit(True, str(cover_path))
                            return

                    self.log.emit("❌ Не найдено подходящей вертикальной обложки")
                    self.finished.emit(False, "")

                else:
                    self.log.emit("❌ Игра не найдена на Steam")
                    self.finished.emit(False, "")

        except urllib.error.URLError as e:
            self.log.emit(f"🌐 Ошибка сети: {str(e)}")
            self.finished.emit(False, "")
        except json.JSONDecodeError as e:
            self.log.emit(f"📄 Ошибка парсинга JSON: {str(e)}")
            self.finished.emit(False, "")
        except Exception as e:
            self.log.emit(f"❌ Неизвестная ошибка: {str(e)}")
            self.finished.emit(False, "")


class AddGameDialog(QDialog):
    """Диалоговое окно для добавления новой игры"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить игру — Blitz")
        self.setFixedSize(500, 450)
        self.setModal(True)

        app_dir = get_app_dir()
        self.covers_dir = app_dir / "covers"
        self.covers_dir.mkdir(parents=True, exist_ok=True)

        self.download_worker = None
        self.pending_accept = False

        self.setup_ui()
        self.scan_proton_versions()

    def setup_ui(self):
        """Настройка интерфейса диалога"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # ========== НАЗВАНИЕ ИГРЫ ==========
        title_label = QLabel("Название игры")
        title_label.setStyleSheet("font-weight: bold; color: #c9d1d9;")
        main_layout.addWidget(title_label)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Введите название игры")
        self.title_edit.setMinimumHeight(32)
        self.title_edit.setStyleSheet("""
            QLineEdit {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                color: #c9d1d9;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
        """)
        main_layout.addWidget(self.title_edit)

        # ========== ОБЛОЖКА ==========
        cover_label = QLabel("Обложка (опционально)")
        cover_label.setStyleSheet("font-weight: bold; color: #c9d1d9; margin-top: 5px;")
        main_layout.addWidget(cover_label)

        cover_layout = QHBoxLayout()
        cover_layout.setSpacing(8)

        self.cover_path_edit = QLineEdit()
        self.cover_path_edit.setPlaceholderText("Путь к файлу обложки")
        self.cover_path_edit.setMinimumHeight(32)
        self.cover_path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                color: #c9d1d9;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
        """)
        cover_layout.addWidget(self.cover_path_edit)

        self.cover_browse_btn = QPushButton("Обзор")
        self.cover_browse_btn.setFixedWidth(70)
        self.cover_browse_btn.setMinimumHeight(32)
        self.cover_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                color: white;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        self.cover_browse_btn.clicked.connect(self.browse_cover)
        cover_layout.addWidget(self.cover_browse_btn)

        main_layout.addLayout(cover_layout)

        # ========== ИСПОЛНЯЕМЫЙ ФАЙЛ ==========
        exe_label = QLabel("Исполняемый файл (.exe)")
        exe_label.setStyleSheet("font-weight: bold; color: #c9d1d9; margin-top: 5px;")
        main_layout.addWidget(exe_label)

        exe_layout = QHBoxLayout()
        exe_layout.setSpacing(8)

        self.exe_path_edit = QLineEdit()
        self.exe_path_edit.setPlaceholderText("Путь к .exe файлу игры")
        self.exe_path_edit.setMinimumHeight(32)
        self.exe_path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                color: #c9d1d9;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
        """)
        exe_layout.addWidget(self.exe_path_edit)

        self.exe_browse_btn = QPushButton("Обзор")
        self.exe_browse_btn.setFixedWidth(70)
        self.exe_browse_btn.setMinimumHeight(32)
        self.exe_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                color: white;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        self.exe_browse_btn.clicked.connect(self.browse_exe)
        exe_layout.addWidget(self.exe_browse_btn)

        main_layout.addLayout(exe_layout)

        # ========== ВЕРСИЯ PROTON ==========
        proton_label = QLabel("Версия GE-Proton")
        proton_label.setStyleSheet("font-weight: bold; color: #c9d1d9; margin-top: 5px;")
        main_layout.addWidget(proton_label)

        self.proton_combo = QComboBox()
        self.proton_combo.setEditable(False)
        self.proton_combo.setMinimumHeight(32)
        self.proton_combo.setStyleSheet("""
            QComboBox {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                color: #c9d1d9;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #58a6ff;
            }
        """)
        main_layout.addWidget(self.proton_combo)

        # ========== КНОПКИ ==========
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setMinimumHeight(32)
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setStyleSheet("""
            QPushButton#cancel_btn {
                background-color: transparent;
                border: 1px solid #f85149;
                border-radius: 6px;
                padding: 6px 16px;
                color: #f85149;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton#cancel_btn:hover {
                background-color: rgba(248, 81, 73, 0.1);
            }
        """)
        self.cancel_btn.clicked.connect(self.on_cancel)
        button_layout.addWidget(self.cancel_btn)

        self.add_btn = QPushButton("Добавить")
        self.add_btn.setMinimumHeight(32)
        self.add_btn.setFixedWidth(100)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                color: white;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        self.add_btn.clicked.connect(self.on_add_clicked)
        button_layout.addWidget(self.add_btn)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.title_edit.setFocus()

        self.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
            }
        """)

    def on_cancel(self):
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.stop()
            self.download_worker.quit()
            self.download_worker.wait(1000)
        self.reject()

    def closeEvent(self, event):
        self.on_cancel()
        event.accept()

    def on_add_clicked(self):
        if not self.validate():
            return

        # Автоматически ищем обложку, если не выбрана ручная
        if not self.cover_path_edit.text().strip():
            if self.download_worker and self.download_worker.isRunning():
                QMessageBox.information(self, "Поиск", "Поиск обложки уже выполняется...")
                return
            self.pending_accept = True
            self.search_cover_auto()
            return

        self.accept()

    def scan_proton_versions(self):
        self.proton_combo.clear()
        self.proton_combo.addItem("GE-Proton (по умолчанию)")

        home = Path.home()
        search_paths = [
            home / ".local/share/Steam/compatibilitytools.d",
            home / ".steam/root/compatibilitytools.d",
            home / ".steam/steam/compatibilitytools.d",
        ]

        found_versions = []
        for search_path in search_paths:
            if search_path.exists():
                for item in search_path.iterdir():
                    if item.is_dir() and ("Proton" in item.name or "proton" in item.name):
                        proton_exec = item / "proton"
                        if proton_exec.exists() and proton_exec.is_file():
                            if item.name not in found_versions:
                                found_versions.append(item.name)

        found_versions.sort(reverse=True)
        for version in found_versions:
            if "GE-Proton" in version:
                self.proton_combo.addItem(f"⚡ {version}")
            else:
                self.proton_combo.addItem(f"📦 {version}")

        if not found_versions:
            self.proton_combo.addItem("⚠️ Proton не найден")
            self.proton_combo.setEnabled(False)
        else:
            self.proton_combo.setCurrentIndex(0)

    def browse_cover(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите обложку",
            str(Path.home()),
            "Изображения (*.png *.jpg *.jpeg *.bmp);;Все файлы (*)"
        )
        if file_path:
            self.cover_path_edit.setText(file_path)

    def browse_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите исполняемый файл игры",
            str(Path.home()),
            "Исполняемые файлы (*.exe);;Все файлы (*)"
        )
        if file_path:
            self.exe_path_edit.setText(file_path)
            if not self.title_edit.text().strip():
                suggested_title = Path(file_path).stem
                self.title_edit.setText(suggested_title)

    def search_cover_auto(self):
        game_title = self.title_edit.text().strip()
        if not game_title:
            self.pending_accept = False
            return

        self.download_worker = CoverDownloadWorker(game_title, self.covers_dir)
        self.download_worker.finished.connect(self.on_cover_downloaded)
        self.download_worker.start()

        self.add_btn.setEnabled(False)
        self.add_btn.setText("Поиск...")
        self.cancel_btn.setEnabled(False)

    def on_cover_downloaded(self, success: bool, cover_path: str):
        self.add_btn.setEnabled(True)
        self.add_btn.setText("Добавить")
        self.cancel_btn.setEnabled(True)

        if success and cover_path:
            self.cover_path_edit.setText(cover_path)

        if self.pending_accept and self.isVisible():
            self.pending_accept = False
            self.accept()

    def get_game_data(self) -> dict:
        proton_version = self.proton_combo.currentText()

        if proton_version.startswith("⚡ ") or proton_version.startswith("📦 "):
            proton_version = proton_version[2:]
        if proton_version.startswith("⚠️ "):
            proton_version = None
        if proton_version == "GE-Proton (по умолчанию)":
            proton_version = None

        return {
            'title': self.title_edit.text().strip(),
            'exe_path': self.exe_path_edit.text().strip(),
            'cover_path': self.cover_path_edit.text().strip() or None,
            'proton_version': proton_version
        }

    def validate(self) -> bool:
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название игры")
            self.title_edit.setFocus()
            return False

        if not self.exe_path_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Выберите исполняемый файл игры")
            self.exe_browse_btn.setFocus()
            return False

        exe_path = Path(self.exe_path_edit.text().strip())
        if not exe_path.exists():
            QMessageBox.warning(self, "Ошибка", "Указанный файл не существует")
            self.exe_browse_btn.setFocus()
            return False

        if exe_path.suffix.lower() != '.exe':
            QMessageBox.warning(self, "Ошибка", "Файл должен иметь расширение .exe")
            self.exe_browse_btn.setFocus()
            return False

        cover_path = self.cover_path_edit.text().strip()
        if cover_path:
            cover = Path(cover_path)
            if not cover.exists():
                QMessageBox.warning(self, "Ошибка", "Указанный файл обложки не существует")
                self.cover_browse_btn.setFocus()
                return False

        return True
