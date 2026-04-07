import json
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QTextEdit, QGroupBox, QCheckBox, QMessageBox, QFrame,
    QSplitter, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPalette

from proton_manager import ProtonManager


class ProfileManagerDialog(QDialog):
    """Диалог управления профилями запуска для игры в Blitz"""

    profile_changed = Signal()

    def __init__(self, game_id: int, game_title: str, db, parent=None):
        super().__init__(parent)
        self.game_id = game_id
        self.game_title = game_title
        self.db = db
        self.current_profile_id = None
        self.proton_manager = None

        self.setWindowTitle(f"Профили запуска - {game_title} (Blitz)")
        self.setMinimumSize(900, 600)
        self.setModal(True)

        self.setup_ui()
        self.load_proton_manager()
        self.load_profiles()

        # Применяем тёмную тему
        self.setStyleSheet(self.get_stylesheet())

    def get_stylesheet(self):
        return """
            QDialog {
                background-color: #0d1117;
            }
            QLabel {
                color: #c9d1d9;
                font-size: 12px;
            }
            QLabel#title_label {
                font-size: 18px;
                font-weight: bold;
                color: #58a6ff;
                padding: 10px;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px;
                color: #c9d1d9;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #58a6ff;
            }
            QGroupBox {
                color: #58a6ff;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
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
            QPushButton {
                background-color: #238636;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QPushButton#delete_btn {
                background-color: #da3633;
            }
            QPushButton#delete_btn:hover {
                background-color: #f85149;
            }
            QPushButton#cancel_btn {
                background-color: transparent;
                border: 1px solid #f85149;
                color: #f85149;
            }
            QPushButton#cancel_btn:hover {
                background-color: rgba(248, 81, 73, 0.1);
            }
            QListWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 5px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 8px;
                border-radius: 6px;
                margin: 2px;
                color: #c9d1d9;
            }
            QListWidget::item:hover {
                background-color: #21262d;
            }
            QListWidget::item:selected {
                background-color: #1f6feb;
                color: white;
            }
            QSplitter::handle {
                background-color: #30363d;
                width: 2px;
            }
            QFrame#right_panel {
                background-color: #161b22;
                border-radius: 12px;
                padding: 16px;
            }
            QTextEdit {
                font-family: monospace;
                font-size: 11px;
            }
        """

    def load_proton_manager(self):
        """Загрузить менеджер Proton"""
        try:
            self.proton_manager = ProtonManager()
        except ImportError:
            pass

    def setup_ui(self):
        """Настройка интерфейса Blitz"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Заголовок
        title_label = QLabel(f"⚡ Управление профилями запуска")
        title_label.setObjectName("title_label")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        subtitle = QLabel(f"Игра: {self.game_title}")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #8b949e; font-size: 11px; margin-bottom: 10px;")
        layout.addWidget(subtitle)

        # Основной сплиттер
        splitter = QSplitter(Qt.Horizontal)

        # ========== ЛЕВАЯ ПАНЕЛЬ - СПИСОК ПРОФИЛЕЙ ==========
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)

        left_layout.addWidget(QLabel("📁 МОИ ПРОФИЛИ:"))

        self.profile_list = QListWidget()
        self.profile_list.setMinimumWidth(250)
        self.profile_list.itemClicked.connect(self.on_profile_selected)
        self.profile_list.itemDoubleClicked.connect(self.duplicate_profile)
        left_layout.addWidget(self.profile_list)

        # Кнопки управления профилями
        btn_grid = QVBoxLayout()
        btn_grid.setSpacing(8)

        self.add_btn = QPushButton("➕ Новый профиль")
        self.add_btn.clicked.connect(self.add_profile)
        btn_grid.addWidget(self.add_btn)

        self.duplicate_btn = QPushButton("📋 Дублировать")
        self.duplicate_btn.clicked.connect(self.duplicate_current_profile)
        self.duplicate_btn.setEnabled(False)
        btn_grid.addWidget(self.duplicate_btn)

        self.set_default_btn = QPushButton("⚡ По умолчанию")
        self.set_default_btn.clicked.connect(self.set_as_default)
        self.set_default_btn.setEnabled(False)
        btn_grid.addWidget(self.set_default_btn)

        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.setObjectName("delete_btn")
        self.delete_btn.clicked.connect(self.delete_profile)
        self.delete_btn.setEnabled(False)
        btn_grid.addWidget(self.delete_btn)

        left_layout.addLayout(btn_grid)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # ========== ПРАВАЯ ПАНЕЛЬ - НАСТРОЙКИ ПРОФИЛЯ ==========
        right_widget = QFrame()
        right_widget.setObjectName("right_panel")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(12)

        # Индикатор режима
        self.mode_label = QLabel("⚙️ РЕДАКТИРОВАНИЕ ПРОФИЛЯ")
        self.mode_label.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        right_layout.addWidget(self.mode_label)

        # Название профиля
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Название профиля:"))
        self.profile_name = QLineEdit()
        self.profile_name.setPlaceholderText("Например: Максимальная производительность, Отладка, Совместимость...")
        self.profile_name.textChanged.connect(self.on_name_changed)
        name_layout.addWidget(self.profile_name)
        right_layout.addLayout(name_layout)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #30363d; max-height: 1px; margin: 5px 0;")
        right_layout.addWidget(line)

        # ========== ВКЛАДКИ НАСТРОЕК ==========
        # Proton версия
        proton_group = QGroupBox("🐚 PROTON")
        proton_layout = QVBoxLayout(proton_group)

        self.proton_combo = QComboBox()
        self.proton_combo.addItem("🌍 GE-Proton (авто-выбор)", None)
        self.proton_combo.addItem("⚙️ Системный Proton", "system")
        right_layout.addWidget(proton_group)
        proton_layout.addWidget(self.proton_combo)

        # Аргументы запуска
        args_group = QGroupBox("🎮 АРГУМЕНТЫ ЗАПУСКА")
        args_layout = QVBoxLayout(args_group)

        self.launch_options = QLineEdit()
        self.launch_options.setPlaceholderText("-dx11 -high -USEALLAVAILABLECORES -novid -console")
        args_layout.addWidget(self.launch_options)

        hint = QLabel("💡 Популярные аргументы: -dx11, -dx9, -high, -low, -windowed, -fullscreen, -novid")
        hint.setStyleSheet("color: #8b949e; font-size: 10px;")
        hint.setWordWrap(True)
        args_layout.addWidget(hint)

        right_layout.addWidget(args_group)

        # Переменные окружения
        env_group = QGroupBox("🔧 ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ")
        env_layout = QVBoxLayout(env_group)

        self.env_edit = QTextEdit()
        self.env_edit.setPlaceholderText('{\n    "MANGOHUD": "1",\n    "DXVK_HUD": "fps",\n    "WINEDEBUG": "-all"\n}')
        self.env_edit.setMaximumHeight(120)
        env_layout.addWidget(self.env_edit)

        env_hint = QLabel("💡 JSON формат. Поддерживаемые переменные: MANGOHUD, GAMEMODERUN, DXVK_HUD, VKD3D_CONFIG, WINEDEBUG")
        env_hint.setStyleSheet("color: #8b949e; font-size: 10px;")
        env_hint.setWordWrap(True)
        env_layout.addWidget(env_hint)

        right_layout.addWidget(env_group)

        # Дополнительные настройки
        advanced_group = QGroupBox("⚙️ ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ")
        advanced_layout = QVBoxLayout(advanced_group)

        checkbox_layout = QHBoxLayout()

        self.esync_check = QCheckBox("Esync (Eventfd синхронизация)")
        self.fsync_check = QCheckBox("Fsync (Futex синхронизация)")

        checkbox_layout.addWidget(self.esync_check)
        checkbox_layout.addWidget(self.fsync_check)
        checkbox_layout.addStretch()
        advanced_layout.addLayout(checkbox_layout)

        perf_layout = QHBoxLayout()

        self.mangohud_check = QCheckBox("MangoHud (мониторинг производительности)")
        self.gamemode_check = QCheckBox("Gamemode (оптимизация системы)")

        perf_layout.addWidget(self.mangohud_check)
        perf_layout.addWidget(self.gamemode_check)
        perf_layout.addStretch()
        advanced_layout.addLayout(perf_layout)

        right_layout.addWidget(advanced_group)

        # Предпросмотр команды запуска
        preview_group = QGroupBox("📋 ПРЕДПРОСМОТР КОМАНДЫ ЗАПУСКА")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(80)
        self.preview_text.setStyleSheet("font-family: monospace; font-size: 10px;")
        preview_layout.addWidget(self.preview_text)

        right_layout.addWidget(preview_group)

        # Кнопки сохранения
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_btn = QPushButton("💾 СОХРАНИТЬ ПРОФИЛЬ")
        self.save_btn.setStyleSheet("background-color: #238636; font-weight: bold; padding: 10px 24px;")
        self.save_btn.clicked.connect(self.save_profile)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)

        button_layout.addStretch()
        right_layout.addLayout(button_layout)

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 600])

        layout.addWidget(splitter)

        # Кнопка закрытия
        close_layout = QHBoxLayout()
        close_layout.addStretch()

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.clicked.connect(self.reject)
        close_layout.addWidget(self.cancel_btn)

        layout.addLayout(close_layout)

        # Таймер для обновления предпросмотра
        self.preview_timer = QTimer()
        self.preview_timer.setInterval(500)
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start()

    def load_profiles(self):
        """Загрузить список профилей"""
        self.profile_list.clear()
        profiles = self.db.get_launch_profiles(self.game_id)

        if not profiles:
            # Создаём профиль по умолчанию, если нет ни одного
            self.create_default_profile()
            profiles = self.db.get_launch_profiles(self.game_id)

        for profile in profiles:
            item = QListWidgetItem()
            item.setData(32, profile['id'])

            # Форматируем отображение
            name = profile['profile_name']
            if profile.get('is_default', 0) == 1:
                item.setText(f"⚡ {name}")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            else:
                item.setText(name)

            self.profile_list.addItem(item)

        self.update_profile_count()

    def create_default_profile(self):
        """Создать профиль по умолчанию"""
        self.db.add_launch_profile(
            game_id=self.game_id,
            profile_name="Стандартный",
            proton_version=None,
            launch_options="",
            environment='{"MANGOHUD": "1", "GAMEMODERUN": "1"}',
            is_default=True
        )

    def update_profile_count(self):
        """Обновить счётчик профилей"""
        count = self.profile_list.count()
        if hasattr(self, 'profile_list') and self.profile_list.parent():
            # Можно добавить отображение количества
            pass

    def load_proton_versions(self):
        """Загрузить установленные версии Proton"""
        if not self.proton_manager:
            return

        # Очищаем, оставляя только первые два пункта
        while self.proton_combo.count() > 2:
            self.proton_combo.removeItem(2)

        versions = self.proton_manager.get_installed_versions()

        for version in versions:
            if "GE-Proton" in version:
                self.proton_combo.addItem(f"⚡ {version}", version)
            else:
                self.proton_combo.addItem(f"📦 {version}", version)

    def on_profile_selected(self, item):
        """Выбор профиля для редактирования"""
        self.current_profile_id = item.data(32)

        # Включаем кнопки
        self.duplicate_btn.setEnabled(True)
        self.set_default_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.mode_label.setText("✏️ РЕДАКТИРОВАНИЕ ПРОФИЛЯ")

        # Загружаем данные профиля
        profiles = self.db.get_launch_profiles(self.game_id)
        profile = next((p for p in profiles if p['id'] == self.current_profile_id), None)

        if profile:
            self.profile_name.setText(profile['profile_name'])

            # Proton версия
            proton = profile.get('proton_version', '')
            if proton:
                # Ищем в комбобоксе
                index = -1
                for i in range(self.proton_combo.count()):
                    if self.proton_combo.itemData(i) == proton:
                        index = i
                        break
                if index >= 0:
                    self.proton_combo.setCurrentIndex(index)
                else:
                    self.proton_combo.setCurrentIndex(0)
            else:
                self.proton_combo.setCurrentIndex(0)

            self.launch_options.setText(profile.get('launch_options', ''))

            # Переменные окружения
            env = profile.get('environment', '')
            try:
                if env:
                    parsed = json.loads(env)
                    self.env_edit.setText(json.dumps(parsed, indent=2))
                else:
                    self.env_edit.clear()
            except:
                self.env_edit.setText(env)

            # Чекбоксы (парсим из environment)
            env_dict = {}
            if profile.get('environment'):
                try:
                    env_dict = json.loads(profile['environment'])
                except:
                    pass

            self.esync_check.setChecked(env_dict.get('WINEESYNC') == '1')
            self.fsync_check.setChecked(env_dict.get('WINEFSYNC') == '1')
            self.mangohud_check.setChecked(env_dict.get('MANGOHUD') == '1')
            self.gamemode_check.setChecked(env_dict.get('GAMEMODERUN') == '1')

    def add_profile(self):
        """Создать новый профиль"""
        self.current_profile_id = None
        self.profile_name.clear()
        self.launch_options.clear()
        self.env_edit.clear()
        self.proton_combo.setCurrentIndex(0)
        self.esync_check.setChecked(False)
        self.fsync_check.setChecked(False)
        self.mangohud_check.setChecked(True)  # По умолчанию включено
        self.gamemode_check.setChecked(True)  # По умолчанию включено

        self.duplicate_btn.setEnabled(False)
        self.set_default_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.save_btn.setEnabled(True)
        self.mode_label.setText("✨ СОЗДАНИЕ НОВОГО ПРОФИЛЯ")

        self.profile_name.setFocus()

    def duplicate_current_profile(self):
        """Дублировать текущий профиль"""
        if not self.current_profile_id:
            return

        profiles = self.db.get_launch_profiles(self.game_id)
        profile = next((p for p in profiles if p['id'] == self.current_profile_id), None)

        if profile:
            # Создаём копию
            new_name = f"{profile['profile_name']} (копия)"

            self.db.add_launch_profile(
                game_id=self.game_id,
                profile_name=new_name,
                proton_version=profile.get('proton_version'),
                launch_options=profile.get('launch_options'),
                environment=profile.get('environment'),
                is_default=False
            )

            self.load_profiles()
            QMessageBox.information(self, "Успех", f"Профиль «{new_name}» создан!")

    def delete_profile(self):
        """Удалить профиль"""
        if not self.current_profile_id:
            return

        # Проверяем, не последний ли это профиль
        profiles = self.db.get_launch_profiles(self.game_id)
        if len(profiles) <= 1:
            QMessageBox.warning(self, "Предупреждение",
                "Нельзя удалить единственный профиль.\n"
                "Сначала создайте новый профиль.")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить этот профиль?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            with self.db.get_connection() as conn:
                conn.execute("DELETE FROM launch_profiles WHERE id = ?", (self.current_profile_id,))

            self.current_profile_id = None
            self.load_profiles()
            self.clear_form()
            self.save_btn.setEnabled(False)
            self.duplicate_btn.setEnabled(False)
            self.set_default_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.mode_label.setText("⚙️ ВЫБЕРИТЕ ПРОФИЛЬ ДЛЯ РЕДАКТИРОВАНИЯ")

    def set_as_default(self):
        """Сделать профиль профилем по умолчанию"""
        if not self.current_profile_id:
            return

        with self.db.get_connection() as conn:
            conn.execute("UPDATE launch_profiles SET is_default = 0 WHERE game_id = ?", (self.game_id,))
            conn.execute("UPDATE launch_profiles SET is_default = 1 WHERE id = ?", (self.current_profile_id,))

        self.load_profiles()
        QMessageBox.information(self, "Успех", "Профиль установлен по умолчанию!")

    def on_name_changed(self):
        """При изменении имени профиля обновляем предпросмотр"""
        self.update_preview()

    def update_preview(self):
        """Обновить предпросмотр команды запуска"""
        # Собираем настройки
        env = self.build_environment()
        launch_options = self.launch_options.text().strip()
        proton = self.proton_combo.currentData()

        # Формируем предпросмотр
        preview_lines = []

        if env:
            preview_lines.append("# Переменные окружения:")
            for key, value in env.items():
                preview_lines.append(f'  {key}="{value}"')

        if proton:
            preview_lines.append(f"# Proton: {proton}")
        else:
            preview_lines.append("# Proton: авто-выбор")

        if launch_options:
            preview_lines.append(f"# Аргументы: {launch_options}")

        preview_lines.append("")
        preview_lines.append("umu-run <путь_к_игре.exe> " + launch_options)

        self.preview_text.setText("\n".join(preview_lines))

    def build_environment(self) -> dict:
        """Собрать переменные окружения из настроек"""
        env = {}

        if self.esync_check.isChecked():
            env["WINEESYNC"] = "1"
        if self.fsync_check.isChecked():
            env["WINEFSYNC"] = "1"
        if self.mangohud_check.isChecked():
            env["MANGOHUD"] = "1"
        if self.gamemode_check.isChecked():
            env["GAMEMODERUN"] = "1"

        # Добавляем пользовательские переменные
        custom_env = self.env_edit.toPlainText().strip()
        if custom_env:
            try:
                custom = json.loads(custom_env)
                env.update(custom)
            except json.JSONDecodeError:
                pass

        return env

    def save_profile(self):
        """Сохранить профиль"""
        profile_name = self.profile_name.text().strip()
        if not profile_name:
            QMessageBox.warning(self, "Ошибка", "Введите название профиля")
            return

        # Собираем переменные окружения
        env = self.build_environment()

        proton_version = self.proton_combo.currentData()
        if proton_version == "system":
            proton_version = None

        launch_options = self.launch_options.text().strip()

        if self.current_profile_id:
            # Обновляем существующий профиль (удаляем и создаём заново)
            with self.db.get_connection() as conn:
                # Сохраняем флаг is_default
                result = conn.execute(
                    "SELECT is_default FROM launch_profiles WHERE id = ?",
                    (self.current_profile_id,)
                ).fetchone()
                was_default = result[0] if result else 0

                # Удаляем старый
                conn.execute("DELETE FROM launch_profiles WHERE id = ?", (self.current_profile_id,))

                # Создаём новый
                conn.execute("""
                    INSERT INTO launch_profiles
                    (game_id, profile_name, proton_version, launch_options, environment, is_default)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (self.game_id, profile_name, proton_version, launch_options,
                      json.dumps(env) if env else None, was_default))

            QMessageBox.information(self, "Успех", f"Профиль «{profile_name}» обновлён!")
        else:
            # Создаём новый профиль
            is_default = self.profile_list.count() == 0

            self.db.add_launch_profile(
                game_id=self.game_id,
                profile_name=profile_name,
                proton_version=proton_version,
                launch_options=launch_options,
                environment=json.dumps(env) if env else None,
                is_default=is_default
            )

            QMessageBox.information(self, "Успех", f"Профиль «{profile_name}» создан!")

        self.load_profiles()
        self.save_btn.setEnabled(False)

        # Если это был новый профиль, очищаем форму
        if not self.current_profile_id:
            self.clear_form()

    def clear_form(self):
        """Очистить форму"""
        self.profile_name.clear()
        self.launch_options.clear()
        self.env_edit.clear()
        self.proton_combo.setCurrentIndex(0)
        self.esync_check.setChecked(False)
        self.fsync_check.setChecked(False)
        self.mangohud_check.setChecked(True)
        self.gamemode_check.setChecked(True)

    def duplicate_profile(self, item):
        """Дублировать профиль по двойному клику"""
        self.on_profile_selected(item)
        self.duplicate_current_profile()

    def closeEvent(self, event):
        """Закрытие окна"""
        self.preview_timer.stop()
        event.accept()
