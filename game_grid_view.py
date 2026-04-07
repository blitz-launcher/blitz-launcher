import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListView, QAbstractItemView, QStyledItemDelegate, QStyle, QMenu,
    QMessageBox, QFileDialog, QDialog, QComboBox
)
from PySide6.QtCore import (
    Qt, QSize, QRect, QModelIndex, QPoint, Signal, QTimer,
    QAbstractListModel, QEvent, QUrl
)
from PySide6.QtGui import (
    QFont, QPixmap, QPainter, QColor, QBrush, QPen, QAction, QIcon,
    QFontMetrics, QPainterPath
)

from game_database import GameDatabase
from icon_factory import IconFactory


class GameListModel(QAbstractListModel):
    """Модель списка игр для Blitz"""

    def __init__(self, db: GameDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.games: List[Dict[str, Any]] = []
        self.filter_favorite = False
        self.search_query = ""
        self.sort_mode = "name"

    def load_games(self, filter_favorite: bool = False,
                   search_query: str = "",
                   sort_mode: str = "name"):
        self.beginResetModel()
        self.filter_favorite = filter_favorite
        self.search_query = search_query
        self.sort_mode = sort_mode
        self.games = self.db.get_games(
            limit=1000,
            offset=0,
            filter_favorite=filter_favorite,
            search_query=search_query if search_query else None,
            sort_mode=sort_mode
        )
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.games)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.games):
            return None
        game = self.games[index.row()]
        if role == Qt.DisplayRole:
            return game.get('name', '')
        elif role == Qt.UserRole:
            return game.get('cover_path', '')
        elif role == Qt.UserRole + 1:
            return game.get('id')
        elif role == Qt.UserRole + 2:
            return game.get('playtime', 0)
        elif role == Qt.UserRole + 3:
            return game.get('last_played', 0)
        elif role == Qt.UserRole + 4:
            return game.get('is_favorite', 0)
        return None

    def get_game_id(self, index: QModelIndex) -> Optional[int]:
        if index.isValid() and index.row() < len(self.games):
            return self.games[index.row()].get('id')
        return None


class GameCardDelegate(QStyledItemDelegate):
    """Делегат для отрисовки карточек игр в Blitz"""

    def __init__(self, db: GameDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.card_width = 200
        self.card_height = 300
        self.corner_radius = 12
        self.text_margin = 8

        self.title_font = QFont("Inter", 11, QFont.Weight.Bold)

        self.text_color = QColor(225, 225, 225)
        self.hover_border_color = QColor(52, 152, 219)
        self.favorite_color = QColor("#f2cc60")
        self.hover_star_color = QColor(200, 200, 200, 180)
        self.overlay_color = QColor(0, 0, 0, 80)
        self.placeholder_bg = QColor(30, 30, 35)

        self.cover_cache = {}

    def sizeHint(self, option, index):
        return QSize(self.card_width, self.card_height)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        name = index.data(Qt.DisplayRole) or ""
        cover_path = index.data(Qt.UserRole) or ""
        is_favorite = index.data(Qt.UserRole + 4) or 0
        is_hovered = bool(option.state & QStyle.State_MouseOver)

        rect = option.rect
        cover_rect = QRect(rect.x(), rect.y(), self.card_width, self.card_height)

        self._draw_cover(painter, cover_rect, cover_path)

        if is_hovered:
            painter.fillRect(cover_rect, QBrush(self.overlay_color))

        self._draw_favorite_icon(painter, cover_rect, is_favorite, is_hovered)

        title_rect = QRect(rect.x(), rect.y() + self.card_height - 32, rect.width(), 32)
        self._draw_game_title(painter, title_rect, name)

        if is_hovered:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(self.hover_border_color, 1.5))
            painter.drawRoundedRect(cover_rect, self.corner_radius, self.corner_radius)

        painter.restore()

    def _draw_cover(self, painter: QPainter, rect: QRect, cover_path: str):
        pixmap = None
        if cover_path and Path(cover_path).exists():
            if cover_path in self.cover_cache:
                pixmap = self.cover_cache[cover_path]
            else:
                original = QPixmap(cover_path)
                if not original.isNull():
                    scaled = original.scaled(rect.width(), rect.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    self.cover_cache[cover_path] = scaled
                    pixmap = scaled

        if pixmap and not pixmap.isNull():
            path = QPainterPath()
            path.addRoundedRect(rect, self.corner_radius, self.corner_radius)
            painter.setClipPath(path)
            painter.drawPixmap(rect, pixmap)
            painter.setClipping(False)
        else:
            painter.fillRect(rect, self.placeholder_bg)
            painter.setPen(QPen(QColor(100, 100, 110)))
            painter.setFont(QFont("Segoe UI Emoji", 48))
            painter.drawText(rect, Qt.AlignCenter, "🎮")

    def _draw_favorite_icon(self, painter: QPainter, rect: QRect, is_favorite: bool, is_hovered: bool):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        star_size = 28
        star_rect = QRect(rect.right() - star_size - 8, rect.top() + 8, star_size, star_size)

        should_draw = False
        star_color = None
        star_symbol = ""

        if is_favorite:
            should_draw = True
            star_color = self.favorite_color
            star_symbol = "★"
        elif is_hovered:
            should_draw = True
            star_color = self.hover_star_color
            star_symbol = "☆"

        if should_draw:
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(star_rect)
            pen_width = 2 if is_favorite else 1
            painter.setPen(QPen(star_color, pen_width))
            painter.setFont(QFont("Segoe UI Emoji", 14))
            painter.drawText(star_rect, Qt.AlignCenter, star_symbol)

        painter.restore()

    def _draw_game_title(self, painter: QPainter, rect: QRect, name: str):
        if not name:
            name = "Без названия"
        painter.fillRect(rect, QBrush(QColor(0, 0, 0, 150)))
        painter.setFont(self.title_font)
        font_metrics = QFontMetrics(self.title_font)
        available_width = rect.width() - self.text_margin * 2
        if font_metrics.horizontalAdvance(name) > available_width:
            name = font_metrics.elidedText(name, Qt.ElideRight, available_width)
        painter.setPen(self.text_color)
        painter.drawText(rect, Qt.AlignCenter, name)

    def clear_cache(self):
        self.cover_cache.clear()


class GameGridView(QWidget):
    """Виджет с сеткой игр для Blitz"""

    game_launch_requested = Signal(int, str)

    def __init__(self, db: GameDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.model = None
        self.delegate = None
        self.current_view = "all"
        self.sort_mode = "name"
        self.setup_ui()
        self.load_games()

    def render_fa_icon(self, icon_code: str, color: QColor, size: int = 16) -> QIcon:
        """Рендерит иконку Font Awesome в QIcon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setFont(IconFactory.get_font(size))
        painter.setPen(color)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, icon_code)
        painter.end()
        return QIcon(pixmap)

    def setup_ui(self):
        """Настройка интерфейса сетки игр"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 20, 20)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Контейнер для поиска и сортировки
        search_sort_container = QWidget()
        search_sort_container.setObjectName("search_sort_container")
        search_sort_layout = QHBoxLayout(search_sort_container)
        search_sort_layout.setContentsMargins(0, 0, 0, 0)
        search_sort_layout.setSpacing(15)

        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setObjectName("search_box")
        self.search_input.setPlaceholderText("Поиск игр...")
        self.search_input.setFixedWidth(350)
        self.search_input.setMinimumHeight(42)
        self.search_input.textChanged.connect(self.on_search_changed)

        # Иконка поиска (лупа Font Awesome)
        self.search_icon = QLabel(self.search_input)
        self.search_icon.setObjectName("search_icon")
        self.search_icon.setText("\uf002")
        self.search_icon.setFont(IconFactory.get_font(16))
        self.search_icon.setFixedSize(28, 28)
        self.search_icon.setAlignment(Qt.AlignCenter)

        # Кнопка очистки (крестик Font Awesome)
        self.clear_btn = QPushButton(self.search_input)
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.setText("\uf00d")
        self.clear_btn.setFont(IconFactory.get_font(14))
        self.clear_btn.setFixedSize(28, 28)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setVisible(False)
        self.clear_btn.clicked.connect(self.clear_search)

        # Комбобокс сортировки с иконкой Font Awesome
        self.sort_combo = QComboBox()
        self.sort_combo.setObjectName("sort_combo")

        # Создаем иконку сортировки \uf0dc
        sort_icon = self.render_fa_icon("\uf0dc", QColor(139, 148, 158), 16)

        # Добавляем пункты с иконкой
        self.sort_combo.addItem(sort_icon, "По алфавиту (A-Z)")
        self.sort_combo.addItem(sort_icon, "По времени игры")
        self.sort_combo.addItem(sort_icon, "По дате добавления")
        self.sort_combo.setCurrentIndex(0)
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)

        def position_icons():
            self.search_icon.move(10, (self.search_input.height() - self.search_icon.height()) // 2)
            self.clear_btn.move(
                self.search_input.width() - 35,
                (self.search_input.height() - self.clear_btn.height()) // 2
            )

        self.search_input.resizeEvent = lambda event: position_icons()
        position_icons()

        search_sort_layout.addWidget(self.search_input)
        search_sort_layout.addWidget(self.sort_combo)
        search_sort_layout.addStretch()
        layout.addWidget(search_sort_container, alignment=Qt.AlignLeft)

        self.games_count_label = QLabel("Всего игр: 0")
        self.games_count_label.setObjectName("games_count")
        layout.addWidget(self.games_count_label, alignment=Qt.AlignLeft)

        self.list_view = QListView()
        self.list_view.setViewMode(QListView.IconMode)
        self.list_view.setMovement(QListView.Static)
        self.list_view.setFlow(QListView.LeftToRight)
        self.list_view.setWrapping(True)
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setMouseTracking(True)
        self.list_view.setGridSize(QSize(210, 310))
        self.list_view.setIconSize(QSize(200, 300))
        self.list_view.setWordWrap(True)
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_view.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.show_context_menu)

        self.model = GameListModel(self.db, self)
        self.delegate = GameCardDelegate(self.db, self)

        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.clicked.connect(self.on_game_clicked)
        self.list_view.viewport().installEventFilter(self)

        layout.addWidget(self.list_view, 1)

    def on_sort_changed(self, index):
        """Обработчик изменения сортировки"""
        if index == 0:
            self.sort_mode = "name"
        elif index == 1:
            self.sort_mode = "playtime"
        elif index == 2:
            self.sort_mode = "date"
        self.refresh()

    def clear_search(self):
        """Очистить поле поиска"""
        self.search_input.clear()
        self.search_input.setFocus()

    def on_search_changed(self, text):
        """Обработчик изменения текста в поиске"""
        self.clear_btn.setVisible(bool(text))
        self.refresh()

    def load_games(self):
        self.current_view = "all"
        self.model.load_games(
            filter_favorite=False,
            search_query=self.search_input.text(),
            sort_mode=self.sort_mode
        )
        self.update_count_label()

    def load_favorites(self):
        self.current_view = "favorites"
        self.model.load_games(
            filter_favorite=True,
            search_query=self.search_input.text(),
            sort_mode=self.sort_mode
        )
        self.update_count_label()

    def load_recent(self):
        self.current_view = "recent"
        recent_games = self.db.get_recent_plays(limit=50, sort_mode=self.sort_mode)
        self.model.beginResetModel()
        self.model.games = recent_games
        self.model.endResetModel()
        self.update_count_label()

    def update_count_label(self):
        count = self.model.rowCount()
        if self.current_view == "favorites":
            self.games_count_label.setText(f"Избранное: {count}")
        elif self.current_view == "recent":
            self.games_count_label.setText(f"Недавние: {count}")
        else:
            self.games_count_label.setText(f"Всего игр: {count}")

    def on_game_clicked(self, index: QModelIndex):
        if not index.isValid():
            return
        game_id = self.model.get_game_id(index)
        game_name = index.data(Qt.DisplayRole)
        if game_id:
            self.game_launch_requested.emit(game_id, game_name)

    def eventFilter(self, watched, event):
        if watched == self.list_view.viewport() and event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                pos = event.pos()
                index = self.list_view.indexAt(pos)
                if index.isValid():
                    item_rect = self.list_view.visualRect(index)
                    star_size = 28
                    star_rect = QRect(
                        item_rect.right() - star_size - 8,
                        item_rect.top() + 8,
                        star_size,
                        star_size
                    )
                    if star_rect.contains(pos):
                        game_id = self.model.get_game_id(index)
                        if game_id:
                            self.toggle_favorite(game_id)
                            return True
        return super().eventFilter(watched, event)

    def show_context_menu(self, position):
        index = self.list_view.indexAt(position)
        if not index.isValid():
            return
        game_id = self.model.get_game_id(index)
        game_name = index.data(Qt.DisplayRole)
        is_favorite = index.data(Qt.UserRole + 4) or 0

        menu = QMenu()

        play_action = QAction("⚡ Запустить", self)
        play_action.triggered.connect(lambda: self.game_launch_requested.emit(game_id, game_name))
        menu.addAction(play_action)
        menu.addSeparator()

        favorite_text = "★ Убрать из избранного" if is_favorite else "☆ Добавить в избранное"
        favorite_action = QAction(favorite_text, self)
        favorite_action.triggered.connect(lambda: self.toggle_favorite(game_id))
        menu.addAction(favorite_action)
        menu.addSeparator()

        delete_action = QAction("🗑️ Удалить", self)
        delete_action.triggered.connect(lambda: self.delete_game(game_id, game_name))
        menu.addAction(delete_action)

        menu.exec(self.list_view.mapToGlobal(position))

    def toggle_favorite(self, game_id: int):
        self.db.toggle_favorite(game_id)
        self.refresh()

    def delete_game(self, game_id: int, game_name: str):
        reply = QMessageBox.question(self, "Удаление", f"Вы уверены, что хотите удалить игру «{game_name}»?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.delete_game(game_id)
            self.refresh()

    def refresh(self):
        """Обновить список игр"""
        if self.current_view == "favorites":
            self.model.load_games(
                filter_favorite=True,
                search_query=self.search_input.text(),
                sort_mode=self.sort_mode
            )
        elif self.current_view == "recent":
            if self.search_input.text():
                filtered = [g for g in self.model.games if self.search_input.text().lower() in g.get('name', '').lower()]
                self.model.beginResetModel()
                self.model.games = filtered
                self.model.endResetModel()
            else:
                self.load_recent()
        else:
            self.model.load_games(
                filter_favorite=False,
                search_query=self.search_input.text(),
                sort_mode=self.sort_mode
            )
        self.update_count_label()
        self.delegate.clear_cache()

    def clear_cover_cache(self):
        if self.delegate:
            self.delegate.clear_cache()
