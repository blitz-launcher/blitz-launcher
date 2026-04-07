THEME = """
/* ========== ГЛОБАЛЬНЫЕ СТИЛИ ========== */
* {
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

QMainWindow {
    background-color: #0d1117;
}

/* ========== СТИЛИ ДЛЯ QGraphicsView (размытый фон) ========== */
QGraphicsView {
    background: transparent;
    border: none;
}

/* ========== БОКОВАЯ ПАНЕЛЬ ========== */
QFrame#sidebar {
    background-color: #161b22;
}

QLabel#logo {
    font-size: 18px;
    font-weight: 600;
    color: #58a6ff;
    padding: 20px 20px 12px 20px;
}

/* Кнопка "Добавить игру" */
QPushButton#add_btn {
    background-color: #238636;
    border: none;
    border-radius: 0px;
    padding: 8px 20px;
    color: white;
    font-weight: 500;
    font-size: 13px;
    margin: 8px 0px;
    text-align: left;
}

QPushButton#add_btn:hover {
    background-color: #2ea043;
}

/* Кнопка "Выход" */
QPushButton#exit_btn {
    background-color: #da3633;
    border: none;
    border-radius: 0px;
    padding: 8px 20px;
    color: white;
    font-weight: 500;
    font-size: 13px;
    margin: 8px 0px;
    text-align: left;
}

QPushButton#exit_btn:hover {
    background-color: #f85149;
}

/* Группы в боковой панели */
QLabel.group-title {
    color: #8b949e;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    padding: 16px 20px 8px 20px;
}

/* Кнопки боковой панели */
.sidebar-btn {
    background-color: transparent;
    border: none;
    border-radius: 0px;
    padding: 8px 20px;
    margin: 0px;
    text-align: left;
}

.sidebar-btn:hover {
    background-color: #21262d;
}

.sidebar-btn[active="true"] {
    background-color: #1f6feb;
    border-left: 3px solid #58a6ff;
}

.sidebar-btn[active="true"] QLabel {
    color: #ffffff;
}

.sidebar-btn QLabel {
    color: #c9d1d9;
}

/* ========== СТРАНИЦА С ИГРАМИ (GRID VIEW) ========== */
/* Контейнер для поиска и сортировки */
QWidget#search_sort_container {
    background-color: transparent;
}

/* Поле поиска */
QLineEdit#search_box {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 10px 35px 10px 40px;
    color: #c9d1d9;
    font-size: 13px;
}

QLineEdit#search_box:focus {
    border-color: #58a6ff;
}

/* Иконка поиска (лупа) */
QLabel#search_icon {
    background-color: transparent;
    color: #8b949e;
}

/* Кнопка очистки поиска (крестик) */
QPushButton#clear_btn {
    background-color: transparent;
    border: none;
    color: #8b949e;
    font-size: 14px;
    font-weight: bold;
    border-radius: 14px;
}

QPushButton#clear_btn:hover {
    color: #f85149;
    background-color: rgba(248, 81, 73, 0.1);
}

/* Комбобокс сортировки */
QComboBox#sort_combo {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 12px;
    color: #c9d1d9;
    font-size: 13px;
    min-width: 180px;
    min-height: 32px;
}

QComboBox#proton_version_combo {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 12px;
    color: #c9d1d9;
    font-size: 13px;
    min-height: 32px;
}

QComboBox#proton_version_combo:hover {
    border-color: #58a6ff;
    background-color: #21262d;
}

QComboBox#sort_combo:hover {
    border-color: #58a6ff;
    background-color: #21262d;
}

/* Убираем стандартную стрелку */
QComboBox#sort_combo::drop-down {
    border: 0px;
    width: 0px;
}

QComboBox#sort_combo::down-arrow {
    image: none;
}

/* Стиль выпадающего списка */
QComboBox#sort_combo QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 4px;
    color: #c9d1d9;
}

QComboBox#sort_combo QAbstractItemView::item {
    padding: 6px 12px;
    border-radius: 4px;
}

QComboBox#sort_combo QAbstractItemView::item:hover {
    background-color: #21262d;
    color: #ffffff;
}

QComboBox#sort_combo QAbstractItemView::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}

QLabel#games_count {
    color: #c9d1d9;
    font-size: 22px;
    font-weight: 600;
}

QListView {
    background-color: #0d1117;
    border: none;
    outline: none;
    margin: 0px;
    padding: 0px;
}

QListView::item {
    background: transparent;
    padding: 0px;
    margin: 0px;
}

/* Скроллбары */
QScrollBar:vertical {
    background: #161b22;
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 3px;
    min-height: 40px;
}

QScrollBar::handle:vertical:hover {
    background: #484f58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ========== ВИДЖЕТ ПРОГРЕССА ЗАГРУЗКИ ========== */
DownloadProgress {
    background-color: #161b22;
    border-top: 1px solid #30363d;
    border-radius: 0px;
}

/* ========== УВЕДОМЛЕНИЯ (STEAM-LIKE) ========== */
QFrame#steam_notification {
    background-color: rgba(22, 27, 34, 245);
    border: 1px solid #30363d;
    border-left: 3px solid #58a6ff;
    border-radius: 10px;
    box-shadow: 0px 10px 26px rgba(0, 0, 0, 0.35);
}

QFrame#steam_notification[kind="success"] {
    border-left-color: #2ea043;
}

QFrame#steam_notification[kind="warning"] {
    border-left-color: #d29922;
}

QFrame#steam_notification[kind="error"] {
    border-left-color: #f85149;
}

QLabel#notification_accent {
    color: #58a6ff;
    font-size: 14px;
}

QLabel#notification_icon {
    color: #58a6ff;
    font-size: 15px;
}

QFrame#steam_notification[kind="error"] QLabel#notification_icon {
    color: #f85149;
}

QLabel#notification_title {
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

QLabel#notification_sep {
    color: #8b949e;
    font-size: 12px;
    padding: 0px 2px;
}

QLabel#notification_message {
    color: #c9d1d9;
    font-size: 12px;
}

QPushButton#notification_action {
    background: transparent;
    border: none;
    color: #3573d9;
    font-size: 11px;
    font-weight: 600;
    padding: 0px;
}

QPushButton#notification_action:hover {
    text-decoration: underline;
}

QFrame#notification_progress {
    background-color: #2ea043;
    border: none;
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
}

/* ========== СТРАНИЦА ДЕТАЛЕЙ ИГРЫ ========== */
GameDetailsPage {
    background-color: transparent;
}

GameDetailsPage QWidget {
    background-color: transparent;
}

/* Левая часть (обложка) - адаптивная */
GameDetailsPage QWidget#left_widget {
    min-width: 200px;
    max-width: 300px;
}

/* Правая часть - растягивается */
GameDetailsPage QWidget#right_widget {
    min-width: 300px;
}

/* Обложка - масштабируется */
QLabel#cover_label {
    background-color: #161b22;
    border-radius: 12px;
    min-width: 150px;
    min-height: 225px;
}

/* Название игры */
QLabel#title_label {
    color: #ffffff;
    font-size: 48px;
    font-weight: bold;
    font-family: 'Inter';
    word-wrap: break-word;
    word-break: break-word;
}

/* Кнопка "Назад" */
QPushButton#back_btn {
    background-color: transparent;
    border: 1px solid #58a6ff;
    border-radius: 8px;
    padding: 10px 20px;
    color: #58a6ff;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#back_btn:hover {
    background-color: rgba(88, 166, 255, 0.1);
}

/* Кнопка "ИГРАТЬ" */
QPushButton#play_btn {
    background-color: #238636;
    border: none;
    border-radius: 12px;
    padding: 16px 32px;
    color: white;
    font-size: 18px;
    font-weight: bold;
    letter-spacing: 1px;
}

QPushButton#play_btn:hover {
    background-color: #2ea043;
}

QPushButton#play_btn[loading="true"] {
    background-color: #1f6feb;
    color: #ffffff;
}

QPushButton#play_btn[loading="true"]:hover {
    background-color: #388bfd;
}

QPushButton#play_btn[in_game="true"] {
    background-color: #1f6feb;
    color: #ffffff;
}

/* Информационные панели */
QFrame#info_frame,
QFrame#profile_frame,
QFrame#settings_frame,
QFrame#toolbar_frame {
    background-color: #161b22;
    border-radius: 10px;
    padding: 12px;
    border: 1px solid #30363d;
}

QFrame#system_actions_frame {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    border-top: 1px solid #30363d;
    padding: 12px;
    margin-top: 4px;
}

/* Заголовки секций */
QLabel#settings_header,
QLabel#profile_header {
    color: #58a6ff !important;
    font-size: 12px;
    font-weight: bold;
}

QLabel#settings_status_label {
    color: #8b949e !important;
    font-size: 11px;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    padding-top: 2px;
}

/* Стили для скроллбара на странице деталей */
GameDetailsPage QScrollArea {
    background: transparent;
    border: none;
}

GameDetailsPage QScrollBar:vertical {
    background: #161b22;
    width: 6px;
    border-radius: 3px;
}

GameDetailsPage QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 3px;
    min-height: 40px;
}

GameDetailsPage QScrollBar::handle:vertical:hover {
    background: #484f58;
}

GameDetailsPage QScrollBar::add-line:vertical,
GameDetailsPage QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Комбобоксы на странице деталей */
GameDetailsPage QComboBox {
    color: #ffffff !important;
    background-color: #0d1117 !important;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px 8px;
}

GameDetailsPage QComboBox:hover {
    border-color: #58a6ff;
}

GameDetailsPage QComboBox::drop-down {
    border: none;
}

GameDetailsPage QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #ffffff;
    margin-right: 4px;
}

/* Чекбоксы для настроек (тумблеры) */
GameDetailsPage QCheckBox {
    color: #ffffff !important;
    spacing: 8px;
    font-size: 12px;
}

/* Чекбоксы для настроек (тумблеры) - расширенная версия */
GameDetailsPage QCheckBox {
    color: #ffffff !important;
    spacing: 8px;
    font-size: 12px;
}

GameDetailsPage QCheckBox::indicator {
    width: 40px;
    height: 20px;
    border-radius: 10px;
    border: 1px solid #444c56;
}

/* Чекбоксы для настроек */
GameDetailsPage QCheckBox {
    color: #ffffff !important;
    spacing: 8px;
    word-wrap: break-word;
    font-size: 12px;
}

/* Индикатор чекбокса (тумблер) */
GameDetailsPage QCheckBox::indicator {
    width: 40px;
    height: 20px;
    border-radius: 10px;
    border: 1px solid #444c56;
}

/* Выключенное состояние */
GameDetailsPage QCheckBox::indicator:unchecked {
    background-color: #30363d;
}

/* Включенное состояние */
GameDetailsPage QCheckBox::indicator:checked {
    background-color: #3573d9;
}

/* Hover эффекты */
GameDetailsPage QCheckBox::indicator:unchecked:hover {
    background-color: #3d444d;
}

GameDetailsPage QCheckBox::indicator:checked:hover {
    background-color: #4488e6;
}

/* Фокус */
GameDetailsPage QCheckBox:focus {
    outline: none;
}

/* Кнопки на панели инструментов */
GameDetailsPage QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 6px 12px;
    color: #c9d1d9;
    font-size: 12px;
}

GameDetailsPage QPushButton:hover {
    background-color: #30363d;
    border-color: #58a6ff;
    color: #ffffff !important;
}

QPushButton#system_action_btn {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 7px;
    padding: 4px 10px;
    min-height: 28px;
    color: #c9d1d9;
    font-size: 11px;
}

QPushButton#system_action_btn:hover {
    background-color: #30363d;
    border-color: #58a6ff;
    color: #ffffff;
}

QLabel#system_action_icon {
    color: #8b949e !important;
}

QLabel#system_action_icon[hovered="true"] {
    color: #ffffff !important;
}

QComboBox#proton_version_combo[systemAction="true"] {
    background-color: #0d1117 !important;
    border: 1px solid #30363d;
    border-radius: 7px;
    padding: 4px 10px;
    min-height: 28px;
    color: #c9d1d9 !important;
    font-size: 11px;
}

QComboBox#proton_version_combo[systemAction="true"]:hover {
    border-color: #58a6ff;
    color: #ffffff !important;
}

/* Общие стили для страницы деталей */
GameDetailsPage QLabel {
    color: #ffffff !important;
}

GameDetailsPage QFrame QLabel {
    color: #c9d1d9 !important;
}

/* ========== МЕНЮ ========== */
QMenu {
    background-color: #1e2436;
    border: 1px solid #2a2f42;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    background-color: transparent;
    color: #c9d1d9;
    padding: 8px 24px;
    border-radius: 4px;
    margin: 2px;
}

QMenu::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}

/* ========== КНОПКИ В ДИАЛОГАХ ========== */
QDialog QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 12px;
    color: #c9d1d9;
    font-size: 12px;
}

QDialog QPushButton:hover {
    background-color: #30363d;
    border-color: #58a6ff;
}

QDialog QPushButton:default {
    background-color: #238636;
    color: white;
    border: none;
}

QDialog QPushButton:default:hover {
    background-color: #2ea043;
}

/* ========== ПОЛЯ ВВОДА В ДИАЛОГАХ ========== */
QDialog QLineEdit {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    color: #c9d1d9;
    font-size: 13px;
}

QDialog QLineEdit:focus {
    border-color: #58a6ff;
}

/* ========== СТИЛИ ДЛЯ BLITZ ========== */
/* Молния в логотипе и иконках */
QLabel[blitz="true"] {
    color: #58a6ff;
}

/* Акцентные элементы с молнией */
QPushButton[blitz="true"] {
    background-color: #1f6feb;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    color: white;
    font-weight: bold;
}

QPushButton[blitz="true"]:hover {
    background-color: #58a6ff;
}
"""
