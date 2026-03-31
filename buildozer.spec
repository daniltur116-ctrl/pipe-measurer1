[app]

# Основные настройки
title = Трубомер
package.name = pipemeasurer
package.domain = org.yourcompany

# Версия приложения
version = 1.0.0
version.regex = __version__ = ['"](.*)['"]

# Зависимости (ВСЕ библиотеки вашего приложения)
requirements = python3==3.9.7,kivy==2.1.0,kivymd==1.1.1,speechrecognition==3.10.0,pandas==1.5.3,openpyxl==3.1.2,pyaudio==0.2.11,requests==2.31.0,android,pyjnius,plyer

# Файлы, которые включить в APK
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json,wav,mp3
source.include_patterns = 
source.exclude_exts = spec,pyc
source.exclude_dirs = tests,bin

# Иконка
icon.filename = icon.png

# Разрешения для Android
android.permissions = INTERNET, RECORD_AUDIO, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Версии Android
android.api = 31
android.minapi = 21
android.ndk = 23b
android.sdk = 30
android.arch = arm64-v8a, armeabi-v7a

# Для работы с микрофоном и голосом
android.gradle_dependencies = 'com.google.android.gms:play-services-auth:20.7.0', 'com.google.android.gms:play-services-location:21.0.1'

# Дополнительные настройки
android.allow_background = True
android.add_android_metadata = 

# Полноэкранный режим
fullscreen = 0

# Ориентация
orientation = portrait

# OSX, Windows, Linux
osx.python_version = 3
osx.kivy_version = 2.1.0

# Kivy
kivy_version = 2.1.0

# Папка для сборки
build_dir = .buildozer
dist_dir = bin

# Игнорировать ошибки
ignore_requirements = 

# Для отладки
log_level = 2