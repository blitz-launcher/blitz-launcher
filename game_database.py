import sqlite3
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from contextlib import contextmanager


class GameDatabase:
    """
    Класс для управления базой данных Blitz Game Launcher
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для работы с подключением"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """Создание всех таблиц при первом запуске"""
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._create_tables(conn)
            self._migrate_game_settings_schema(conn)
            self._init_default_data(conn)

    def _create_tables(self, conn):
        """Создание структуры таблиц"""

        conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                umu_id TEXT UNIQUE,
                name TEXT NOT NULL,
                sort_name TEXT,
                store TEXT CHECK(store IN ('steam', 'epic', 'gog', 'local', 'other')),
                store_id TEXT,
                install_path TEXT NOT NULL,
                executable TEXT,
                wine_prefix TEXT,
                proton_version TEXT,
                launch_options TEXT,
                environment TEXT,
                last_played INTEGER DEFAULT 0,
                playtime INTEGER DEFAULT 0,
                launch_count INTEGER DEFAULT 0,
                cover_path TEXT,
                cover_url TEXT,
                background_path TEXT,
                is_favorite INTEGER DEFAULT 0,
                install_status TEXT DEFAULT 'installed'
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                description TEXT,
                release_date TEXT,
                developer TEXT,
                publisher TEXT,
                genres TEXT,
                tags TEXT,
                steam_rating REAL,
                metacritic_score INTEGER,
                required_os TEXT,
                disk_space INTEGER,
                is_steam_deck_verified INTEGER DEFAULT 0,
                last_sync INTEGER,
                raw_data TEXT,
                UNIQUE(game_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS umu_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                umu_id TEXT NOT NULL,
                compatibility_tool TEXT,
                tool_version TEXT,
                notes TEXT,
                is_custom INTEGER DEFAULT 0,
                UNIQUE(game_id, umu_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS launch_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                profile_name TEXT NOT NULL,
                proton_version TEXT,
                wine_prefix TEXT,
                launch_options TEXT,
                environment TEXT,
                is_default INTEGER DEFAULT 0,
                UNIQUE(game_id, profile_name)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS launch_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                profile_id INTEGER REFERENCES launch_profiles(id) ON DELETE SET NULL,
                launch_time INTEGER NOT NULL,
                exit_code INTEGER,
                session_duration INTEGER,
                log_path TEXT,
                error_message TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS saves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                save_name TEXT NOT NULL,
                save_path TEXT NOT NULL,
                backup_path TEXT,
                created_at INTEGER,
                last_played INTEGER,
                file_size INTEGER,
                is_cloud_synced INTEGER DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS proton_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_name TEXT UNIQUE NOT NULL,
                version_type TEXT,
                install_path TEXT,
                is_installed INTEGER DEFAULT 1,
                last_used INTEGER,
                compatibility_notes TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                icon_path TEXT,
                sort_order INTEGER DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS collection_games (
                collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                sort_order INTEGER DEFAULT 0,
                PRIMARY KEY (collection_id, game_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_tags (
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (game_id, tag_id)
            )
        """)

        # Таблица настроек игр
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_settings (
                game_id INTEGER PRIMARY KEY REFERENCES games(id) ON DELETE CASCADE,
                mangohud INTEGER DEFAULT 1,
                gamemode INTEGER DEFAULT 1,
                esync INTEGER DEFAULT 1,
                fsync INTEGER DEFAULT 1,
                esunc INTEGER DEFAULT 1,
                fsunc INTEGER DEFAULT 1,
                ntsync INTEGER DEFAULT 0,
                dxvk INTEGER DEFAULT 1,
                vkbasalt INTEGER DEFAULT 0,
                fsr INTEGER DEFAULT 0,
                dlss INTEGER DEFAULT 0,
                proton_version TEXT DEFAULT 'System Default',
                dxvk_version TEXT DEFAULT '2.5.3 (стабильная)',
                fsr_level TEXT DEFAULT 'Качество',
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)

        self._create_indexes(conn)

    def _migrate_game_settings_schema(self, conn):
        """Миграция game_settings: добавление недостающих колонок."""
        existing = {
            row[1] for row in conn.execute("PRAGMA table_info(game_settings)").fetchall()
        }
        alter_statements = [
            ("esunc", "ALTER TABLE game_settings ADD COLUMN esunc INTEGER DEFAULT 1"),
            ("fsunc", "ALTER TABLE game_settings ADD COLUMN fsunc INTEGER DEFAULT 1"),
            ("ntsync", "ALTER TABLE game_settings ADD COLUMN ntsync INTEGER DEFAULT 0"),
            ("proton_version", "ALTER TABLE game_settings ADD COLUMN proton_version TEXT DEFAULT 'System Default'"),
            ("mangohud_extended", "ALTER TABLE game_settings ADD COLUMN mangohud_extended INTEGER DEFAULT 0"),
        ]
        for column_name, statement in alter_statements:
            if column_name not in existing:
                conn.execute(statement)

    def _create_indexes(self, conn):
        """Создание индексов"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_games_name ON games(name)",
            "CREATE INDEX IF NOT EXISTS idx_games_store ON games(store)",
            "CREATE INDEX IF NOT EXISTS idx_games_last_played ON games(last_played)",
            "CREATE INDEX IF NOT EXISTS idx_games_favorite ON games(is_favorite)",
            "CREATE INDEX IF NOT EXISTS idx_metadata_game ON game_metadata(game_id)",
            "CREATE INDEX IF NOT EXISTS idx_umu_game ON umu_mappings(game_id)",
            "CREATE INDEX IF NOT EXISTS idx_profiles_game ON launch_profiles(game_id)",
            "CREATE INDEX IF NOT EXISTS idx_history_game ON launch_history(game_id)",
            "CREATE INDEX IF NOT EXISTS idx_history_time ON launch_history(launch_time)",
            "CREATE INDEX IF NOT EXISTS idx_saves_game ON saves(game_id)",
            "CREATE INDEX IF NOT EXISTS idx_proton_name ON proton_versions(version_name)",
            "CREATE INDEX IF NOT EXISTS idx_game_tags_game ON game_tags(game_id)",
            "CREATE INDEX IF NOT EXISTS idx_game_settings ON game_settings(game_id)",
        ]
        for index in indexes:
            try:
                conn.execute(index)
            except sqlite3.Error:
                pass

    def _init_default_data(self, conn):
        """Заполнение начальными данными"""
        default_settings = {
            'theme': 'dark',
            'library_folder': '',
            'default_proton': 'GE-Proton9-26',
            'default_wine_prefix': '',
            'language': 'ru',
            'window_width': '1200',
            'window_height': '800',
            'enable_gamescope': '0',
            'enable_mangohud': '1',
            'auto_download_covers': '1',
            'show_hidden_games': '0',
            'umu_runtime_enabled': '1'
        }
        for key, value in default_settings.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

        default_tags = [
            ('Избранное', '#FFD700'),
            ('Пройдено', '#4CAF50'),
            ('Отложено', '#FF9800'),
            ('Не играл', '#9E9E9E'),
        ]
        for name, color in default_tags:
            conn.execute("INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)", (name, color))

    @staticmethod
    def _get_sort_name(name: str) -> str:
        """Генерация сортировочного имени с учётом артиклей"""
        sort_name = name
        articles = [
            'the ', 'a ', 'an ', 'the_', 'a_', 'an_',
            'The ', 'A ', 'An ', 'The_', 'A_', 'An_',
            'это ', 'эта ', 'этот ', 'та ', 'тот ',
            'Это ', 'Эта ', 'Этот ', 'Та ', 'Тот ',
            'игра ', 'Игра ',
        ]
        for article in articles:
            if sort_name.lower().startswith(article.lower()):
                sort_name = sort_name[len(article):]
                break
        return sort_name.strip()

    @staticmethod
    def _safe_json_loads(value: Any) -> Any:
        """Безопасная загрузка JSON"""
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    @staticmethod
    def _safe_json_dumps(value: Any) -> str:
        """Безопасное преобразование в JSON"""
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, str):
            try:
                json.loads(value)
                return value
            except (json.JSONDecodeError, TypeError):
                return json.dumps([value]) if value else None
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def clean_proton_version(proton_version: str) -> Optional[str]:
        """Очистить версию Proton от эмодзи"""
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

    # ============================================================
    # ОСНОВНЫЕ ОПЕРАЦИИ С ИГРАМИ
    # ============================================================

    def add_game(self, name: str, install_path: str, store: str = 'local',
                 store_id: str = None, executable: str = None,
                 umu_id: str = None, **kwargs) -> int:
        with self.get_connection() as conn:
            sort_name = self._get_sort_name(name)
            proton_version = kwargs.get('proton_version')
            if proton_version:
                proton_version = self.clean_proton_version(proton_version)
            if not proton_version:
                proton_version = self.get_setting('default_proton')

            cursor = conn.execute("""
                INSERT INTO games (
                    name, sort_name, install_path, executable, store, store_id, umu_id,
                    wine_prefix, proton_version, launch_options, environment,
                    cover_path, cover_url, background_path,
                    is_favorite, install_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, sort_name, install_path, executable, store, store_id, umu_id,
                kwargs.get('wine_prefix'),
                proton_version,
                kwargs.get('launch_options'),
                kwargs.get('environment'),
                kwargs.get('cover_path'),
                kwargs.get('cover_url'),
                kwargs.get('background_path'),
                kwargs.get('is_favorite', 0),
                'installed'
            ))
            game_id = cursor.lastrowid
            if umu_id:
                conn.execute("INSERT INTO umu_mappings (game_id, umu_id, is_custom) VALUES (?, ?, 1)", (game_id, umu_id))
            return game_id

    def get_game(self, game_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            result = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
            return dict(result) if result else None

    def get_games(self, limit: int = 50, offset: int = 0,
                  filter_favorite: bool = False,
                  search_query: str = None,
                  store_filter: str = None,
                  sort_mode: str = "name") -> List[Dict[str, Any]]:
        """
        Получить список игр с поддержкой сортировки
        """
        with self.get_connection() as conn:
            query = """
                SELECT g.*, GROUP_CONCAT(DISTINCT t.name) as tags,
                       GROUP_CONCAT(DISTINCT t.color) as tag_colors,
                       gm.description, gm.developer, gm.steam_rating, gm.is_steam_deck_verified
                FROM games g
                LEFT JOIN game_metadata gm ON g.id = gm.game_id
                LEFT JOIN game_tags gt ON g.id = gt.game_id
                LEFT JOIN tags t ON gt.tag_id = t.id
                WHERE 1=1
            """
            params = []

            if filter_favorite:
                query += " AND g.is_favorite = 1"

            if search_query:
                escaped_query = search_query.replace('%', '\\%').replace('_', '\\_')
                query += " AND g.name LIKE ? ESCAPE '\\'"
                params.append(f"%{escaped_query}%")

            if store_filter:
                query += " AND g.store = ?"
                params.append(store_filter)

            query += " GROUP BY g.id"

            if sort_mode == "name":
                query += " ORDER BY g.sort_name COLLATE NOCASE ASC, g.name COLLATE NOCASE ASC"
            elif sort_mode == "playtime":
                query += " ORDER BY g.playtime DESC, g.name COLLATE NOCASE ASC"
            elif sort_mode == "date":
                query += " ORDER BY g.id DESC, g.name COLLATE NOCASE ASC"
            else:
                query += " ORDER BY g.sort_name COLLATE NOCASE ASC, g.name COLLATE NOCASE ASC"

            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            results = conn.execute(query, params).fetchall()
            return [dict(row) for row in results]

    def get_games_count(self, filter_favorite: bool = False,
                        search_query: str = None,
                        store_filter: str = None) -> int:
        """Получить количество игр с учетом фильтров"""
        with self.get_connection() as conn:
            query = "SELECT COUNT(*) FROM games WHERE 1=1"
            params = []

            if filter_favorite:
                query += " AND is_favorite = 1"

            if search_query:
                escaped_query = search_query.replace('%', '\\%').replace('_', '\\_')
                query += " AND name LIKE ? ESCAPE '\\'"
                params.append(f"%{escaped_query}%")

            if store_filter:
                query += " AND store = ?"
                params.append(store_filter)

            result = conn.execute(query, params).fetchone()
            return result[0] if result else 0

    def get_favorite_games(self) -> List[Dict[str, Any]]:
        return self.get_games(filter_favorite=True, limit=1000, offset=0)

    def toggle_favorite(self, game_id: int) -> bool:
        with self.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                result = conn.execute("SELECT is_favorite FROM games WHERE id = ?", (game_id,)).fetchone()
                if result:
                    new_status = 0 if result[0] == 1 else 1
                    conn.execute("UPDATE games SET is_favorite = ? WHERE id = ?", (new_status, game_id))
                    conn.commit()
                    return True
                conn.commit()
                return False
            except:
                conn.rollback()
                raise

    def update_game(self, game_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        with self.get_connection() as conn:
            fields = []
            values = []
            allowed_fields = [
                'name', 'sort_name', 'store', 'store_id', 'install_path',
                'executable', 'wine_prefix', 'proton_version', 'launch_options',
                'environment', 'cover_path', 'cover_url', 'background_path',
                'is_favorite', 'install_status', 'umu_id', 'playtime', 'last_played'
            ]
            for field, value in kwargs.items():
                if field in allowed_fields:
                    if field == 'proton_version' and value:
                        value = self.clean_proton_version(value)
                    fields.append(f"{field} = ?")
                    values.append(value)
            if not fields:
                return False
            values.append(game_id)
            conn.execute(f"UPDATE games SET {', '.join(fields)} WHERE id = ?", values)
            return True

    def delete_game(self, game_id: int) -> bool:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
            return True

    def get_game_count(self, filter_favorite: bool = False, search_query: str = None) -> int:
        with self.get_connection() as conn:
            query = "SELECT COUNT(*) FROM games WHERE 1=1"
            params = []
            if filter_favorite:
                query += " AND is_favorite = 1"
            if search_query:
                escaped_query = search_query.replace('%', '\\%').replace('_', '\\_')
                query += " AND name LIKE ? ESCAPE '\\'"
                params.append(f"%{escaped_query}%")
            result = conn.execute(query, params).fetchone()
            return result[0] if result else 0

    # ============================================================
    # МЕТАДАННЫЕ ИГР
    # ============================================================

    def update_metadata(self, game_id: int, metadata: Dict[str, Any]) -> bool:
        with self.get_connection() as conn:
            processed = {}
            for key, value in metadata.items():
                if key in ['genres', 'tags', 'raw_data']:
                    processed[key] = self._safe_json_dumps(value)
                else:
                    processed[key] = value
            processed['last_sync'] = int(datetime.now().timestamp())
            fields = []
            values = []
            allowed_fields = [
                'description', 'release_date', 'developer', 'publisher',
                'genres', 'tags', 'steam_rating', 'metacritic_score',
                'required_os', 'disk_space', 'is_steam_deck_verified',
                'last_sync', 'raw_data'
            ]
            for field, value in processed.items():
                if field in allowed_fields and value is not None:
                    fields.append(f"{field} = ?")
                    values.append(value)
            if not fields:
                return False
            values.append(game_id)
            conn.execute(f"INSERT OR REPLACE INTO game_metadata (game_id, {', '.join(fields)}) VALUES (?, {', '.join(['?'] * len(fields))})", (game_id, *values))
            return True

    def get_metadata(self, game_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            result = conn.execute("SELECT * FROM game_metadata WHERE game_id = ?", (game_id,)).fetchone()
            if not result:
                return None
            data = dict(result)
            for field in ['genres', 'tags', 'raw_data']:
                if data.get(field):
                    data[field] = self._safe_json_loads(data[field])
            return data

    # ============================================================
    # ПРОФИЛИ ЗАПУСКА
    # ============================================================

    def add_launch_profile(self, game_id: int, profile_name: str,
                          proton_version: str = None, wine_prefix: str = None,
                          launch_options: str = None, environment: str = None,
                          is_default: bool = False) -> int:
        with self.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                if is_default:
                    conn.execute("UPDATE launch_profiles SET is_default = 0 WHERE game_id = ?", (game_id,))
                if proton_version:
                    proton_version = self.clean_proton_version(proton_version)
                cursor = conn.execute("""
                    INSERT INTO launch_profiles (game_id, profile_name, proton_version, wine_prefix,
                                                 launch_options, environment, is_default)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (game_id, profile_name, proton_version, wine_prefix, launch_options, environment, 1 if is_default else 0))
                conn.commit()
                return cursor.lastrowid
            except:
                conn.rollback()
                raise

    def get_launch_profiles(self, game_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            results = conn.execute("SELECT * FROM launch_profiles WHERE game_id = ? ORDER BY is_default DESC, profile_name", (game_id,)).fetchall()
            return [dict(row) for row in results]

    def get_default_profile(self, game_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            result = conn.execute("SELECT * FROM launch_profiles WHERE game_id = ? AND is_default = 1", (game_id,)).fetchone()
            return dict(result) if result else None

    def get_launch_config(self, game_id: int, profile_id: int = None) -> Dict[str, Any]:
        game = self.get_game(game_id)
        if not game:
            return {}

        profile = None
        if profile_id:
            with self.get_connection() as conn:
                result = conn.execute("SELECT * FROM launch_profiles WHERE id = ?", (profile_id,)).fetchone()
                if result:
                    profile = dict(result)

        if not profile:
            profile = self.get_default_profile(game_id)

        env = {}
        umu_id = game.get('umu_id', f"umu-{game_id}")
        env["GAMEID"] = umu_id

        wine_prefix = None
        if profile and profile.get('wine_prefix'):
            wine_prefix = profile['wine_prefix']
        elif game.get('wine_prefix'):
            wine_prefix = game['wine_prefix']
        if wine_prefix:
            env["WINEPREFIX"] = wine_prefix

        proton_version = None
        if profile and profile.get('proton_version'):
            proton_version = profile['proton_version']
        elif game.get('proton_version'):
            proton_version = game['proton_version']
        if proton_version:
            proton_version = self.clean_proton_version(proton_version)

        if profile and profile.get('environment'):
            try:
                custom_env = json.loads(profile['environment'])
                env.update(custom_env)
            except:
                pass

        install_path = Path(game['install_path'])
        if game.get('executable'):
            executable_path = install_path / game['executable']
        else:
            exe_files = list(install_path.glob("*.exe"))
            if exe_files:
                executable_path = exe_files[0]
            else:
                executable_path = install_path

        launch_options = ""
        if profile and profile.get('launch_options'):
            launch_options = profile['launch_options']
        elif game.get('launch_options'):
            launch_options = game['launch_options']

        return {
            'game': game,
            'profile': profile,
            'env': env,
            'executable': str(executable_path),
            'launch_options': launch_options,
            'umu_id': umu_id,
            'proton_version': proton_version
        }

    # ============================================================
    # ИСТОРИЯ ЗАПУСКОВ
    # ============================================================

    def add_launch_record(self, game_id: int, session_duration: int = None,
                         exit_code: int = None, log_path: str = None,
                         error_message: str = None, profile_id: int = None) -> int:
        """Добавление записи о запуске"""
        with self.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("""
                    UPDATE games
                    SET launch_count = launch_count + 1,
                        last_played = strftime('%s', 'now')
                    WHERE id = ?
                """, (game_id,))

                cursor = conn.execute("""
                    INSERT INTO launch_history (
                        game_id, profile_id, launch_time, session_duration, exit_code, log_path, error_message
                    ) VALUES (?, ?, strftime('%s', 'now'), ?, ?, ?, ?)
                """, (game_id, profile_id, session_duration, exit_code, log_path, error_message))

                if profile_id:
                    conn.execute("""
                        UPDATE launch_profiles
                        SET last_used = strftime('%s', 'now')
                        WHERE id = ?
                    """, (profile_id,))

                conn.commit()
                return cursor.lastrowid
            except:
                conn.rollback()
                raise

    def update_game_session(self, history_id: int, session_duration: int, exit_code: int = 0) -> bool:
        """Обновление информации о сессии игры"""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    UPDATE launch_history
                    SET session_duration = ?, exit_code = ?
                    WHERE id = ?
                """, (session_duration, exit_code, history_id))

                result = conn.execute("SELECT game_id FROM launch_history WHERE id = ?", (history_id,)).fetchone()
                if result:
                    game_id = result[0]
                    conn.execute("""
                        UPDATE games
                        SET playtime = playtime + ?
                        WHERE id = ?
                    """, (session_duration, game_id))

                conn.commit()
                return True
            except:
                conn.rollback()
                return False

    def get_recent_plays(self, limit: int = 20, days: int = 30, sort_mode: str = "date") -> List[Dict[str, Any]]:
        """Получение последних запущенных игр с фильтром по дням и сортировкой"""
        with self.get_connection() as conn:
            query = """
                SELECT DISTINCT
                    g.id, g.name, g.cover_path, g.install_path, g.executable,
                    g.playtime, g.proton_version, g.sort_name,
                    MAX(lh.launch_time) as launch_time,
                    lh.session_duration, lh.exit_code,
                    COUNT(lh.id) as launch_count
                FROM launch_history lh
                JOIN games g ON lh.game_id = g.id
                WHERE lh.launch_time > strftime('%s', 'now', ?)
                GROUP BY g.id
            """
            params = [f'-{days} days']

            if sort_mode == "name":
                query += " ORDER BY g.sort_name COLLATE NOCASE ASC"
            elif sort_mode == "playtime":
                query += " ORDER BY g.playtime DESC"
            elif sort_mode == "date":
                query += " ORDER BY launch_time DESC"
            else:
                query += " ORDER BY launch_time DESC"

            query += " LIMIT ?"
            params.append(limit)

            results = conn.execute(query, params).fetchall()
            return [dict(row) for row in results]

    def get_recent_plays_with_details(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение последних запущенных игр с детальной информацией"""
        with self.get_connection() as conn:
            results = conn.execute("""
                SELECT
                    g.id, g.name, g.cover_path,
                    lh.launch_time, lh.session_duration, lh.exit_code,
                    datetime(lh.launch_time, 'unixepoch', 'localtime') as launch_date,
                    CASE
                        WHEN lh.session_duration < 60 THEN CAST(lh.session_duration AS TEXT) || ' сек'
                        WHEN lh.session_duration < 3600 THEN CAST(lh.session_duration / 60 AS TEXT) || ' мин'
                        ELSE CAST(lh.session_duration / 3600 AS TEXT) || ' ч ' || CAST((lh.session_duration % 3600) / 60 AS TEXT) || ' мин'
                    END as duration_formatted
                FROM launch_history lh
                JOIN games g ON lh.game_id = g.id
                ORDER BY lh.launch_time DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [dict(row) for row in results]

    def get_weekly_stats(self) -> Dict[str, Any]:
        """Получение статистики за неделю"""
        with self.get_connection() as conn:
            stats = {}

            result = conn.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(session_duration), 0) as total_time
                FROM launch_history
                WHERE launch_time > strftime('%s', 'now', '-7 days')
            """).fetchone()
            stats['weekly_launches'] = result[0] if result else 0
            stats['weekly_playtime'] = result[1] if result else 0

            result = conn.execute("""
                SELECT g.name, COUNT(lh.id) as launch_count, COALESCE(SUM(lh.session_duration), 0) as total_time
                FROM launch_history lh
                JOIN games g ON lh.game_id = g.id
                WHERE lh.launch_time > strftime('%s', 'now', '-7 days')
                GROUP BY g.id
                ORDER BY total_time DESC
                LIMIT 1
            """).fetchone()
            if result:
                stats['most_played_weekly'] = dict(result)

            return stats

    # ============================================================
    # ТЕГИ
    # ============================================================

    def add_tag(self, name: str, color: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute("INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)", (name, color))
            return cursor.lastrowid

    def get_tags(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            results = conn.execute("SELECT * FROM tags ORDER BY name").fetchall()
            return [dict(row) for row in results]

    def add_game_tag(self, game_id: int, tag_id: int) -> bool:
        with self.get_connection() as conn:
            try:
                conn.execute("INSERT INTO game_tags (game_id, tag_id) VALUES (?, ?)", (game_id, tag_id))
                return True
            except sqlite3.IntegrityError:
                return False

    def remove_game_tag(self, game_id: int, tag_id: int) -> bool:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM game_tags WHERE game_id = ? AND tag_id = ?", (game_id, tag_id))
            return True

    def get_game_tags(self, game_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            results = conn.execute("SELECT t.* FROM tags t JOIN game_tags gt ON t.id = gt.tag_id WHERE gt.game_id = ? ORDER BY t.name", (game_id,)).fetchall()
            return [dict(row) for row in results]

    # ============================================================
    # КОЛЛЕКЦИИ
    # ============================================================

    def add_collection(self, name: str, description: str = None, icon_path: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute("INSERT INTO collections (name, description, icon_path) VALUES (?, ?, ?)", (name, description, icon_path))
            return cursor.lastrowid

    def get_collections(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            results = conn.execute("""
                SELECT c.*, COUNT(cg.game_id) as game_count
                FROM collections c
                LEFT JOIN collection_games cg ON c.id = cg.collection_id
                GROUP BY c.id ORDER BY c.sort_order, c.name
            """).fetchall()
            return [dict(row) for row in results]

    def add_game_to_collection(self, game_id: int, collection_id: int) -> bool:
        with self.get_connection() as conn:
            try:
                conn.execute("INSERT INTO collection_games (collection_id, game_id) VALUES (?, ?)", (collection_id, game_id))
                return True
            except sqlite3.IntegrityError:
                return False

    def remove_game_from_collection(self, game_id: int, collection_id: int) -> bool:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM collection_games WHERE collection_id = ? AND game_id = ?", (collection_id, game_id))
            return True

    # ============================================================
    # ВЕРСИИ PROTON
    # ============================================================

    def scan_proton_versions(self) -> List[Dict[str, Any]]:
        versions = []
        home = Path.home()
        search_paths = [
            home / ".steam" / "root" / "steamapps" / "common",
            home / ".steam" / "root" / "compatibilitytools.d",
            home / ".local" / "share" / "Steam" / "steamapps" / "common",
            home / ".local" / "share" / "Steam" / "compatibilitytools.d",
        ]

        def is_valid_proton(path: Path) -> bool:
            proton_exec = path / "proton"
            if not proton_exec.exists():
                proton_exec = path / "proton" / "proton"
            return proton_exec.exists() and proton_exec.is_file()

        for search_path in search_paths:
            if not search_path.exists():
                continue
            for item in search_path.iterdir():
                if item.is_dir() and ("Proton" in item.name or "proton" in item.name):
                    if is_valid_proton(item):
                        version_type = "ge" if "GE" in item.name or "GE-Proton" in item.name else "official"
                        versions.append({
                            "version_name": item.name,
                            "version_type": version_type,
                            "install_path": str(item),
                            "is_installed": 1
                        })

        with self.get_connection() as conn:
            for v in versions:
                conn.execute("INSERT OR REPLACE INTO proton_versions (version_name, version_type, install_path, is_installed, last_used) VALUES (?, ?, ?, ?, ?)",
                           (v['version_name'], v['version_type'], v['install_path'], v['is_installed'], None))
        return versions

    def get_proton_versions(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            results = conn.execute("SELECT * FROM proton_versions WHERE is_installed = 1 ORDER BY version_type, version_name").fetchall()
            return [dict(row) for row in results]

    # ============================================================
    # НАСТРОЙКИ
    # ============================================================

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.get_connection() as conn:
            result = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            if not result:
                return default
            value = result[0]
            if isinstance(value, str) and value and value[0] in ('{', '[', '"'):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
            return value

    def set_setting(self, key: str, value: Any) -> None:
        if isinstance(value, (dict, list, bool, int, float)):
            value = json.dumps(value, ensure_ascii=False)
        with self.get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, strftime('%s', 'now'))", (key, str(value)))

    # ============================================================
    # НАСТРОЙКИ ИГР
    # ============================================================

    def get_game_settings(self, game_id: int) -> Dict[str, Any]:
        """Получить настройки игры из БД"""
        if not game_id:
            return {
                'game_id': None,
                'mangohud': 0,
                'gamemode': 0,
                'esync': 0,
                'fsync': 0,
                'esunc': 0,
                'fsunc': 0,
                'ntsync': 0,
                'dxvk': 0,
                'vkbasalt': 0,
                'fsr': 0,
                'dlss': 0,
                'proton_version': 'System Default',
                'dxvk_version': '2.5.3 (стабильная)',
                'fsr_level': 'Качество',
                'mangohud_extended': 0,
            }
        with self.get_connection() as conn:
            result = conn.execute("SELECT * FROM game_settings WHERE game_id = ?", (game_id,)).fetchone()

            if result:
                return dict(result)
            else:
                default_settings = {
                    'game_id': game_id,
                    'mangohud': 0,
                    'gamemode': 0,
                    'esync': 0,
                    'fsync': 0,
                    'esunc': 0,
                    'fsunc': 0,
                    'ntsync': 0,
                    'dxvk': 0,
                    'vkbasalt': 0,
                    'fsr': 0,
                    'dlss': 0,
                    'proton_version': 'System Default',
                    'dxvk_version': '2.5.3 (стабильная)',
                    'fsr_level': 'Качество',
                    'mangohud_extended': 0,
                }
                conn.execute("""
                    INSERT INTO game_settings (
                        game_id, mangohud, gamemode, esync, fsync, esunc, fsunc, ntsync, dxvk,
                        vkbasalt, fsr, dlss, proton_version, dxvk_version, fsr_level, mangohud_extended
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    game_id,
                    default_settings['mangohud'],
                    default_settings['gamemode'],
                    default_settings['esync'],
                    default_settings['fsync'],
                    default_settings['esunc'],
                    default_settings['fsunc'],
                    default_settings['ntsync'],
                    default_settings['dxvk'],
                    default_settings['vkbasalt'],
                    default_settings['fsr'],
                    default_settings['dlss'],
                    default_settings['proton_version'],
                    default_settings['dxvk_version'],
                    default_settings['fsr_level'],
                    default_settings['mangohud_extended'],
                ))
                return default_settings

    def save_game_settings(self, game_id: int, settings: Dict[str, Any]) -> bool:
        """Сохранить настройки игры в БД"""
        if not game_id:
            return False
        with self.get_connection() as conn:
            try:
                esync_value = settings.get('esync', settings.get('esunc', False))
                fsync_value = settings.get('fsync', settings.get('fsunc', False))
                ntsync_value = settings.get('ntsync', settings.get('ntsunc', False))
                conn.execute("""
                    INSERT OR REPLACE INTO game_settings (
                        game_id, mangohud, gamemode, esync, fsync, esunc, fsunc, ntsync, dxvk,
                        vkbasalt, fsr, dlss, proton_version, dxvk_version, fsr_level,
                        mangohud_extended, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                """, (
                    game_id,
                    1 if settings.get('mangohud', False) else 0,
                    1 if settings.get('gamemode', False) else 0,
                    1 if esync_value else 0,
                    1 if fsync_value else 0,
                    1 if esync_value else 0,
                    1 if fsync_value else 0,
                    1 if ntsync_value else 0,
                    1 if settings.get('dxvk', False) else 0,
                    1 if settings.get('vkbasalt', False) else 0,
                    1 if settings.get('fsr', False) else 0,
                    1 if settings.get('dlss', False) else 0,
                    settings.get('proton_version', 'System Default'),
                    settings.get('dxvk_version', '2.5.3 (стабильная)'),
                    settings.get('fsr_level', 'Качество'),
                    1 if settings.get('mangohud_extended', False) else 0,
                ))
                return True
            except Exception as e:
                print(f"❌ Ошибка сохранения настроек игры {game_id}: {e}")
                return False

    def update_game_setting(self, game_id: int, setting_name: str, value) -> bool:
        """Обновить одну настройку игры"""
        with self.get_connection() as conn:
            try:
                if isinstance(value, bool):
                    value = 1 if value else 0

                conn.execute(f"""
                    UPDATE game_settings
                    SET {setting_name} = ?, updated_at = strftime('%s', 'now')
                    WHERE game_id = ?
                """, (value, game_id))
                return True
            except Exception as e:
                print(f"❌ Ошибка обновления настройки {setting_name} для игры {game_id}: {e}")
                return False

    def get_launch_settings(self, game_id: int) -> Dict[str, Any]:
        """Получить настройки для запуска игры"""
        settings = self.get_game_settings(game_id)

        return {
            'mangohud': bool(settings.get('mangohud', 0)),
            'mangohud_extended': bool(settings.get('mangohud_extended', 0)),
            'gamemode': bool(settings.get('gamemode', 0)),
            'esync': bool(settings.get('esync', 0)),
            'fsync': bool(settings.get('fsync', 0)),
            'esunc': bool(settings.get('esunc', settings.get('esync', 0))),
            'fsunc': bool(settings.get('fsunc', settings.get('fsync', 0))),
            'ntsync': bool(settings.get('ntsync', 0)),
            'dxvk': bool(settings.get('dxvk', 0)),
            'vkbasalt': bool(settings.get('vkbasalt', 0)),
            'fsr': bool(settings.get('fsr', 0)),
            'dlss': bool(settings.get('dlss', 0)),
            'proton_version': settings.get('proton_version', 'System Default'),
            'dxvk_version': settings.get('dxvk_version', '2.5.3 (стабильная)'),
            'fsr_level': settings.get('fsr_level', 'Качество')
        }

    # ============================================================
    # СТАТИСТИКА
    # ============================================================

    def get_statistics(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            stats = {}
            result = conn.execute("SELECT COUNT(*) FROM games").fetchone()
            stats['total_games'] = result[0] if result else 0
            result = conn.execute("SELECT SUM(playtime) FROM games").fetchone()
            stats['total_playtime'] = result[0] if result else 0
            result = conn.execute("SELECT COUNT(*) FROM launch_history").fetchone()
            stats['total_launches'] = result[0] if result else 0
            result = conn.execute("SELECT name, playtime FROM games ORDER BY playtime DESC LIMIT 1").fetchone()
            if result:
                stats['most_played_game'] = dict(result)
            stats['db_size'] = self.db_path.stat().st_size if self.db_path.exists() else 0
            return stats

    def vacuum(self):
        with self.get_connection() as conn:
            conn.execute("VACUUM")

    def backup(self, backup_path: Path) -> bool:
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            return True
        except Exception as e:
            print(f"Backup failed: {e}")
            return False
