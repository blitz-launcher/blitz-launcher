from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase


class IconFactory:
    """Фабрика для создания иконок Font Awesome"""

    _fa_font_family = None

    @classmethod
    def load_font(cls):
        """Загрузка шрифта Font Awesome"""
        if cls._fa_font_family:
            return

        app_dir = Path(__file__).parent
        fonts_dir = app_dir / "assets" / "fonts"
        fa_font_path = fonts_dir / "fontawesome.otf"

        if fa_font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(fa_font_path))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                cls._fa_font_family = families[0] if families else "Font Awesome 7 Free"
            else:
                cls._fa_font_family = "Font Awesome 7 Free"
        else:
            cls._fa_font_family = "Font Awesome 7 Free"

    @classmethod
    def get_font(cls, size: int = 14) -> QFont:
        """Получить шрифт Font Awesome"""
        cls.load_font()
        font = QFont(cls._fa_font_family)
        font.setPixelSize(size)
        return font
