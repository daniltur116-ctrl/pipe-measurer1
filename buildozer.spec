[app]

# Название приложения
title = Трубомер

# Внутреннее имя пакета
package.name = pipemeasurer

# Домен
package.domain = org.yourcompany

# Версия
version = 1.0.0

# Директория с исходным кодом
source.dir = .

# Включаемые расширения
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json

# Исключаемые директории
source.exclude_dirs = tests, bin, .git, __pycache__

# Иконка
icon.filename = icon.png

# Зависимости
requirements = python3,kivy

# Разрешения
android.permissions = INTERNET, RECORD_AUDIO

# Версии Android (исправлено)
android.api = 30
android.minapi = 21
android.ndk = 23b
android.sdk = 30

# Не использовать build-tools 37 (старая версия)
android.accept_sdk_license = True

# Внешний вид
fullscreen = 0
orientation = portrait

# Kivy
kivy_version = 2.1.0

# Папки сборки
build_dir = .buildozer
dist_dir = bin

[buildozer]
log_level = 2
