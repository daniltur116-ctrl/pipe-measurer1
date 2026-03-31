[app]

# Название приложения (отображается под иконкой)
title = Трубомер

# Внутреннее имя пакета (только латиница)
package.name = pipemeasurer

# Домен для уникальности пакета
package.domain = org.yourcompany

# Версия приложения
version = 1.0.0

# Директория с исходным кодом (текущая папка)
source.dir = .

# Включаемые расширения файлов
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json

# Исключаемые директории
source.exclude_dirs = tests, bin, .git, __pycache__

# Иконка приложения (обязательно должна быть в репозитории!)
icon.filename = icon.png

# Зависимости (минимальный набор для теста)
requirements = python3,kivy

# Разрешения Android
android.permissions = INTERNET, RECORD_AUDIO

# Версии Android SDK/NDK
android.api = 30
android.minapi = 21
android.ndk = 23b

# Внешний вид
fullscreen = 0
orientation = portrait

# Kivy версия
kivy_version = 2.1.0

# Папки для сборки
build_dir = .buildozer
dist_dir = bin

[buildozer]
log_level = 2
