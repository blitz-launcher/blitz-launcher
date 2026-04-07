#!/bin/bash

# Получаем абсолютный путь к папке, где лежит этот скрипт
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Путь к файлу ярлыка в системе пользователя
DESKTOP_FILE="$HOME/.local/share/applications/blitz-launcher.desktop"

echo "Начинаю установку ярлыка для Blitz Launcher..."

# Создаем содержание .desktop файла
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=Blitz Launcher
Comment=Управление Proton и запуск игр (Alpha)
Exec=python3 $DIR/main.py
Path=$DIR
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Game;Utility;
StartupNotify=true
EOF

# Даем права на выполнение ярлыку
chmod +x "$DESKTOP_FILE"

echo "Готово! Blitz Launcher теперь доступен в меню приложений."
echo "Путь к проекту: $DIR"
