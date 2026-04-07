import os
import sys
import platform
import subprocess
import tarfile
import shutil
import tempfile
import json
import urllib.request
import urllib.error
import re
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar, QMessageBox,
    QDialog, QTextEdit, QFrame, QCheckBox, QGroupBox, QLineEdit,
    QComboBox, QScrollArea, QApplication
)
from PySide6.QtGui import QFont


# Глобальная переменная для хранения пути к папке приложения
_APP_DIR = None


def set_app_dir(path: Path):
    global _APP_DIR
    _APP_DIR = path


def get_app_dir() -> Path:
    global _APP_DIR
    if _APP_DIR is None:
        return Path(__file__).parent
    return _APP_DIR


# ============================================================
# КЛАСС ДЛЯ ПОЛУЧЕНИЯ ПОСЛЕДНЕЙ ВЕРСИИ DXVK
# ============================================================

class DXVKVersionFetcher:
    @staticmethod
    def get_latest_version() -> Optional[str]:
        try:
            url = "https://api.github.com/repos/doitsujin/dxvk/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                version = data.get('tag_name', '').replace('v', '')
                return version
        except Exception as e:
            print(f"⚠️ Не удалось получить последнюю версию DXVK: {e}")
            return "2.5.3"

    @staticmethod
    def get_download_url(version: str) -> str:
        return f"https://github.com/doitsujin/dxvk/releases/download/v{version}/dxvk-{version}.tar.gz"

# ============================================================
# SYSTEM CHECKER
# ============================================================

class SystemChecker:
    _BLITZ_MANGOHUD_MARKER = "# Blitz MangoHud config"
    
    @staticmethod
    def check_mangohud() -> bool:
        """Проверка наличия MangoHud в системе"""
        return shutil.which("mangohud") is not None

    @staticmethod
    def get_mangohud_version() -> Optional[str]:
        """Получить версию MangoHud"""
        try:
            result = subprocess.run(["mangohud", "--version"], capture_output=True, text=True, timeout=5)
            output = result.stdout + result.stderr
            match = re.search(r'(\d+\.\d+\.\d+)', output)
            return match.group(1) if match else None
        except:
            return None

    @staticmethod
    def check_gamemode() -> bool:
        """Проверка наличия Gamemode"""
        return shutil.which("gamemoderun") is not None

    @staticmethod
    def check_vulkan() -> bool:
        """Проверка поддержки Vulkan"""
        try:
            result = subprocess.run(["vulkaninfo", "--summary"],
                                   capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False

    @staticmethod
    def check_wine() -> bool:
        """Проверка наличия Wine"""
        return shutil.which("wine") is not None

    @staticmethod
    def check_vkbasalt() -> bool:
        """Проверка наличия vkBasalt в системе"""
        return shutil.which("vkbasalt") is not None

    @staticmethod
    def get_vkbasalt_version() -> Optional[str]:
        """Получить версию vkBasalt"""
        try:
            result = subprocess.run(["vkbasalt", "--version"], capture_output=True, text=True, timeout=5)
            output = result.stdout + result.stderr
            match = re.search(r'(\d+\.\d+\.\d+)', output)
            return match.group(1) if match else None
        except:
            return None

    @staticmethod
    def get_vkbasalt_config_path() -> Path:
        """Получить путь к конфигурационному файлу vkBasalt"""
        config_dir = Path.home() / ".config/vkbasalt"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "vkBasalt.conf"

    @staticmethod
    def create_vkbasalt_config():
        """Создать конфигурацию vkBasalt"""
        config_path = SystemChecker.get_vkbasalt_config_path()
        
        config_content = """# vkBasalt конфигурация для Blitz Game Launcher
# Эффекты пост-обработки

# ========== ЭФФЕКТЫ ==========
# Доступные эффекты: cas, contrast_adaptivesharpening, smaa, deband, lut
effects = cas,contrast_adaptivesharpening,smaa,deband

# ========== CAS (Contrast Adaptive Sharpening) ==========
# Резкость изображения (0.0 - 1.0)
casSharpness = 0.5

# ========== SMAA (Enhanced Subpixel Morphological Antialiasing) ==========
# Качество сглаживания: low, medium, high, ultra
smaaQuality = high

# ========== DEBAND (убирает полосы на градиентах) ==========
debandIterations = 1
debandThreshold = 0.01
debandRange = 16

# ========== CONTRAST ADAPTIVE SHARPENING ==========
# Альтернативное резкое увеличение резкости
sharpeningStrength = 0.65

# ========== LUT (Color Lookup Table) ==========
# Файл цветокоррекции
lutFile = /usr/share/vkbasalt/LUT.png

# ========== ОБЩИЕ НАСТРОЙКИ ==========
# Клавиша для включения/выключения эффектов
toggleKey = Home

# Клавиша для переключения эффектов
cycleEffects = End

# Клавиша для перезагрузки конфига
reloadConfig = Insert

# Отображение FPS (если нужно)
# showFps = True

# Отображение статистики
# showStats = True
"""
        config_path.write_text(config_content)
        print(f"✅ Создан конфиг vkBasalt: {config_path}")
        return config_path

    @staticmethod
    def update_vkbasalt_config():
        """Обновить или создать конфигурацию vkBasalt"""
        config_path = SystemChecker.get_vkbasalt_config_path()
        
        if not config_path.exists():
            return SystemChecker.create_vkbasalt_config()
        
        return config_path

    @staticmethod
    def apply_vkbasalt_env(env: dict):
        """Применить переменные окружения для vkBasalt"""
        if not SystemChecker.check_vkbasalt():
            print("⚠️ vkBasalt не установлен в системе")
            return env
        
        # Обновляем конфиг
        SystemChecker.update_vkbasalt_config()
        
        # Устанавливаем переменные окружения
        env["ENABLE_VKBASALT"] = "1"
        env["VKBASALT_ENABLE"] = "1"
        env["LD_PRELOAD"] = "libvkbasalt.so"
        
        print("✅ vkBasalt активирован")
        print("   - Нажмите Home для включения/выключения эффектов")
        print("   - Нажмите End для переключения эффектов")
        return env

    @staticmethod
    def get_mangohud_config_path() -> Path:
        """Получить путь к конфигурационному файлу MangoHud"""
        config_dir = Path.home() / ".config/MangoHud"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "MangoHud.conf"

    @staticmethod
    def create_mangohud_config():
        """Создать полную конфигурацию MangoHud"""
        config_path = SystemChecker.get_mangohud_config_path()
        
        config_content = f"""# {SystemChecker._BLITZ_MANGOHUD_MARKER}
# MangoHud конфигурация для Blitz Game Launcher
# Полный набор метрик

# ========== ОСНОВНЫЕ ПОКАЗАТЕЛИ ==========
fps                         # FPS
frametime                   # Время кадра в мс
frametime_ms                # Тоже самое
frame_timing                # Тайминг кадров
frame_count                 # Счетчик кадров

# ========== ЗАГРУЗКА ==========
cpu_stats                   # Статистика CPU (загрузка по ядрам)
cpu_load                    # Общая загрузка CPU
core_load                   # Загрузка каждого ядра
gpu_stats                   # Статистика GPU
gpu_load                    # Загрузка GPU
gpu_core_clock              # Частота ядра GPU
gpu_mem_clock               # Частота памяти GPU
gpu_mem_temp                # Температура памяти GPU

# ========== ТЕМПЕРАТУРА ==========
cpu_temp                    # Температура CPU
gpu_temp                    # Температура GPU

# ========== ПАМЯТЬ ==========
ram                         # Использование RAM
ram_total                   # Всего RAM
vram                        # Использование VRAM
vram_total                  # Всего VRAM

# ========== ЧАСТОТЫ ==========
cpu_mhz                     # Частота CPU
gpu_core_clock              # Частота ядра GPU
gpu_mem_clock               # Частота памяти GPU

# ========== СТАТУСЫ ==========
gamemode                    # Статус Gamemode (активен/неактивен)
vsync                       # Статус VSync (включен/выключен)
wine                        # Версия Wine
vulkan_driver               # Драйвер Vulkan
engine_version              # Версия движка
resolution                  # Разрешение экрана
fps_color_change            # Изменение цвета FPS
throttling_status           # Статус троттлинга
fan_speed                   # Скорость вентилятора GPU
pci_bus_usage               # Использование PCI шины
pcie_speed                  # Скорость PCIe

# ========== ЭНЕРГОПОТРЕБЛЕНИЕ ==========
power                       # Энергопотребление GPU
power_cpu                   # Энергопотребление CPU

# ========== ВНЕШНИЙ ВИД ==========
position=top-right          # Позиция: top-left, top-right, bottom-left, bottom-right
background_alpha=0.6        # Прозрачность фона (0-1)
background_color=000000     # Цвет фона (HEX)
text_color=FFFFFF           # Цвет текста (HEX)
font_size=20                # Размер шрифта
text_outline                # Обводка текста
font_scale=1.0              # Масштаб шрифта
table                       # Табличный формат вывода

# ========== КЛАВИШИ ==========
toggle_hud=F12              # Клавиша для показа/скрытия HUD
toggle_logging=F11          # Клавиша для логирования
toggle_position=Shift+F11   # Клавиша для смены позиции
toggle_hud_position=Ctrl+F11 # Альтернативная смена позиции
reload_cfg=Shift+F12        # Перезагрузка конфига

# ========== ЛОГИРОВАНИЕ ==========
log_duration=30             # Длительность логирования в секундах
output_folder=/tmp/mangohud # Папка для логов

# ========== ПРОЧЕЕ ==========
permit_upload               # Разрешить загрузку (для отладки)
round_fps                   # Округлять FPS
benchmark_percentiles=99,95,90,50,25,5,1  # Перцентили для бенчмарка
"""
        
        config_path.write_text(config_content)
        print(f"✅ Создан полный конфиг MangoHud: {config_path}")
        print(f"   - Включено отображение: Gamemode, VSync, и все метрики")
        return config_path

    @staticmethod
    def update_mangohud_config():
        """Обновить или создать конфигурацию MangoHud"""
        config_path = SystemChecker.get_mangohud_config_path()
        
        if not config_path.exists():
            return SystemChecker.create_mangohud_config()
        
        try:
            content = config_path.read_text(encoding="utf-8", errors="replace")
            
            # Проверяем наличие маркера Blitz
            if SystemChecker._BLITZ_MANGOHUD_MARKER not in content:
                print("⚠️ Конфиг MangoHud не от Blitz, пересоздаем...")
                return SystemChecker.create_mangohud_config()
            
            # Проверяем наличие нужных параметров
            required_params = ["fps", "cpu_stats", "gpu_stats", "gamemode", "vsync"]
            missing_params = [p for p in required_params if p not in content]
            
            if missing_params:
                print(f"⚠️ В конфиге MangoHud отсутствуют параметры: {missing_params}")
                print("🔄 Пересоздаем полную конфигурацию...")
                return SystemChecker.create_mangohud_config()
        except Exception as e:
            print(f"⚠️ Ошибка чтения конфига MangoHud: {e}")
            return SystemChecker.create_mangohud_config()
        
        return config_path

    @staticmethod
    def apply_mangohud_env(env: dict, extended: bool = True):
        """
        Применить переменные окружения для MangoHud
        extended: расширенный режим (все метрики)
        """
        # Основная переменная
        env["MANGOHUD"] = "1"
        
        # Полная конфигурация со всеми метриками, включая gamemode и vsync
        if extended:
            env["MANGOHUD_CONFIG"] = (
                # Основные
                "fps,frametime,"
                # Загрузка
                "cpu_stats,gpu_stats,"
                # Температура
                "cpu_temp,gpu_temp,"
                # Память
                "ram,vram,"
                # Частоты
                "cpu_mhz,gpu_core_clock,gpu_mem_clock,"
                # Статусы
                "gamemode,vsync,"
                # Драйверы
                "wine,vulkan_driver,"
                # Другое
                "resolution,frame_timing,power"
            )
        else:
            # Базовая конфигурация
            env["MANGOHUD_CONFIG"] = "fps,frametime,cpu_stats,gpu_stats,cpu_temp,gpu_temp,ram,vram,gamemode,vsync"
        
        # Позиция оверлея
        env["MANGOHUD_POSITION"] = "top-right"
        
        # Размер шрифта
        env["MANGOHUD_FONT_SIZE"] = "20"
        
        # Включаем обводку текста
        env["MANGOHUD_CONFIG"] += ",text_outline"
        
        # Включаем табличный формат
        env["MANGOHUD_CONFIG"] += ",table"
        
        # Принудительно включаем отображение Gamemode
        env["MANGOHUD_GAMEMODE"] = "1"
        
        # Включаем отображение VSync
        env["MANGOHUD_VSYNC"] = "1"
        
        print(f"✅ MangoHud включен (расширенный режим: {extended})")
        print(f"📊 Отображаемые метрики: FPS, Frametime, CPU/GPU, RAM/VRAM, Gamemode, VSync")
        return env

    @staticmethod
    def apply_mangohud_runtime_env(env: dict):
        """Старый метод для совместимости - используем расширенный режим"""
        return SystemChecker.apply_mangohud_env(env, extended=True)

    @staticmethod
    def check_umu_installed() -> bool:
        """Проверка наличия UMU Launcher"""
        return shutil.which("umu-run") is not None

    @staticmethod
    def get_umu_version() -> Optional[str]:
        """Получить версию UMU Launcher"""
        try:
            result = subprocess.run(["umu-run", "--version"], capture_output=True, text=True, timeout=5)
            output = result.stdout + result.stderr
            match = re.search(r'(\d+\.\d+\.\d+)', output)
            return match.group(1) if match else None
        except:
            return None

    @staticmethod
    def get_system_info() -> dict:
        """Получить полную информацию о системе"""
        info = {
            'mangohud': SystemChecker.check_mangohud(),
            'mangohud_version': SystemChecker.get_mangohud_version(),
            'gamemode': SystemChecker.check_gamemode(),
            'vkbasalt': SystemChecker.check_vkbasalt(),
            'vkbasalt_version': SystemChecker.get_vkbasalt_version(),
            'vulkan': SystemChecker.check_vulkan(),
            'wine': SystemChecker.check_wine(),
            'umu': SystemChecker.check_umu_installed(),
            'umu_version': SystemChecker.get_umu_version(),
        }
        return info

    @staticmethod
    def print_system_info():
        """Вывести информацию о системе в консоль"""
        info = SystemChecker.get_system_info()
        print("\n" + "="*50)
        print("🔍 ИНФОРМАЦИЯ О СИСТЕМЕ")
        print("="*50)
        print(f"🐧 MangoHud:     {'✅ ' + info['mangohud_version'] if info['mangohud'] else '❌ не установлен'}")
        print(f"🎮 Gamemode:     {'✅ установлен' if info['gamemode'] else '❌ не установлен'}")
        print(f"🎨 vkBasalt:     {'✅ ' + info['vkbasalt_version'] if info['vkbasalt'] else '❌ не установлен'}")
        print(f"🔮 Vulkan:       {'✅ доступен' if info['vulkan'] else '❌ не доступен'}")
        print(f"🍷 Wine:         {'✅ установлен' if info['wine'] else '❌ не установлен'}")
        print(f"📦 UMU:          {'✅ ' + info['umu_version'] if info['umu'] else '❌ не установлен'}")
        print("="*50 + "\n")


# ============================================================
# ДИАЛОГ ПРОГРЕССА УСТАНОВКИ
# ============================================================

class InstallProgressDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(500, 450)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        self.icon_label = QLabel("⚡")
        self.icon_label.setStyleSheet("font-size: 48px;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        self.title_label = QLabel("Установка...")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #58a6ff;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #21262d;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #58a6ff;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(250)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #c9d1d9;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.log_text)

        self.setStyleSheet("QDialog { background-color: #0d1117; }")

    def set_title(self, text: str):
        self.title_label.setText(text)

    def set_icon(self, icon: str):
        self.icon_label.setText(icon)

    def set_progress(self, value: int):
        self.progress_bar.setValue(value)

    def set_progress_range(self, min_val: int, max_val: int):
        self.progress_bar.setRange(min_val, max_val)

    def add_log(self, text: str):
        self.log_text.append(text)
        self.log_text.ensureCursorVisible()


# ============================================================
# ПОТОК ДЛЯ ЗАГРУЗКИ СПИСКА ВЕРСИЙ PROTON
# ============================================================

class ProtonVersionsLoader(QThread):
    finished = Signal(list)

    def run(self):
        try:
            url = "https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                versions = []
                for release in data:
                    if "GE-Proton" in release['tag_name']:
                        for asset in release['assets']:
                            if asset['name'].endswith('.tar.gz'):
                                versions.append({
                                    'name': release['tag_name'],
                                    'url': asset['browser_download_url'],
                                    'published': release['published_at']
                                })
                                break
                self.finished.emit(versions[:30])
        except Exception as e:
            print(f"❌ Ошибка загрузки списка версий: {e}")
            self.finished.emit([])


# ============================================================
# ПОТОК ДЛЯ УСТАНОВКИ PROTON
# ============================================================

class ProtonInstallWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, version_name: str, download_url: str, install_dir: Path, cache_dir: Path):
        super().__init__()
        self.version_name = version_name
        self.download_url = download_url
        self.install_dir = install_dir
        self.cache_dir = cache_dir
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def _is_valid_tar_gz(self, file_path: Path) -> bool:
        try:
            if not file_path.exists():
                return False
            with tarfile.open(file_path, 'r:gz') as tar:
                members = tar.getmembers()
                return len(members) > 0
        except (tarfile.TarError, EOFError, OSError):
            return False

    def _download_file(self, url: str, dest_path: Path) -> bool:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

            with urllib.request.urlopen(req, timeout=60) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192

                with open(dest_path, 'wb') as f:
                    while True:
                        if self._is_cancelled:
                            return False

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = int(downloaded * 100 / total_size)
                            self.progress.emit(percent)

                if total_size > 0 and downloaded < total_size:
                    return False
                return True
        except Exception as e:
            self.log.emit(f"❌ Ошибка скачивания: {str(e)}")
            return False

    def run(self):
        try:
            self.log.emit(f"📥 Загрузка {self.version_name}...")

            cached_file = self.cache_dir / f"{self.version_name}.tar.gz"

            if cached_file.exists() and self._is_valid_tar_gz(cached_file):
                self.log.emit("📁 Найдено в кэше")
            else:
                if cached_file.exists():
                    self.log.emit("⚠️ Кэш поврежден, скачиваем заново")
                    cached_file.unlink()

                success = self._download_file(self.download_url, cached_file)
                if not success:
                    self.finished.emit(False, "Ошибка загрузки файла")
                    return

                if not self._is_valid_tar_gz(cached_file):
                    self.log.emit("❌ Скачанный файл поврежден")
                    cached_file.unlink()
                    self.finished.emit(False, "Файл поврежден, попробуйте снова")
                    return

            self.log.emit(f"📦 Распаковка {self.version_name}...")

            self.install_dir.mkdir(parents=True, exist_ok=True)

            try:
                with tarfile.open(cached_file, 'r:gz') as tar:
                    tar.extractall(self.install_dir)

                self.log.emit(f"✅ {self.version_name} успешно установлен!")
                self.cleanup_cache()
                self.finished.emit(True, self.version_name)

            except (tarfile.TarError, EOFError) as e:
                self.log.emit(f"❌ Ошибка распаковки: {e}")
                cached_file.unlink()
                self.finished.emit(False, "Архив поврежден")

        except Exception as e:
            self.log.emit(f"❌ Ошибка: {str(e)}")
            self.finished.emit(False, str(e))

    def cleanup_cache(self, keep_last: int = 5):
        try:
            files = sorted(self.cache_dir.glob("*.tar.gz"), key=lambda x: x.stat().st_mtime, reverse=True)
            for file in files[keep_last:]:
                file.unlink()
        except Exception:
            pass


# ============================================================
# МЕНЕДЖЕР PROTON
# ============================================================

class ProtonManager:
    def __init__(self):
        self.proton_dir = Path.home() / ".local/share/Steam/compatibilitytools.d"
        self.proton_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_valid_proton_path(path: Path) -> bool:
        proton_exec = path / "proton"
        if not proton_exec.exists():
            proton_exec = path / "proton" / "proton"
        return proton_exec.exists() and proton_exec.is_file()

    def get_installed_versions(self) -> List[str]:
        versions = []
        if self.proton_dir.exists():
            for item in self.proton_dir.iterdir():
                if item.is_dir() and ("Proton" in item.name or "GE-Proton" in item.name):
                    if self.is_valid_proton_path(item):
                        versions.append(item.name)
        versions.sort(reverse=True)
        return versions

    def is_version_installed(self, version: str) -> bool:
        installed = self.get_installed_versions()
        return version in installed


# ============================================================
# ДИАЛОГ МЕНЕДЖЕРА PROTON
# ============================================================

class ProtonManagerPage(QWidget):
    def __init__(self, download_progress_widget=None, parent=None):
        super().__init__(parent)
        
        self.download_progress = download_progress_widget
        self.cache_dir = Path.home() / ".cache/blitz-launcher/proton"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.proton_dir = Path.home() / ".local/share/Steam/compatibilitytools.d"
        self.proton_dir.mkdir(parents=True, exist_ok=True)
        
        self._is_alive = True
        self.load_thread = None
        self.install_thread = None
        
        self.setup_ui()
        self.load_versions()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel("Управление версиями GE-Proton")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #58a6ff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Поиск
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск версий Proton...")
        self.search_input.setMinimumHeight(36)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #c9d1d9;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
        """)
        self.search_input.textChanged.connect(self.filter_versions)
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_frame)
        
        # Кнопка обновления
        refresh_btn = QPushButton("🔄 Обновить список")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        refresh_btn.clicked.connect(self.load_versions)
        layout.addWidget(refresh_btn)
        
        # Список версий
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.versions_widget = QWidget()
        self.versions_layout = QVBoxLayout(self.versions_widget)
        self.versions_layout.setContentsMargins(0, 0, 0, 0)
        self.versions_layout.setSpacing(8)
        self.versions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll_area.setWidget(self.versions_widget)
        layout.addWidget(scroll_area, 1)
    
    def get_installed_versions(self) -> set:
        installed = set()
        if self.proton_dir.exists():
            for item in self.proton_dir.iterdir():
                if item.is_dir() and ("Proton" in item.name or "GE-Proton" in item.name):
                    installed.add(item.name)
        return installed
    
    def load_versions(self):
        if not self._is_alive:
            return
        
        self.clear_versions()
        installed_versions = self.get_installed_versions()
        
        loading_label = QLabel("🔄 Загрузка списка версий...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet("color: #8b949e; padding: 20px;")
        self.versions_layout.addWidget(loading_label)
        QApplication.processEvents()
        
        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.quit()
        
        self.load_thread = ProtonVersionsLoader()
        self.load_thread.finished.connect(lambda versions: self.populate_versions(versions, installed_versions))
        self.load_thread.start()
    
    def clear_versions(self):
        try:
            while self.versions_layout.count():
                item = self.versions_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
        except (RuntimeError, AttributeError):
            pass
    
    def populate_versions(self, versions: List[Dict], installed_versions: set):
        if not self._is_alive:
            return
        
        self.clear_versions()
        
        if not versions:
            error_label = QLabel("❌ Не удалось загрузить список версий")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("color: #f85149; padding: 20px;")
            self.versions_layout.addWidget(error_label)
            return
        
        for version_info in versions:
            version_name = version_info['name']
            is_installed = version_name in installed_versions
            self.add_version_item(version_name, version_info['url'], is_installed)
    
    def add_version_item(self, version_name: str, download_url: str, is_installed: bool):
        if not self._is_alive:
            return
        
        item_widget = QFrame()
        item_widget.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-radius: 8px;
                padding: 8px;
            }
            QFrame:hover { background-color: #21262d; }
        """)
        
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(12, 8, 12, 8)
        
        version_label = QLabel(version_name)
        version_label.setStyleSheet("color: #c9d1d9; font-size: 13px; font-weight: 500;")
        item_layout.addWidget(version_label)
        item_layout.addStretch()
        
        if is_installed:
            btn = QPushButton("🗑️ Удалить")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 1px solid #f85149;
                    border-radius: 6px;
                    padding: 6px 16px;
                    color: #f85149;
                    font-size: 12px;
                }
                QPushButton:hover { background-color: rgba(248, 81, 73, 0.1); }
            """)
            btn.clicked.connect(lambda: self.uninstall_version(version_name, item_widget))
        else:
            btn = QPushButton("⬇️ Установить")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #238636;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    color: white;
                    font-size: 12px;
                }
                QPushButton:hover { background-color: #2ea043; }
            """)
            btn.clicked.connect(lambda: self.install_version(version_name, download_url))
        
        item_layout.addWidget(btn)
        setattr(item_widget, 'version_name', version_name)
        self.versions_layout.addWidget(item_widget)
    
    def filter_versions(self):
        if not self._is_alive:
            return
        
        search_text = self.search_input.text().lower()
        for i in range(self.versions_layout.count()):
            item = self.versions_layout.itemAt(i)
            if item and item.widget():
                version_name = getattr(item.widget(), 'version_name', '')
                item.widget().setVisible(search_text in version_name.lower())
    
    def install_version(self, version_name: str, download_url: str):
        if not self._is_alive:
            return
        
        if self.download_progress:
            self.download_progress.update_progress(f"Загрузка {version_name}", 0)
        
        self.install_thread = ProtonInstallWorker(version_name, download_url, self.proton_dir, self.cache_dir)
        self.install_thread.progress.connect(lambda p: self.update_progress(version_name, p))
        self.install_thread.log.connect(lambda msg: print(msg))
        self.install_thread.finished.connect(lambda success, msg: self.on_install_finished(version_name, success, msg))
        self.install_thread.start()
    
    def update_progress(self, version_name: str, percent: int):
        if self._is_alive and self.download_progress:
            self.download_progress.update_progress(f"Загрузка {version_name}", percent)
    
    def on_install_finished(self, version_name: str, success: bool, msg: str):
        if not self._is_alive:
            return
        
        if self.download_progress:
            if success:
                self.download_progress.update_progress(f"{version_name} установлен", 100)
            else:
                self.download_progress.update_progress(f"Ошибка: {version_name}", 100)
        
        if success:
            self.load_versions()
            print(f"✅ {version_name} успешно установлен!")
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить {version_name}:\n{msg}")
    
    def uninstall_version(self, version_name: str, item_widget: QWidget):
        if not self._is_alive:
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить {version_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            version_path = self.proton_dir / version_name
            try:
                shutil.rmtree(version_path)
                QMessageBox.information(self, "Успех", f"{version_name} успешно удален!")
                self.load_versions()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить {version_name}:\n{e}")


# ============================================================
# РАБОЧИЙ ПОТОК ДЛЯ УСТАНОВКИ DXVK
# ============================================================

class DXVKInstallWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, prefix_path: Path):
        super().__init__()
        self.prefix_path = prefix_path
        self.cache_dir = Path.home() / ".cache/blitz-launcher/dxvk"

    def run(self):
        try:
            self.log.emit("🔍 Получение последней версии DXVK...")
            version = DXVKVersionFetcher.get_latest_version()
            if not version:
                version = "2.5.3"
                self.log.emit(f"⚠️ Используем версию по умолчанию: {version}")

            download_url = DXVKVersionFetcher.get_download_url(version)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.log.emit(f"📥 Скачивание DXVK {version}...")

            archive_path = self.cache_dir / f"dxvk-{version}.tar.gz"
            if not archive_path.exists():
                req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=60) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    chunk_size = 8192
                    with open(archive_path, 'wb') as f:
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = int(downloaded * 100 / total_size)
                                self.progress.emit(percent)
            else:
                self.log.emit("📁 DXVK найден в кэше")
                self.progress.emit(100)

            self.log.emit(f"📦 Распаковка DXVK {version}...")

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.extractall(tmp_path)

                extracted_dir = None
                for item in tmp_path.iterdir():
                    if item.is_dir() and "dxvk" in item.name:
                        extracted_dir = item
                        break

                if not extracted_dir:
                    raise Exception("Не удалось найти распакованную папку DXVK")

                x32_dir = extracted_dir / "x32"
                x64_dir = extracted_dir / "x64"

                prefix_windows = self.prefix_path / "drive_c" / "windows"
                prefix_system32 = prefix_windows / "system32"
                prefix_syswow64 = prefix_windows / "syswow64"

                prefix_system32.mkdir(parents=True, exist_ok=True)
                prefix_syswow64.mkdir(parents=True, exist_ok=True)

                if x64_dir.exists():
                    for file in x64_dir.glob("*.dll"):
                        dest = prefix_system32 / file.name
                        shutil.copy2(file, dest)
                        self.log.emit(f"  ✅ {file.name} -> system32/")

                if x32_dir.exists():
                    for file in x32_dir.glob("*.dll"):
                        dest = prefix_syswow64 / file.name
                        shutil.copy2(file, dest)
                        self.log.emit(f"  ✅ {file.name} -> syswow64/")

                marker = self.prefix_path / ".dxvk_installed"
                marker.write_text(version)

            self.log.emit(f"✅ DXVK {version} успешно установлен в префикс!")
            self.finished.emit(True, f"DXVK {version} установлен")

        except Exception as e:
            self.log.emit(f"❌ Ошибка: {str(e)}")
            self.finished.emit(False, str(e))


# ============================================================
# РАБОЧИЙ ПОТОК ДЛЯ УСТАНОВКИ UMU
# ============================================================

class UMUInstallWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, umu_dir: Path):
        super().__init__()
        self.umu_dir = umu_dir
        self.umu_run = umu_dir / "umu-run"
        self.umu_url = "https://github.com/Open-Wine-Components/umu-launcher/releases/download/1.4.0/umu-launcher-1.4.0-zipapp.tar"

    def run(self):
        tmp_path = None
        try:
            self.log.emit("📥 Скачивание UMU Launcher...")
            req = urllib.request.Request(self.umu_url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tar') as tmp_file:
                tmp_path = Path(tmp_file.name)
                with urllib.request.urlopen(req, timeout=60) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    chunk_size = 8192
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk: break
                        tmp_file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            self.progress.emit(int(downloaded * 100 / total_size))

            self.log.emit("📦 Распаковка UMU (чистка структуры)...")
            
            # Полная пересоздание папки umu
            if self.umu_dir.exists():
                shutil.rmtree(self.umu_dir)
            self.umu_dir.mkdir(parents=True, exist_ok=True)

            with tarfile.open(tmp_path, 'r:*') as tar:
                members = tar.getmembers()
                for member in members:
                    # Разбиваем путь внутри архива на части
                    parts = Path(member.name).parts
                    
                    # Если файл внутри папки (длина пути > 1), отрезаем первый уровень
                    if len(parts) > 1:
                        # Создаем новый путь без первой папки (umu-launcher-1.4.0/)
                        member.name = str(Path(*parts[1:]))
                        tar.extract(member, path=self.umu_dir)
                    # Если файл в корне архива и это не папка, извлекаем как есть
                    elif not member.isdir():
                        tar.extract(member, path=self.umu_dir)

            # Установка прав на исполнение
            if self.umu_run.exists():
                self.umu_run.chmod(0o755)
                self.log.emit("✅ UMU установлен корректно!")
                self.finished.emit(True, "Успех")
            else:
                raise Exception("Файл umu-run не найден в корне папки umu")

        except Exception as e:
            self.log.emit(f"❌ Ошибка: {str(e)}")
            self.finished.emit(False, str(e))
        
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)


# ============================================================
# МЕНЕДЖЕР UMU
# ============================================================

class UMUManager:
    _instance = None
    _install_lock = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        app_dir = get_app_dir()
        self.umu_dir = app_dir / "umu"
        self.umu_run = self.umu_dir / "umu-run"

    def is_available(self) -> bool:
        if shutil.which("umu-run"):
            return True
        return self.umu_run.exists() and self.umu_run.is_file()

    def ensure_umu(self, parent=None) -> bool:
        if self.is_available():
            return True

        if UMUManager._install_lock:
            QMessageBox.warning(parent, "Установка", "Установка UMU уже выполняется")
            return False

        UMUManager._install_lock = True
        try:
            if not self.umu_dir.exists():
                self.umu_dir.mkdir(parents=True, exist_ok=True)

            dialog = InstallProgressDialog("Установка UMU", parent)
            result_flag = [False]

            worker = UMUInstallWorker(self.umu_dir)
            worker.progress.connect(dialog.set_progress)
            worker.log.connect(dialog.add_log)

            def on_finished(success, msg):
                result_flag[0] = success
                dialog.accept()

            worker.finished.connect(on_finished)

            dialog.set_title("Автоматическая установка UMU")
            dialog.set_icon("⚡")
            dialog.set_progress_range(0, 100)
            dialog.add_log("Для запуска игр необходим UMU Launcher")
            dialog.add_log("Начинаем автоматическую установку...")

            worker.start()
            dialog.exec()
            return result_flag[0]
        finally:
            UMUManager._install_lock = False

    def ensure_dxvk(self, prefix_path: Path, parent=None, dialog_callback=None) -> bool:
        marker = prefix_path / ".dxvk_installed"
        if marker.exists():
            version = marker.read_text().strip()
            if dialog_callback:
                dialog_callback(f"✅ DXVK {version} уже установлен")
            return True

        dialog = InstallProgressDialog("Установка DXVK", parent)
        result_flag = [False]

        worker = DXVKInstallWorker(prefix_path)
        worker.progress.connect(dialog.set_progress)
        worker.log.connect(dialog.add_log)

        def on_finished(success, msg):
            result_flag[0] = success
            dialog.accept()
            if dialog_callback:
                dialog_callback(msg)

        worker.finished.connect(on_finished)

        dialog.set_title("Установка DXVK (последняя версия)")
        dialog.set_icon("⚡")
        dialog.set_progress_range(0, 100)
        dialog.add_log("DXVK улучшает производительность DirectX игр")
        dialog.add_log("Начинаем автоматическую установку последней версии...")

        worker.start()
        dialog.exec()
        return result_flag[0]

    def get_safe_prefix_name(self, game_title: str) -> str:
        safe = re.sub(r'[<>:"/\\|?*]', '_', game_title)
        safe = safe.replace(' ', '_')
        safe = re.sub(r'_+', '_', safe)
        safe = safe.strip('_')
        if len(safe) > 50:
            safe = safe[:50]
        return safe

    def get_prefix_path(self, game_title: str, game_id: int) -> Path:
        safe_name = self.get_safe_prefix_name(game_title)
        return Path.home() / "Games" / "prefix" / f"{game_id}_{safe_name}"

    def find_proton_path(self, version: str) -> Optional[str]:
        search_dirs = [
            Path.home() / ".local/share/Steam/compatibilitytools.d",
            Path.home() / ".steam/root/compatibilitytools.d",
            Path.home() / ".steam/steam/compatibilitytools.d",
        ]
        for search_dir in search_dirs:
            if search_dir.exists():
                for item in search_dir.iterdir():
                    if item.is_dir() and version in item.name:
                        if ProtonManager.is_valid_proton_path(item):
                            return str(item)
        return None

    def find_any_ge_proton(self) -> Optional[str]:
        proton_manager = ProtonManager()
        installed = proton_manager.get_installed_versions()
        for version in installed:
            if "GE-Proton" in version or "GE" in version:
                path = self.find_proton_path(version)
                if path:
                    return path
        for version in installed:
            path = self.find_proton_path(version)
            if path:
                return path
        return None

    def clean_proton_version(self, proton_version: str) -> Optional[str]:
        if not proton_version:
            return None
        clean = proton_version
        if clean.startswith("⚡ ") or clean.startswith("📦 "):
            clean = clean[2:]
        if clean.startswith("⚠️ "):
            return None
        if clean == "GE-Proton (по умолчанию)":
            return None
        return clean.strip()

    def launch_with_options(self, exe_path: str, game_id: int, game_title: str,
                            proton_version: str = None, parent=None, db=None, extra_env=None):
        """Запуск игры с опциями (без диалога)"""

        if not self.ensure_umu(parent):
            QMessageBox.critical(parent, "Ошибка", "Не удалось установить UMU")
            return None

        env = {}

        # Добавляем дополнительные переменные из GameDetailsPage (MangoHud и т.д.)
        if extra_env:
            env.update(extra_env)
            if extra_env.get("MANGOHUD") == "1":
                print("🎮 MangoHud включен")
                inline_cfg = extra_env.get("MANGOHUD_CONFIG")
                if inline_cfg:
                    env["MANGOHUD_CONFIG"] = inline_cfg
                    print(f"📝 MangoHud конфиг (inline): {inline_cfg}")
                else:
                    config_path = SystemChecker.update_mangohud_config()
                    env["MANGOHUD_CONFIG"] = str(config_path)
                    print(f"📝 MangoHud конфиг: {config_path}")
            if extra_env.get("GAMEMODERUN") == "1":
                print("⚡ Gamemode включен")
            if extra_env.get("WINEESYNC") == "1":
                print("⚙️ Esync включен")
            if extra_env.get("WINEFSYNC") == "1":
                print("⚙️ Fsync включен")

        prefix_path = self.get_prefix_path(game_title, game_id)
        prefix_path.mkdir(parents=True, exist_ok=True)

        print(f"\n📁 Префикс игры: {prefix_path}")
        self.ensure_dxvk(prefix_path, parent, lambda msg: print(msg))

        env["GAMEID"] = f"umu-{game_id}"
        env["WINEPREFIX"] = str(prefix_path)
        env["STORE"] = "local"
        env.pop("PROTONPATH", None)
        env.pop("PROTON_VERSION", None)

        clean_version = self.clean_proton_version(proton_version)

        if clean_version:
            proton_path = self.find_proton_path(clean_version)
            if proton_path:
                env["PROTONPATH"] = proton_path
                env["PROTON_VERSION"] = clean_version
                print(f"🐚 Используется Proton: {clean_version}")
            else:
                ge_proton = self.find_any_ge_proton()
                if ge_proton:
                    env["PROTONPATH"] = ge_proton
                    env["PROTON_VERSION"] = Path(ge_proton).name
                    print(f"🐚 Используется GE-Proton: {Path(ge_proton).name}")
        else:
            ge_proton = self.find_any_ge_proton()
            if ge_proton:
                env["PROTONPATH"] = ge_proton
                env["PROTON_VERSION"] = Path(ge_proton).name
                print(f"🐚 Используется GE-Proton по умолчанию: {Path(ge_proton).name}")

        history_id = None
        if db:
            history_id = db.add_launch_record(game_id=game_id)
            print(f"📝 Запись в истории: {history_id}")

        if env.get("GAMEMODERUN") == "1":
            cmd = ["gamemoderun", str(self.umu_run), exe_path]
            print("⚡ Запуск через gamemoderun")
        else:
            cmd = [str(self.umu_run), exe_path]

        final_env = os.environ.copy()
        final_env.update(env)

        print(f"\n⚡ Команда запуска: {' '.join(cmd)}")
        print(f"\n📋 Финальные переменные окружения:")
        for key in ['GAMEID', 'WINEPREFIX', 'PROTONPATH', 'PROTON_VERSION', 'GAMEMODERUN', 'MANGOHUD', 'MANGOHUD_CONFIG']:
            if key in final_env:
                print(f"   {key}={final_env[key]}")

        try:
            process = subprocess.Popen(cmd, env=final_env, start_new_session=True)
            if history_id and parent:
                if hasattr(parent, 'all_games_page'):
                    for game in parent.all_games_page.model.games:
                        if game.get('id') == game_id:
                            # Сохраняем history_id в карточке
                            pass
            return process
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None


# ============================================================
# ФУНКЦИЯ ДЛЯ ЗАПУСКА ИГРЫ
# ============================================================

def auto_setup_umu_and_launch(exe_path: str, game_id: int, proton_version: str, parent=None) -> bool:
    umu_manager = UMUManager()
    if not umu_manager.ensure_umu(parent):
        QMessageBox.critical(parent, "Ошибка", "Не удалось установить UMU")
        return False
    proton_manager = ProtonManager()
    if proton_version and proton_version != "GE-Proton (по умолчанию)":
        clean_version = umu_manager.clean_proton_version(proton_version)
        if clean_version and not proton_manager.is_version_installed(clean_version):
            QMessageBox.warning(parent, "Требуется GE-Proton",
                               f"Для запуска игры необходим {clean_version}\n\n"
                               f"Установите его через менеджер Proton")
            return False
    return True
