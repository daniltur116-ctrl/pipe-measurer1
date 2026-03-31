"""
Трубомер - Голосовой измеритель труб
Полноценное мобильное приложение для Android с графическим интерфейсом
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import platform
from kivy.animation import Animation

import speech_recognition as sr
import pandas as pd
from datetime import datetime, timedelta
import os
import re
import json
import hashlib
from pathlib import Path
import threading

# Установка цвета фона и размера окна
Window.clearcolor = (0.95, 0.95, 0.95, 1)
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.RECORD_AUDIO, Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE])

# ============= СИСТЕМА АВТОРИЗАЦИИ =============
class UserManager:
    def __init__(self):
        # Для Android используем путь в хранилище приложения
        if platform == 'android':
            from android.storage import app_storage_path
            self.data_dir = app_storage_path()
        else:
            self.data_dir = os.getcwd()
        
        self.users_file = os.path.join(self.data_dir, 'users.json')
        self.current_user = None
        self.load_users()
    
    def load_users(self):
        """Загружает пользователей из файла"""
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r', encoding='utf-8') as f:
                self.users = json.load(f)
        else:
            self.users = {}
            # Создаем тестового пользователя
            self.register_user('admin', 'admin123', 'Администратор')
    
    def save_users(self):
        """Сохраняет пользователей в файл"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def hash_password(self, password):
        """Хеширует пароль"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username, password, full_name=''):
        """Регистрирует нового пользователя"""
        if username in self.users:
            return False, "Пользователь уже существует"
        
        measurements_file = os.path.join(self.data_dir, f'measurements_{username}.json')
        self.users[username] = {
            'password': self.hash_password(password),
            'full_name': full_name,
            'registered': datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            'measurements_file': measurements_file
        }
        self.save_users()
        return True, "Пользователь зарегистрирован"
    
    def login(self, username, password):
        """Авторизация пользователя"""
        if username not in self.users:
            return False, "Пользователь не найден"
        
        if self.users[username]['password'] != self.hash_password(password):
            return False, "Неверный пароль"
        
        self.current_user = username
        return True, f"Добро пожаловать, {username}!"
    
    def logout(self):
        """Выход из системы"""
        self.current_user = None
    
    def get_user_data_file(self):
        """Возвращает путь к файлу с данными пользователя"""
        if self.current_user:
            return self.users[self.current_user]['measurements_file']
        return None

# ============= УПРАВЛЕНИЕ ДАННЫМИ ПОЛЬЗОВАТЕЛЯ =============
class UserData:
    def __init__(self, user_manager):
        self.user_manager = user_manager
        self.measurements = []
        self.load_measurements()
    
    def load_measurements(self):
        """Загружает измерения текущего пользователя"""
        filename = self.user_manager.get_user_data_file()
        if filename and os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                self.measurements = json.load(f)
        else:
            self.measurements = []
    
    def save_measurements(self):
        """Сохраняет измерения текущего пользователя"""
        filename = self.user_manager.get_user_data_file()
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.measurements, f, ensure_ascii=False, indent=2)
    
    def add_measurement(self, measurement):
        """Добавляет измерение"""
        self.measurements.append(measurement)
        self.save_measurements()
    
    def get_measurements(self):
        """Возвращает измерения"""
        return self.measurements
    
    def clear_measurements(self):
        """Очищает измерения"""
        self.measurements = []
        self.save_measurements()
    
    def remove_last(self):
        """Удаляет последнее измерение"""
        if self.measurements:
            removed = self.measurements.pop()
            self.save_measurements()
            return removed
        return None
    
    def remove_by_index(self, index):
        """Удаляет измерение по индексу"""
        if 0 <= index < len(self.measurements):
            removed = self.measurements.pop(index)
            self.save_measurements()
            return removed
        return None

# ============= ФУНКЦИИ ПАРСИНГА =============
def convert_words_to_numbers(text):
    """Преобразует слова в числа"""
    words = {
        'ноль': '0', 'один': '1', 'два': '2', 'три': '3', 'четыре': '4',
        'пять': '5', 'шесть': '6', 'семь': '7', 'восемь': '8', 'девять': '9',
        'десять': '10', 'одиннадцать': '11', 'двенадцать': '12', 'тринадцать': '13',
        'четырнадцать': '14', 'пятнадцать': '15', 'шестнадцать': '16', 'семнадцать': '17',
        'восемнадцать': '18', 'девятнадцать': '19', 'двадцать': '20', 'тридцать': '30',
        'сорок': '40', 'пятьдесят': '50', 'шестьдесят': '60', 'семьдесят': '70',
        'восемьдесят': '80', 'девяносто': '90', 'сто': '100', 'двести': '200',
        'триста': '300', 'четыреста': '400', 'пятьсот': '500', 'шестьсот': '600',
        'семьсот': '700', 'восемьсот': '800', 'девятьсот': '900',
        'тысяча': '1000', 'миллион': '1000000'
    }
    
    for word, num in words.items():
        text = text.replace(word, num)
    
    return text

def parse_length_text(text):
    """Парсинг текста с длиной"""
    text = text.lower().strip()
    text = convert_words_to_numbers(text)
    
    # Ищем числа
    numbers = re.findall(r'\d+[.,]?\d*', text)
    
    if not numbers:
        return 0.0
    
    total_meters = 0.0
    
    # Определяем единицы измерения
    for num_str in numbers:
        num = float(num_str.replace(',', '.'))
        
        # Ищем контекст вокруг числа
        context_start = max(0, text.find(num_str) - 20)
        context_end = min(len(text), text.find(num_str) + len(num_str) + 20)
        context = text[context_start:context_end]
        
        if 'миллиметр' in context or 'мм' in context:
            total_meters += num / 1000
        elif 'сантиметр' in context or 'см' in context:
            total_meters += num / 100
        elif 'метр' in context or 'м' in context:
            total_meters += num
        elif 'километр' in context or 'км' in context:
            total_meters += num * 1000
        else:
            # Если единицы не указаны, считаем что это метры
            total_meters += num
    
    return round(total_meters, 3)

def format_length(length_m):
    """Форматирует длину в читаемый вид"""
    if length_m >= 1:
        return f"{length_m:.2f} м"
    else:
        return f"{int(length_m * 1000)} мм"

# ============= КАСТОМНЫЕ ВИДЖЕТЫ =============
class RoundedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0.2, 0.6, 0.8, 1)
        self.color = (1, 1, 1, 1)
        self.size_hint_y = None
        self.height = dp(50)
        self.font_size = dp(16)
        
        with self.canvas.before:
            Color(0.2, 0.6, 0.8, 1)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(10)])
        
        self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class MeasurementCard(BoxLayout):
    """Карточка измерения для списка"""
    def __init__(self, measurement, index, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.measurement = measurement
        self.index = index
        self.on_delete = on_delete
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(120)
        self.padding = dp(10)
        self.spacing = dp(5)
        
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(5)])
        
        # ID и дата
        header = BoxLayout(size_hint_y=None, height=dp(30))
        id_label = Label(text=f"🆔 {measurement.get('ID', 'N/A')}", 
                         font_size=dp(12), halign='left', size_hint_x=0.7)
        date_label = Label(text=f"{measurement.get('Дата', '')} {measurement.get('Время', '')}", 
                          font_size=dp(10), halign='right', size_hint_x=0.3)
        header.add_widget(id_label)
        header.add_widget(date_label)
        
        # Длина
        length_label = Label(text=f"📏 {measurement.get('Формат', '')}",
                            font_size=dp(18), bold=True, size_hint_y=None, height=dp(35))
        
        # Оригинальный текст
        text_label = Label(text=f"📝 {measurement.get('Оригинальный текст', '')[:50]}",
                          font_size=dp(10), size_hint_y=None, height=dp(30))
        
        # Кнопка удаления
        btn_layout = BoxLayout(size_hint_y=None, height=dp(30))
        delete_btn = Button(text="🗑️ Удалить", size_hint_x=0.3, background_color=(0.8, 0.2, 0.2, 1))
        delete_btn.bind(on_press=self.delete_measurement)
        btn_layout.add_widget(Label(size_hint_x=0.7))
        btn_layout.add_widget(delete_btn)
        
        self.add_widget(header)
        self.add_widget(length_label)
        self.add_widget(text_label)
        self.add_widget(btn_layout)
        
        self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def delete_measurement(self, instance):
        if self.on_delete:
            self.on_delete(self.index)

# ============= ОСНОВНОЙ КЛАСС ПРИЛОЖЕНИЯ =============
class PipeMeasurerApp(App):
    def build(self):
        self.user_manager = UserManager()
        self.user_data = None
        self.current_screen = 'auth'
        
        # Основной контейнер
        self.main_layout = BoxLayout(orientation='vertical')
        
        # Заголовок
        self.title_bar = BoxLayout(size_hint_y=0.08, padding=[dp(10), dp(5)], spacing=dp(10))
        with self.title_bar.canvas.before:
            Color(0.2, 0.4, 0.6, 1)
            self.title_rect = RoundedRectangle(size=self.title_bar.size, pos=self.title_bar.pos, radius=[0])
        
        self.title_label = Label(text="ТРУБОМЕР", font_size=dp(20), bold=True, color=(1, 1, 1, 1))
        self.user_label = Label(text="", font_size=dp(12), color=(1, 1, 1, 1), size_hint_x=0.3)
        self.title_bar.add_widget(self.title_label)
        self.title_bar.add_widget(self.user_label)
        
        self.main_layout.add_widget(self.title_bar)
        
        # Контент (будет меняться)
        self.content_area = BoxLayout(orientation='vertical')
        self.main_layout.add_widget(self.content_area)
        
        # Показываем экран авторизации
        self.show_auth_screen()
        
        return self.main_layout
    
    def show_auth_screen(self):
        """Показывает экран авторизации"""
        self.content_area.clear_widgets()
        self.user_label.text = ""
        
        # Центральный контейнер
        center_layout = BoxLayout(orientation='vertical', size_hint=(0.9, 0.8), 
                                   pos_hint={'center_x': 0.5, 'center_y': 0.5})
        
        # Логотип или иконка
        logo_label = Label(text="📏", font_size=dp(60), size_hint_y=0.2)
        center_layout.add_widget(logo_label)
        
        # Кнопки
        login_btn = RoundedButton(text="🔑 Войти", size_hint_y=0.12)
        login_btn.bind(on_press=self.show_login_popup)
        
        register_btn = RoundedButton(text="📝 Зарегистрироваться", size_hint_y=0.12)
        register_btn.bind(on_press=self.show_register_popup)
        
        center_layout.add_widget(Label(size_hint_y=0.1))
        center_layout.add_widget(login_btn)
        center_layout.add_widget(Label(size_hint_y=0.05))
        center_layout.add_widget(register_btn)
        center_layout.add_widget(Label(size_hint_y=0.1))
        
        self.content_area.add_widget(center_layout)
    
    def show_login_popup(self, instance):
        """Показывает попап для входа"""
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        username_input = TextInput(hint_text="Имя пользователя", multiline=False, size_hint_y=0.2)
        password_input = TextInput(hint_text="Пароль", password=True, multiline=False, size_hint_y=0.2)
        
        btn_layout = BoxLayout(size_hint_y=0.2, spacing=dp(10))
        login_btn = Button(text="Войти")
        cancel_btn = Button(text="Отмена")
        
        btn_layout.add_widget(login_btn)
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(username_input)
        content.add_widget(password_input)
        content.add_widget(btn_layout)
        
        popup = Popup(title="Вход в систему", content=content, size_hint=(0.8, 0.4))
        
        def do_login(instance):
            username = username_input.text.strip()
            password = password_input.text
            success, message = self.user_manager.login(username, password)
            
            if success:
                self.user_data = UserData(self.user_manager)
                popup.dismiss()
                self.show_main_screen()
            else:
                # Показываем ошибку
                error_label = Label(text=message, color=(1, 0, 0, 1))
                content.add_widget(error_label)
                Clock.schedule_once(lambda dt: content.remove_widget(error_label), 2)
        
        login_btn.bind(on_press=do_login)
        cancel_btn.bind(on_press=popup.dismiss)
        
        popup.open()
    
    def show_register_popup(self, instance):
        """Показывает попап для регистрации"""
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        username_input = TextInput(hint_text="Имя пользователя", multiline=False, size_hint_y=0.15)
        password_input = TextInput(hint_text="Пароль", password=True, multiline=False, size_hint_y=0.15)
        confirm_input = TextInput(hint_text="Подтвердите пароль", password=True, multiline=False, size_hint_y=0.15)
        fullname_input = TextInput(hint_text="Ваше имя (необязательно)", multiline=False, size_hint_y=0.15)
        
        btn_layout = BoxLayout(size_hint_y=0.15, spacing=dp(10))
        register_btn = Button(text="Зарегистрироваться")
        cancel_btn = Button(text="Отмена")
        
        btn_layout.add_widget(register_btn)
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(username_input)
        content.add_widget(password_input)
        content.add_widget(confirm_input)
        content.add_widget(fullname_input)
        content.add_widget(btn_layout)
        
        popup = Popup(title="Регистрация", content=content, size_hint=(0.9, 0.6))
        
        def do_register(instance):
            username = username_input.text.strip()
            password = password_input.text
            confirm = confirm_input.text
            fullname = fullname_input.text.strip()
            
            if not username or not password:
                error_label = Label(text="Заполните обязательные поля", color=(1, 0, 0, 1))
                content.add_widget(error_label)
                Clock.schedule_once(lambda dt: content.remove_widget(error_label), 2)
                return
            
            if password != confirm:
                error_label = Label(text="Пароли не совпадают", color=(1, 0, 0, 1))
                content.add_widget(error_label)
                Clock.schedule_once(lambda dt: content.remove_widget(error_label), 2)
                return
            
            success, message = self.user_manager.register_user(username, password, fullname)
            
            if success:
                popup.dismiss()
                # Показываем сообщение об успехе
                success_popup = Popup(title="Успех", 
                                     content=Label(text=message), 
                                     size_hint=(0.6, 0.3))
                success_popup.open()
                Clock.schedule_once(lambda dt: success_popup.dismiss(), 2)
            else:
                error_label = Label(text=message, color=(1, 0, 0, 1))
                content.add_widget(error_label)
                Clock.schedule_once(lambda dt: content.remove_widget(error_label), 2)
        
        register_btn.bind(on_press=do_register)
        cancel_btn.bind(on_press=popup.dismiss)
        
        popup.open()
    
    def show_main_screen(self):
        """Показывает главный экран приложения"""
        self.content_area.clear_widgets()
        self.user_label.text = f"👤 {self.user_manager.current_user}"
        
        # Кнопки главного меню
        menu_layout = GridLayout(cols=2, padding=dp(10), spacing=dp(10), size_hint_y=0.5)
        
        buttons = [
            ("🎤 Голосовой ввод", self.voice_input_screen),
            ("⌨️ Ручной ввод", self.manual_input_screen),
            ("📋 Мои измерения", self.show_measurements_screen),
            ("📊 Экспорт в Excel", self.export_to_excel),
            ("📈 Статистика", self.show_stats_screen),
            ("⚙️ Настройки", self.show_settings_screen),
            ("🚪 Выйти", self.logout)
        ]
        
        for text, callback in buttons:
            btn = RoundedButton(text=text)
            btn.bind(on_press=callback)
            menu_layout.add_widget(btn)
        
        self.content_area.add_widget(menu_layout)
        
        # Информационная панель
        info_panel = BoxLayout(orientation='vertical', size_hint_y=0.3, padding=dp(10), spacing=dp(5))
        with info_panel.canvas.before:
            Color(0.9, 0.9, 0.9, 1)
            self.info_rect = RoundedRectangle(size=info_panel.size, pos=info_panel.pos, radius=[dp(10)])
        
        self.info_label = Label(text=self.get_info_text(), font_size=dp(12), size_hint_y=0.8)
        info_panel.add_widget(self.info_label)
        
        self.content_area.add_widget(info_panel)
    
    def get_info_text(self):
        """Возвращает текст информационной панели"""
        if self.user_data:
            measurements = self.user_data.get_measurements()
            total = sum(m['Длина, м'] for m in measurements) if measurements else 0
            count = len(measurements)
            return f"📊 Статистика:\nВсего замеров: {count}\nОбщая длина: {format_length(total)}"
        return "📊 Статистика отсутствует"
    
    def voice_input_screen(self, instance):
        """Экран голосового ввода"""
        self.content_area.clear_widgets()
        
        # Заголовок
        title = Label(text="🎤 Голосовой ввод", font_size=dp(18), bold=True, size_hint_y=0.1)
        self.content_area.add_widget(title)
        
        # Инструкция
        instruction = Label(text="Нажмите кнопку и произнесите длину трубы\n\nПримеры:\n'5 метров 15 сантиметров'\n'120 миллиметров'\n'2.5 метра'",
                           font_size=dp(12), size_hint_y=0.25)
        self.content_area.add_widget(instruction)
        
        # Кнопка записи
        self.record_btn = RoundedButton(text="🔴 Начать запись", size_hint_y=0.15)
        self.record_btn.bind(on_press=self.start_recording)
        self.content_area.add_widget(self.record_btn)
        
        # Статус
        self.status_label = Label(text="Готов к записи", font_size=dp(12), size_hint_y=0.1)
        self.content_area.add_widget(self.status_label)
        
        # Результат
        self.result_label = Label(text="", font_size=dp(14), size_hint_y=0.2)
        self.content_area.add_widget(self.result_label)
        
        # Кнопка назад
        back_btn = RoundedButton(text="◀ Назад", size_hint_y=0.1)
        back_btn.bind(on_press=lambda x: self.show_main_screen())
        self.content_area.add_widget(back_btn)
    
    def start_recording(self, instance):
        """Запускает запись голоса в отдельном потоке"""
        self.record_btn.disabled = True
        self.status_label.text = "🎤 Слушаю... Говорите громко и четко"
        
        # Запускаем в отдельном потоке
        threading.Thread(target=self.record_voice_thread, daemon=True).start()
    
    def record_voice_thread(self):
        """Поток для записи голоса"""
        recognizer = sr.Recognizer()
        
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                text = recognizer.recognize_google(audio, language="ru-RU")
                
                # Парсим длину
                length_m = parse_length_text(text)
                
                # Создаем измерение
                measurement = {
                    "Длина, м": length_m,
                    "Оригинальный текст": text,
                    "Формат": format_length(length_m),
                    "Время": datetime.now().strftime("%H:%M:%S"),
                    "Дата": datetime.now().strftime("%d.%m.%Y"),
                    "Пользователь": self.user_manager.current_user,
                    "ID": f"TR-{datetime.now().strftime('%y%m%d%H%M%S')}-{len(self.user_data.get_measurements())+1}"
                }
                
                # Сохраняем
                self.user_data.add_measurement(measurement)
                
                # Обновляем UI
                Clock.schedule_once(lambda dt: self.recording_success(text, length_m, measurement['ID']))
                
        except sr.WaitTimeoutError:
            Clock.schedule_once(lambda dt: self.recording_error("Время ожидания истекло"))
        except sr.UnknownValueError:
            Clock.schedule_once(lambda dt: self.recording_error("Речь не распознана"))
        except sr.RequestError:
            Clock.schedule_once(lambda dt: self.recording_error("Ошибка подключения к интернету"))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.recording_error(f"Ошибка: {str(e)}"))
    
    def recording_success(self, text, length_m, measurement_id):
        """Обработка успешной записи"""
        self.status_label.text = "✅ Запись успешно обработана!"
        self.result_label.text = f"Распознано: {text}\n📏 Длина: {format_length(length_m)}\n🆔 ID: {measurement_id}"
        self.record_btn.disabled = False
        
        # Анимация
        anim = Animation(color=(0.2, 0.8, 0.2, 1), duration=0.5)
        anim.start(self.record_btn)
        Clock.schedule_once(lambda dt: self.reset_button_color(), 0.5)
    
    def reset_button_color(self):
        self.record_btn.background_color = (0.2, 0.6, 0.8, 1)
    
    def recording_error(self, error_msg):
        """Обработка ошибки записи"""
        self.status_label.text = f"❌ {error_msg}"
        self.record_btn.disabled = False
        self.record_btn.background_color = (0.8, 0.2, 0.2, 1)
        Clock.schedule_once(lambda dt: self.reset_button_color(), 2)
    
    def manual_input_screen(self, instance):
        """Экран ручного ввода"""
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        text_input = TextInput(hint_text="Введите длину трубы\n\nНапример:\n5 метров 15 см\n120 мм\n2.5 м",
                               multiline=False, size_hint_y=0.3)
        
        btn_layout = BoxLayout(size_hint_y=0.2, spacing=dp(10))
        save_btn = Button(text="Сохранить")
        cancel_btn = Button(text="Отмена")
        
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(Label(text="Введите длину трубы:", size_hint_y=0.1))
        content.add_widget(text_input)
        content.add_widget(btn_layout)
        
        popup = Popup(title="Ручной ввод", content=content, size_hint=(0.9, 0.5))
        
        def save_measurement(instance):
            text = text_input.text.strip()
            if text:
                length_m = parse_length_text(text)
                measurement = {
                    "Длина, м": length_m,
                    "Оригинальный текст": text,
                    "Формат": format_length(length_m),
                    "Время": datetime.now().strftime("%H:%M:%S"),
                    "Дата": datetime.now().strftime("%d.%m.%Y"),
                    "Пользователь": self.user_manager.current_user,
                    "ID": f"TR-{datetime.now().strftime('%y%m%d%H%M%S')}-{len(self.user_data.get_measurements())+1}"
                }
                self.user_data.add_measurement(measurement)
                popup.dismiss()
                
                # Показываем сообщение об успехе
                success_popup = Popup(title="Успех",
                                     content=Label(text=f"✅ Добавлено: {format_length(length_m)}"),
                                     size_hint=(0.6, 0.3))
                success_popup.open()
                Clock.schedule_once(lambda dt: success_popup.dismiss(), 1.5)
                
                # Обновляем главный экран
                self.show_main_screen()
            else:
                error_label = Label(text="Введите значение", color=(1, 0, 0, 1))
                content.add_widget(error_label)
                Clock.schedule_once(lambda dt: content.remove_widget(error_label), 2)
        
        save_btn.bind(on_press=save_measurement)
        cancel_btn.bind(on_press=popup.dismiss)
        
        popup.open()
    
    def show_measurements_screen(self, instance):
        """Показывает список всех измерений"""
        measurements = self.user_data.get_measurements()
        
        if not measurements:
            popup = Popup(title="Нет измерений",
                         content=Label(text="📭 У вас пока нет измерений"),
                         size_hint=(0.7, 0.3))
            popup.open()
            Clock.schedule_once(lambda dt: popup.dismiss(), 2)
            return
        
        self.content_area.clear_widgets()
        
        # Заголовок
        header = BoxLayout(size_hint_y=0.08, padding=[dp(10), dp(5)])
        header.add_widget(Label(text="📋 Мои измерения", font_size=dp(18), bold=True))
        
        # Кнопка назад
        back_btn = Button(text="◀ Назад", size_hint_x=0.2, background_color=(0.2, 0.6, 0.8, 1))
        back_btn.bind(on_press=lambda x: self.show_main_screen())
        header.add_widget(back_btn)
        
        self.content_area.add_widget(header)
        
        # Список измерений
        scroll = ScrollView()
        list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5), padding=dp(5))
        list_layout.bind(minimum_height=list_layout.setter('height'))
        
        for i, m in enumerate(reversed(measurements)):  # Показываем новые первыми
            card = MeasurementCard(m, len(measurements) - 1 - i, self.delete_measurement)
            list_layout.add_widget(card)
        
        scroll.add_widget(list_layout)
        self.content_area.add_widget(scroll)
        
        # Статистика внизу
        total = sum(m['Длина, м'] for m in measurements)
        stats_label = Label(text=f"Всего: {len(measurements)} | Общая длина: {format_length(total)}",
                           size_hint_y=0.07, font_size=dp(12))
        self.content_area.add_widget(stats_label)
    
    def delete_measurement(self, index):
        """Удаляет измерение"""
        removed = self.user_data.remove_by_index(index)
        if removed:
            self.show_measurements_screen(None)  # Обновляем список
    
    def show_stats_screen(self, instance):
        """Показывает статистику"""
        measurements = self.user_data.get_measurements()
        
        if not measurements:
            popup = Popup(title="Нет данных",
                         content=Label(text="📭 Нет измерений для статистики"),
                         size_hint=(0.7, 0.3))
            popup.open()
            Clock.schedule_once(lambda dt: popup.dismiss(), 2)
            return
        
        self.content_area.clear_widgets()
        
        # Заголовок
        header = BoxLayout(size_hint_y=0.08, padding=[dp(10), dp(5)])
        header.add_widget(Label(text="📈 Статистика", font_size=dp(18), bold=True))
        
        back_btn = Button(text="◀ Назад", size_hint_x=0.2, background_color=(0.2, 0.6, 0.8, 1))
        back_btn.bind(on_press=lambda x: self.show_main_screen())
        header.add_widget(back_btn)
        
        self.content_area.add_widget(header)
        
        # Статистические данные
        stats_layout = GridLayout(cols=2, padding=dp(10), spacing=dp(10), size_hint_y=None)
        stats_layout.bind(minimum_height=stats_layout.setter('height'))
        
        total = sum(m['Длина, м'] for m in measurements)
        avg = total / len(measurements)
        max_val = max(m['Длина, м'] for m in measurements)
        min_val = min(m['Длина, м'] for m in measurements)
        
        # Подсчет за сегодня
        today = datetime.now().date()
        today_measurements = [m for m in measurements 
                              if datetime.strptime(m['Дата'], '%d.%m.%Y').date() == today]
        today_total = sum(m['Длина, м'] for m in today_measurements)
        
        stats = [
            ("📊 Всего замеров:", str(len(measurements))),
            ("📏 Общая длина:", format_length(total)),
            ("📐 Средняя длина:", format_length(avg)),
            ("📈 Максимум:", format_length(max_val)),
            ("📉 Минимум:", format_length(min_val)),
            ("📅 Замеров сегодня:", str(len(today_measurements))),
            ("📏 Длина сегодня:", format_length(today_total))
        ]
        
        for label, value in stats:
            stats_layout.add_widget(Label(text=label, font_size=dp(14), halign='left', size_hint_x=0.5))
            stats_layout.add_widget(Label(text=value, font_size=dp(14), bold=True, halign='right', size_hint_x=0.5))
        
        scroll = ScrollView()
        scroll.add_widget(stats_layout)
        self.content_area.add_widget(scroll)
    
    def export_to_excel(self, instance):
        """Экспорт в Excel"""
        measurements = self.user_data.get_measurements()
        
        if not measurements:
            popup = Popup(title="Нет данных",
                         content=Label(text="📭 Нет измерений для экспорта"),
                         size_hint=(0.7, 0.3))
            popup.open()
            Clock.schedule_once(lambda dt: popup.dismiss(), 2)
            return
        
        try:
            # Создаем DataFrame
            df = pd.DataFrame(measurements)
            
            # Определяем путь для сохранения
            if platform == 'android':
                from android.storage import primary_external_storage_path
                docs_path = os.path.join(primary_external_storage_path(), 'Documents', 'Трубомер')
            else:
                docs_path = os.path.join(os.path.expanduser('~'), 'Documents', 'Трубомер')
            
            os.makedirs(docs_path, exist_ok=True)
            filename = os.path.join(docs_path, f"замеры_{self.user_manager.current_user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            
            # Сохраняем Excel
            df.to_excel(filename, index=False, sheet_name='Замеры')
            
            # Показываем сообщение об успехе
            success_popup = Popup(title="Экспорт завершен",
                                 content=Label(text=f"✅ Файл сохранен:\n{filename}", font_size=dp(12)),
                                 size_hint=(0.9, 0.3))
            success_popup.open()
            Clock.schedule_once(lambda dt: success_popup.dismiss(), 3)
            
        except Exception as e:
            error_popup = Popup(title="Ошибка экспорта",
                               content=Label(text=f"❌ {str(e)}", font_size=dp(12)),
                               size_hint=(0.8, 0.3))
            error_popup.open()
            Clock.schedule_once(lambda dt: error_popup.dismiss(), 3)
    
    def show_settings_screen(self, instance):
        """Показывает экран настроек"""
        self.content_area.clear_widgets()
        
        # Заголовок
        header = BoxLayout(size_hint_y=0.08, padding=[dp(10), dp(5)])
        header.add_widget(Label(text="⚙️ Настройки", font_size=dp(18), bold=True))
        
        back_btn = Button(text="◀ Назад", size_hint_x=0.2, background_color=(0.2, 0.6, 0.8, 1))
        back_btn.bind(on_press=lambda x: self.show_main_screen())
        header.add_widget(back_btn)
        
        self.content_area.add_widget(header)
        
        # Настройки
        settings_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # Информация о пользователе
        user_info = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(100))
        user_info.add_widget(Label(text=f"👤 Пользователь: {self.user_manager.current_user}", font_size=dp(14)))
        if self.user_manager.users[self.user_manager.current_user].get('full_name'):
            user_info.add_widget(Label(text=f"📛 Имя: {self.user_manager.users[self.user_manager.current_user]['full_name']}", font_size=dp(12)))
        user_info.add_widget(Label(text=f"📅 Зарегистрирован: {self.user_manager.users[self.user_manager.current_user]['registered']}", font_size=dp(10)))
        settings_layout.add_widget(user_info)
        
        # Кнопки действий
        clear_btn = RoundedButton(text="🗑️ Очистить все измерения")
        clear_btn.bind(on_press=self.clear_all_measurements)
        
        change_pass_btn = RoundedButton(text="🔐 Сменить пароль")
        change_pass_btn.bind(on_press=self.change_password)
        
        settings_layout.add_widget(clear_btn)
        settings_layout.add_widget(change_pass_btn)
        
        # Информация о приложении
        version_label = Label(text="Трубомер v5.0\nДля Android", font_size=dp(10), size_hint_y=0.1)
        settings_layout.add_widget(version_label)
        
        scroll = ScrollView()
        scroll.add_widget(settings_layout)
        self.content_area.add_widget(scroll)
    
    def clear_all_measurements(self, instance):
        """Очищает все измерения"""
        def confirm_clear(instance):
            self.user_data.clear_measurements()
            confirm_popup.dismiss()
            
            # Показываем сообщение об успехе
            success_popup = Popup(title="Успех",
                                 content=Label(text="✅ Все измерения удалены"),
                                 size_hint=(0.6, 0.3))
            success_popup.open()
            Clock.schedule_once(lambda dt: success_popup.dismiss(), 1.5)
            self.show_main_screen()
        
        content = BoxLayout(orientation='vertical', spacing=dp(10))
        content.add_widget(Label(text="Вы уверены, что хотите удалить ВСЕ измерения?\nЭто действие нельзя отменить!"))
        
        btn_layout = BoxLayout(size_hint_y=0.3, spacing=dp(10))
        yes_btn = Button(text="Да, удалить", background_color=(0.8, 0.2, 0.2, 1))
        no_btn = Button(text="Отмена")
        
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(btn_layout)
        
        confirm_popup = Popup(title="Подтверждение", content=content, size_hint=(0.8, 0.3))
        
        yes_btn.bind(on_press=confirm_clear)
        no_btn.bind(on_press=confirm_popup.dismiss)
        
        confirm_popup.open()
    
    def change_password(self, instance):
        """Смена пароля"""
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        old_pass = TextInput(hint_text="Старый пароль", password=True, multiline=False, size_hint_y=0.2)
        new_pass = TextInput(hint_text="Новый пароль", password=True, multiline=False, size_hint_y=0.2)
        confirm_pass = TextInput(hint_text="Подтвердите пароль", password=True, multiline=False, size_hint_y=0.2)
        
        btn_layout = BoxLayout(size_hint_y=0.2, spacing=dp(10))
        save_btn = Button(text="Сохранить")
        cancel_btn = Button(text="Отмена")
        
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(old_pass)
        content.add_widget(new_pass)
        content.add_widget(confirm_pass)
        content.add_widget(btn_layout)
        
        popup = Popup(title="Смена пароля", content=content, size_hint=(0.9, 0.5))
        
        def do_change(instance):
            old = old_pass.text
            new = new_pass.text
            confirm = confirm_pass.text
            
            # Проверяем старый пароль
            current_hash = self.user_manager.users[self.user_manager.current_user]['password']
            if current_hash != self.user_manager.hash_password(old):
                error_label = Label(text="Неверный старый пароль", color=(1, 0, 0, 1))
                content.add_widget(error_label)
                Clock.schedule_once(lambda dt: content.remove_widget(error_label), 2)
                return
            
            if new != confirm:
                error_label = Label(text="Пароли не совпадают", color=(1, 0, 0, 1))
                content.add_widget(error_label)
                Clock.schedule_once(lambda dt: content.remove_widget(error_label), 2)
                return
            
            if len(new) < 4:
                error_label = Label(text="Пароль должен быть не менее 4 символов", color=(1, 0, 0, 1))
                content.add_widget(error_label)
                Clock.schedule_once(lambda dt: content.remove_widget(error_label), 2)
                return
            
            # Меняем пароль
            self.user_manager.users[self.user_manager.current_user]['password'] = self.user_manager.hash_password(new)
            self.user_manager.save_users()
            
            popup.dismiss()
            success_popup = Popup(title="Успех",
                                 content=Label(text="✅ Пароль успешно изменен"),
                                 size_hint=(0.6, 0.3))
            success_popup.open()
            Clock.schedule_once(lambda dt: success_popup.dismiss(), 2)
        
        save_btn.bind(on_press=do_change)
        cancel_btn.bind(on_press=popup.dismiss)
        
        popup.open()
    
    def logout(self, instance):
        """Выход из аккаунта"""
        self.user_manager.logout()
        self.user_data = None
        self.show_auth_screen()

# Запуск приложения
if __name__ == '__main__':
    PipeMeasurerApp().run()