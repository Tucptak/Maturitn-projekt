"""
Braniac - Desktopová aplikace (PyQt5)
Maturitní projekt 2026

Tato aplikace umožňuje hrát kvízy z databáze přes desktopové rozhraní.
"""
import sys
import os
import requests
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QStackedWidget, QListWidget,
    QListWidgetItem, QMessageBox, QFrame, QProgressBar, QGridLayout,
    QScrollArea, QComboBox, QSpacerItem, QSizePolicy, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QPalette, QColor

# Konfigurace API
API_BASE_URL = os.getenv('API_URL', 'http://localhost:5000')


class StyleSheet:
    """Definice stylů pro aplikaci."""
    
    MAIN = """
        QMainWindow {
            background-color: #0f172a;
        }
        QWidget {
            background-color: #0f172a;
            color: #f8fafc;
            font-family: 'Segoe UI', sans-serif;
        }
        QLabel {
            color: #f8fafc;
        }
        QPushButton {
            background-color: #6366f1;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #4f46e5;
        }
        QPushButton:pressed {
            background-color: #4338ca;
        }
        QPushButton:disabled {
            background-color: #334155;
            color: #64748b;
        }
        QPushButton.answer {
            background-color: #1e293b;
            border: 2px solid #334155;
            text-align: left;
            padding: 15px 20px;
            font-size: 16px;
        }
        QPushButton.answer:hover {
            border-color: #6366f1;
            background-color: rgba(99, 102, 241, 0.1);
        }
        QPushButton.answer.selected {
            border-color: #6366f1;
            background-color: rgba(99, 102, 241, 0.2);
        }
        QPushButton.answer.correct {
            border-color: #22c55e;
            background-color: rgba(34, 197, 94, 0.2);
        }
        QPushButton.answer.incorrect {
            border-color: #ef4444;
            background-color: rgba(239, 68, 68, 0.2);
        }
        QLineEdit {
            background-color: #1e293b;
            border: 2px solid #334155;
            border-radius: 8px;
            padding: 12px 16px;
            color: #f8fafc;
            font-size: 14px;
        }
        QLineEdit:focus {
            border-color: #6366f1;
        }
        QListWidget {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 5px;
        }
        QListWidget::item {
            background-color: #0f172a;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 15px;
            margin: 5px;
        }
        QListWidget::item:selected {
            background-color: rgba(99, 102, 241, 0.2);
            border-color: #6366f1;
        }
        QListWidget::item:hover {
            border-color: #6366f1;
        }
        QProgressBar {
            background-color: #334155;
            border: none;
            border-radius: 4px;
            height: 8px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #6366f1;
            border-radius: 4px;
        }
        QComboBox {
            background-color: #1e293b;
            border: 2px solid #334155;
            border-radius: 8px;
            padding: 10px 15px;
            color: #f8fafc;
        }
        QComboBox:hover {
            border-color: #6366f1;
        }
        QComboBox:focus {
            border-color: #6366f1;
        }
        QComboBox:on {
            border-color: #4338ca;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: #1e293b;
            border: 2px solid #334155;
            padding: 4px 0px;
            outline: none;
            selection-background-color: rgba(99, 102, 241, 0.25);
            selection-color: #f8fafc;
            color: #f8fafc;
        }
        QComboBox QAbstractItemView::item {
            padding: 10px 15px;
            min-height: 20px;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: rgba(99, 102, 241, 0.15);
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: rgba(99, 102, 241, 0.25);
        }
        QScrollArea {
            border: none;
        }
        QScrollBar:vertical {
            background-color: #1e293b;
            width: 10px;
            margin: 0;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background-color: #334155;
            min-height: 30px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #6366f1;
        }
        QScrollBar::handle:vertical:pressed {
            background-color: #4f46e5;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
            background: none;
            border: none;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        QScrollBar:horizontal {
            background-color: #1e293b;
            height: 10px;
            margin: 0;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal {
            background-color: #334155;
            min-width: 30px;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #6366f1;
        }
        QScrollBar::handle:horizontal:pressed {
            background-color: #4f46e5;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0;
            background: none;
            border: none;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
        QFrame.card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
        }
    """


class APIClient:
    """Klient pro komunikaci s Flask API."""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.user = None
    
    def login(self, email, password):
        """Přihlášení uživatele."""
        try:
            # Pro desktop app používáme speciální API endpoint
            response = self.session.post(
                f"{self.base_url}/api/login",
                json={'email': email, 'password': password}
            )
            if response.status_code == 200:
                data = response.json()
                self.user = data.get('user')
                return True, data
            else:
                return False, response.json().get('error', 'Přihlášení selhalo')
        except Exception as e:
            return False, str(e)
    
    def token_login(self, token):
        """Přihlášení pomocí SSO tokenu z webové aplikace."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/token",
                json={'token': token}
            )
            if response.status_code == 200:
                data = response.json()
                self.user = data.get('user')
                return True, data
            else:
                return False, response.json().get('error', 'Token je neplatný nebo expirovaný')
        except Exception as e:
            return False, str(e)
    
    def get_quizzes(self, category=None, difficulty=None):
        """Získání seznamu kvízů."""
        try:
            params = {}
            if category:
                params['category'] = category
            if difficulty:
                params['difficulty'] = difficulty
            
            response = self.session.get(
                f"{self.base_url}/api/quizzes",
                params=params
            )
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []
    
    def get_quiz_questions(self, quiz_id):
        """Získání otázek kvízu."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/quiz/{quiz_id}/questions"
            )
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None
    
    def submit_quiz(self, quiz_id, answers, time_spent):
        """Odeslání výsledků kvízu."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/quiz/{quiz_id}/submit",
                json={
                    'answers': answers,
                    'time_spent': time_spent
                }
            )
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None


class LoginWidget(QWidget):
    """Widget pro přihlášení."""
    
    login_successful = pyqtSignal(dict)
    
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # Logo/Název
        title = QLabel("🧠 Braniac")
        title.setFont(QFont('Segoe UI', 32, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Přihlaste se ke svému účtu")
        subtitle.setStyleSheet("color: #64748b; font-size: 16px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(30)
        
        # Formulář
        form_container = QWidget()
        form_container.setMaximumWidth(400)
        form_layout = QVBoxLayout(form_container)
        
        # Email
        email_label = QLabel("Email")
        form_layout.addWidget(email_label)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("vas@email.cz")
        form_layout.addWidget(self.email_input)
        
        form_layout.addSpacing(10)
        
        # Heslo
        password_label = QLabel("Heslo")
        form_layout.addWidget(password_label)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Vaše heslo")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.handle_login)
        form_layout.addWidget(self.password_input)
        
        form_layout.addSpacing(20)
        
        # Tlačítko
        self.login_btn = QPushButton("Přihlásit se")
        self.login_btn.clicked.connect(self.handle_login)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        form_layout.addWidget(self.login_btn)
        
        # Chybová zpráva
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #ef4444;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        form_layout.addWidget(self.error_label)
        
        layout.addWidget(form_container, alignment=Qt.AlignCenter)
        
        # Info
        info = QLabel("Pro vytvoření účtu použijte webovou aplikaci")
        info.setStyleSheet("color: #64748b; font-size: 12px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        self.setLayout(layout)
    
    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        if not email or not password:
            self.show_error("Vyplňte email a heslo")
            return
        
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Přihlašování...")
        
        success, result = self.api.login(email, password)
        
        if success:
            self.login_successful.emit(result)
        else:
            self.show_error(result if isinstance(result, str) else "Přihlášení selhalo")
        
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Přihlásit se")
    
    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()


class QuizListWidget(QWidget):
    """Widget pro výběr kvízu."""
    
    quiz_selected = pyqtSignal(dict)
    logout_requested = pyqtSignal()
    
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self.quizzes = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("📚 Vyberte kvíz")
        title.setFont(QFont('Segoe UI', 24, QFont.Bold))
        header.addWidget(title)
        
        header.addStretch()
        
        # Uživatel info
        self.user_label = QLabel()
        self.user_label.setStyleSheet("color: #64748b;")
        header.addWidget(self.user_label)
        
        logout_btn = QPushButton("Odhlásit")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #334155;
                color: #f8fafc;
                padding: 8px 16px;
            }
            QPushButton:hover {
                border-color: #6366f1;
                color: #6366f1;
            }
            QPushButton:pressed {
                border-color: #4338ca;
                color: #4338ca;
            }
        """)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.clicked.connect(self.logout_requested.emit)
        header.addWidget(logout_btn)
        
        layout.addLayout(header)
        
        # Filtry
        filters = QHBoxLayout()
        
        self.category_combo = QComboBox()
        self.category_combo.setCursor(Qt.PointingHandCursor)
        self.category_combo.addItem("Všechny kategorie", "")
        self.category_combo.currentIndexChanged.connect(self.load_quizzes)
        filters.addWidget(self.category_combo)
        
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.setCursor(Qt.PointingHandCursor)
        self.difficulty_combo.addItem("Všechny obtížnosti", "")
        self.difficulty_combo.addItem("Lehký", "easy")
        self.difficulty_combo.addItem("Střední", "medium")
        self.difficulty_combo.addItem("Těžký", "hard")
        self.difficulty_combo.currentIndexChanged.connect(self.load_quizzes)
        filters.addWidget(self.difficulty_combo)
        
        filters.addStretch()
        
        refresh_btn = QPushButton("🔄 Obnovit")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.load_quizzes)
        filters.addWidget(refresh_btn)
        
        layout.addLayout(filters)
        
        # Seznam kvízů
        self.quiz_list = QListWidget()
        self.quiz_list.itemDoubleClicked.connect(self.on_quiz_selected)
        layout.addWidget(self.quiz_list)
        
        # Tlačítko pro hraní
        self.play_btn = QPushButton("🎮 Hrát vybraný kvíz")
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.play_selected)
        self.quiz_list.itemSelectionChanged.connect(
            lambda: self.play_btn.setEnabled(len(self.quiz_list.selectedItems()) > 0)
        )
        layout.addWidget(self.play_btn)
        
        self.setLayout(layout)
    
    def set_user(self, user):
        self.user_label.setText(f"👤 {user.get('name', 'Uživatel')}")
    
    def load_quizzes(self):
        category = self.category_combo.currentData()
        difficulty = self.difficulty_combo.currentData()
        
        self.quizzes = self.api.get_quizzes(category, difficulty)
        self.quiz_list.clear()
        
        # Aktualizace kategorií
        categories = set()
        for quiz in self.quizzes:
            categories.add(quiz.get('category', ''))
        
        # Přidání kvízů do seznamu
        for quiz in self.quizzes:
            difficulty_text = {
                'easy': '🟢 Lehký',
                'medium': '🟡 Střední',
                'hard': '🔴 Těžký'
            }.get(quiz.get('difficulty', ''), quiz.get('difficulty', ''))
            
            item_text = f"{quiz['name']}\n" \
                       f"📁 {quiz.get('category', 'Bez kategorie')} | " \
                       f"{difficulty_text} | " \
                       f"📝 {quiz.get('question_count', 0)} otázek"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, quiz)
            self.quiz_list.addItem(item)
    
    def on_quiz_selected(self, item):
        quiz = item.data(Qt.UserRole)
        if quiz:
            self.quiz_selected.emit(quiz)
    
    def play_selected(self):
        items = self.quiz_list.selectedItems()
        if items:
            self.on_quiz_selected(items[0])


class QuizGameWidget(QWidget):
    """Widget pro hraní kvízu."""
    
    game_finished = pyqtSignal(dict)
    back_requested = pyqtSignal()
    
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self.quiz = None
        self.questions = []
        self.current_index = 0
        self.answers = []
        self.time_remaining = 0
        self.total_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.answer_buttons = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        
        self.timer_label = QLabel("30")
        self.timer_label.setFont(QFont('Segoe UI', 24, QFont.Bold))
        self.timer_label.setStyleSheet("color: #6366f1;")
        header.addWidget(self.timer_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        header.addWidget(self.progress_bar, 1)
        
        self.question_counter = QLabel("1/10")
        self.question_counter.setFont(QFont('Segoe UI', 16))
        header.addWidget(self.question_counter)
        
        layout.addLayout(header)
        
        # Otázka
        self.question_label = QLabel("Načítání...")
        self.question_label.setFont(QFont('Segoe UI', 20))
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignCenter)
        self.question_label.setStyleSheet("padding: 30px;")
        layout.addWidget(self.question_label)
        
        # Odpovědi
        answers_layout = QGridLayout()
        answers_layout.setSpacing(15)
        
        labels = ['A', 'B', 'C', 'D']
        for i in range(4):
            btn = QPushButton(f"{labels[i]}: ")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    border: 2px solid #334155;
                    border-radius: 8px;
                    padding: 20px;
                    text-align: left;
                    font-size: 16px;
                }
                QPushButton:hover {
                    border-color: #6366f1;
                    background-color: rgba(99, 102, 241, 0.1);
                }
                QPushButton:pressed {
                    border-color: #4338ca;
                    background-color: rgba(99, 102, 241, 0.25);
                }
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self.select_answer(idx))
            answers_layout.addWidget(btn, i // 2, i % 2)
            self.answer_buttons.append(btn)
        
        layout.addLayout(answers_layout)
        
        layout.addStretch()
        
        # Tlačítko zpět
        back_btn = QPushButton("← Ukončit kvíz")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #334155;
                color: #f8fafc;
            }
            QPushButton:hover {
                border-color: #6366f1;
                color: #6366f1;
            }
            QPushButton:pressed {
                border-color: #4338ca;
                color: #4338ca;
            }
        """)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.confirm_quit)
        layout.addWidget(back_btn)
        
        self.setLayout(layout)
    
    def start_quiz(self, quiz):
        self.quiz = quiz
        self.current_index = 0
        self.answers = []
        self.total_time = 0
        
        # Získání otázek
        data = self.api.get_quiz_questions(quiz['id'])
        if data and 'questions' in data:
            self.questions = data['questions']
            self.time_limit = data.get('time_limit', 30)
            self.show_question(0)
        else:
            QMessageBox.warning(self, "Chyba", "Nepodařilo se načíst otázky.")
            self.back_requested.emit()
    
    def show_question(self, index):
        if index >= len(self.questions):
            self.finish_quiz()
            return
        
        self.current_index = index
        question = self.questions[index]
        
        # Aktualizace UI
        self.question_label.setText(question['text'])
        self.question_counter.setText(f"{index + 1}/{len(self.questions)}")
        self.progress_bar.setValue(int((index + 1) / len(self.questions) * 100))
        
        # Odpovědi
        labels = ['A', 'B', 'C', 'D']
        for i, btn in enumerate(self.answer_buttons):
            if i < len(question['answers']):
                btn.setText(f"{labels[i]}: {question['answers'][i]['text']}")
                btn.show()
                btn.setEnabled(True)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1e293b;
                        border: 2px solid #334155;
                        border-radius: 8px;
                        padding: 20px;
                        text-align: left;
                        font-size: 16px;
                    }
                    QPushButton:hover {
                        border-color: #6366f1;
                        background-color: rgba(99, 102, 241, 0.1);
                    }
                    QPushButton:pressed {
                        border-color: #4338ca;
                        background-color: rgba(99, 102, 241, 0.25);
                    }
                """)
            else:
                btn.hide()
        
        # Spuštění časovače
        self.time_remaining = self.time_limit
        self.timer_label.setText(str(self.time_remaining))
        self.timer_label.setStyleSheet("color: #6366f1;")
        self.timer.start(1000)
    
    def update_timer(self):
        self.time_remaining -= 1
        self.timer_label.setText(str(self.time_remaining))
        
        if self.time_remaining <= 5:
            self.timer_label.setStyleSheet("color: #ef4444;")
        elif self.time_remaining <= 10:
            self.timer_label.setStyleSheet("color: #f59e0b;")
        
        if self.time_remaining <= 0:
            self.timer.stop()
            # Timeout - bez odpovědi
            self.answers.append({
                'question_id': self.questions[self.current_index]['id'],
                'answer_id': None
            })
            self.total_time += self.time_limit
            self.show_question(self.current_index + 1)
    
    def select_answer(self, index):
        self.timer.stop()
        time_spent = self.time_limit - self.time_remaining
        self.total_time += time_spent
        
        question = self.questions[self.current_index]
        answer_id = question['answers'][index]['id'] if index < len(question['answers']) else None
        
        self.answers.append({
            'question_id': question['id'],
            'answer_id': answer_id
        })
        
        # Vizuální feedback
        for btn in self.answer_buttons:
            btn.setEnabled(False)
        
        self.answer_buttons[index].setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.3);
                border: 2px solid #6366f1;
                border-radius: 8px;
                padding: 20px;
                text-align: left;
                font-size: 16px;
            }
        """)
        
        # Další otázka po krátké pauze
        QTimer.singleShot(300, lambda: self.show_question(self.current_index + 1))
    
    def finish_quiz(self):
        self.timer.stop()
        
        # Odeslání výsledků
        result = self.api.submit_quiz(self.quiz['id'], self.answers, self.total_time)
        
        if result:
            self.game_finished.emit(result)
        else:
            QMessageBox.warning(self, "Chyba", "Nepodařilo se odeslat výsledky.")
            self.back_requested.emit()
    
    def confirm_quit(self):
        reply = QMessageBox.question(
            self, 'Ukončit kvíz',
            'Opravdu chcete ukončit kvíz? Váš postup nebude uložen.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.timer.stop()
            self.back_requested.emit()


class ResultsWidget(QWidget):
    """Widget pro zobrazení výsledků."""
    
    back_requested = pyqtSignal()
    replay_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.last_result = None
        self.quiz_name = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # Titul
        title = QLabel("🎉 Výsledky")
        title.setFont(QFont('Segoe UI', 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Skóre
        self.score_label = QLabel("0%")
        self.score_label.setFont(QFont('Segoe UI', 64, QFont.Bold))
        self.score_label.setStyleSheet("color: #6366f1;")
        self.score_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.score_label)
        
        # Detaily
        self.details_label = QLabel()
        self.details_label.setStyleSheet("color: #94a3b8; font-size: 16px;")
        self.details_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.details_label)
        
        layout.addSpacing(20)
        
        # Seznam odpovědí
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setMaximumHeight(300)
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_scroll.setWidget(self.results_container)
        layout.addWidget(self.results_scroll)
        
        layout.addSpacing(20)
        
        # Tlačítka
        buttons = QHBoxLayout()
        buttons.setAlignment(Qt.AlignCenter)
        
        back_btn = QPushButton("← Zpět na seznam")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #334155;
                color: #f8fafc;
            }
            QPushButton:hover {
                border-color: #6366f1;
                color: #6366f1;
            }
            QPushButton:pressed {
                border-color: #4338ca;
                color: #4338ca;
            }
        """)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.back_requested.emit)
        buttons.addWidget(back_btn)
        
        export_btn = QPushButton("💾 Exportovat výsledky")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #334155;
                color: #f8fafc;
            }
            QPushButton:hover {
                border-color: #6366f1;
                color: #6366f1;
            }
            QPushButton:pressed {
                border-color: #4338ca;
                color: #4338ca;
            }
        """)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self.export_results)
        buttons.addWidget(export_btn)
        
        replay_btn = QPushButton("🔄 Hrát znovu")
        replay_btn.setCursor(Qt.PointingHandCursor)
        replay_btn.clicked.connect(self.replay_requested.emit)
        buttons.addWidget(replay_btn)
        
        layout.addLayout(buttons)
        
        self.setLayout(layout)
    
    def show_results(self, result, quiz_name=None):
        self.last_result = result
        self.quiz_name = quiz_name or 'kviz'
        self.score_label.setText(f"{result.get('percentage', 0)}%")
        self.details_label.setText(
            f"{result.get('score', 0)} z {result.get('max_score', 0)} správných odpovědí | "
            f"Čas: {result.get('time_spent', 0)} sekund"
        )
        
        # Vyčištění předchozích výsledků
        for i in reversed(range(self.results_layout.count())):
            self.results_layout.itemAt(i).widget().deleteLater()
        
        # Zobrazení odpovědí
        for i, item in enumerate(result.get('results', [])):
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {'rgba(34, 197, 94, 0.1)' if item['is_correct'] else 'rgba(239, 68, 68, 0.1)'};
                    border-left: 4px solid {'#22c55e' if item['is_correct'] else '#ef4444'};
                    border-radius: 8px;
                    padding: 10px;
                }}
            """)
            
            frame_layout = QVBoxLayout(frame)
            
            q_label = QLabel(f"{i + 1}. {item.get('question_text', '')}")
            q_label.setWordWrap(True)
            q_label.setStyleSheet("font-weight: bold;")
            frame_layout.addWidget(q_label)
            
            answer_text = item.get('selected_answer_text') or 'Bez odpovědi'
            a_label = QLabel(f"Vaše odpověď: {answer_text}")
            a_label.setStyleSheet("color: #94a3b8;")
            frame_layout.addWidget(a_label)
            
            if not item['is_correct']:
                correct = QLabel(f"Správná odpověď: {item.get('correct_answer_text', '')}")
                correct.setStyleSheet("color: #22c55e;")
                frame_layout.addWidget(correct)
            
            self.results_layout.addWidget(frame)
    
    def export_results(self):
        """Export výsledků do textového souboru."""
        if not self.last_result:
            return
        
        result = self.last_result
        now = datetime.now()
        date_str = now.strftime('%d.%m.%Y')
        time_str = now.strftime('%H:%M')
        
        text = f"Výsledky kvízu: {self.quiz_name}\n"
        text += f"Datum: {date_str} {time_str}\n"
        text += f"{'=' * 40}\n\n"
        text += f"Skóre: {result.get('score', 0)} / {result.get('max_score', 0)} ({result.get('percentage', 0)}%)\n"
        text += f"Čas: {result.get('time_spent', 0)} sekund\n\n"
        text += f"{'=' * 40}\n"
        text += "Přehled odpovědí:\n\n"
        
        for i, item in enumerate(result.get('results', [])):
            text += f"{i + 1}. {item.get('question_text', '')}\n"
            answer_text = item.get('selected_answer_text') or 'Bez odpovědi'
            text += f"   Vaše odpověď: {answer_text}\n"
            if item.get('is_correct'):
                text += "   ✓ Správně\n"
            else:
                text += f"   ✗ Špatně — Správná odpověď: {item.get('correct_answer_text', '')}\n"
            text += "\n"
        
        import unicodedata
        import re
        safe_name = unicodedata.normalize('NFD', self.quiz_name)
        safe_name = safe_name.encode('ascii', 'ignore').decode('ascii')
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', safe_name)
        safe_name = re.sub(r'_+', '_', safe_name).strip('_').lower()
        file_date = now.strftime('%Y-%m-%d')
        default_name = f"vysledky_{safe_name}_{file_date}.txt"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exportovat výsledky", default_name,
            "Textové soubory (*.txt);;Všechny soubory (*)"
        )
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)


class CustomTitleBar(QWidget):
    """Vlastní titulková lišta."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._drag_pos = None
        self.setFixedHeight(40)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#1e293b"))
        self.setPalette(palette)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(0)

        # Icon + title
        icon_label = QLabel("🧠")
        icon_label.setStyleSheet("font-size: 18px; background: transparent;")
        layout.addWidget(icon_label)

        title_label = QLabel("Braniac")
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #f8fafc;
            padding-left: 6px;
            background: transparent;
        """)
        layout.addWidget(title_label)
        layout.addStretch()

        # Window control buttons
        btn_style_base = """
            QPushButton {{
                background-color: transparent;
                color: #94a3b8;
                border: none;
                border-radius: 0px;
                font-size: 16px;
                padding: 0px;
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: {hover_fg};
            }}
        """

        self.btn_minimize = QPushButton("─")
        self.btn_minimize.setStyleSheet(btn_style_base.format(hover_bg="#334155", hover_fg="#f8fafc"))
        self.btn_minimize.clicked.connect(self._minimize)

        self.btn_maximize = QPushButton("☐")
        self.btn_maximize.setStyleSheet(btn_style_base.format(hover_bg="#334155", hover_fg="#f8fafc"))
        self.btn_maximize.clicked.connect(self._toggle_maximize)

        self.btn_close = QPushButton("✕")
        self.btn_close.setStyleSheet(btn_style_base.format(hover_bg="#ef4444", hover_fg="#ffffff"))
        self.btn_close.clicked.connect(self._close)

        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)

    def _minimize(self):
        self.parent_window.showMinimized()

    def _toggle_maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()

    def _close(self):
        self.parent_window.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.parent_window.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_maximize()


class MainWindow(QMainWindow):
    """Hlavní okno aplikace."""
    
    def __init__(self, target_quiz_id=None, sso_token=None):
        super().__init__()
        self.api = APIClient(API_BASE_URL)
        self.current_quiz = None
        self.target_quiz_id = target_quiz_id
        self.sso_token = sso_token
        self.init_ui()
        
        # Pokud máme SSO token, automaticky se přihlásíme
        if self.sso_token:
            QTimer.singleShot(100, self._auto_login_with_token)
    
    def init_ui(self):
        self.setWindowTitle("Braniac - Desktop")
        self.setMinimumSize(900, 700)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet(StyleSheet.MAIN)
        
        # Centrální widget se stacked layoutem
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Custom title bar
        self.title_bar = CustomTitleBar(self)
        layout.addWidget(self.title_bar)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #334155; border: none;")
        layout.addWidget(separator)
        
        # Content area with padding
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        
        self.stack = QStackedWidget()
        
        # Login widget
        self.login_widget = LoginWidget(self.api)
        self.login_widget.login_successful.connect(self.on_login_success)
        self.stack.addWidget(self.login_widget)
        
        # Quiz list widget
        self.quiz_list_widget = QuizListWidget(self.api)
        self.quiz_list_widget.quiz_selected.connect(self.start_quiz)
        self.quiz_list_widget.logout_requested.connect(self.logout)
        self.stack.addWidget(self.quiz_list_widget)
        
        # Quiz game widget
        self.quiz_game_widget = QuizGameWidget(self.api)
        self.quiz_game_widget.game_finished.connect(self.show_results)
        self.quiz_game_widget.back_requested.connect(self.show_quiz_list)
        self.stack.addWidget(self.quiz_game_widget)
        
        # Results widget
        self.results_widget = ResultsWidget()
        self.results_widget.back_requested.connect(self.show_quiz_list)
        self.results_widget.replay_requested.connect(self.replay_quiz)
        self.stack.addWidget(self.results_widget)
        
        content_layout.addWidget(self.stack)
        layout.addWidget(content_widget)
    
    def _auto_login_with_token(self):
        """Automatické přihlášení pomocí SSO tokenu z webu."""
        success, result = self.api.token_login(self.sso_token)
        self.sso_token = None  # Použít jen jednou
        
        if success:
            self.on_login_success(result)
        else:
            QMessageBox.warning(
                self, 'Automatické přihlášení selhalo',
                'Token je neplatný nebo expirovaný. Přihlaste se prosím ručně.'
            )
    
    def on_login_success(self, data):
        user = data.get('user', {})
        self.quiz_list_widget.set_user(user)
        self.quiz_list_widget.load_quizzes()
        self.stack.setCurrentWidget(self.quiz_list_widget)
        
        # Pokud byl zadán konkrétní kvíz, spustit ho automaticky
        if self.target_quiz_id is not None:
            self._auto_start_quiz(self.target_quiz_id)
            self.target_quiz_id = None  # Použít jen jednou
    
    def _auto_start_quiz(self, quiz_id):
        """Automaticky spustí kvíz podle ID."""
        for quiz in self.quiz_list_widget.quizzes:
            if quiz.get('id') == quiz_id:
                self.start_quiz(quiz)
                return
        QMessageBox.warning(self, 'Kvíz nenalezen', f'Kvíz s ID {quiz_id} nebyl nalezen.')
    
    def logout(self):
        self.api.user = None
        self.stack.setCurrentWidget(self.login_widget)
    
    def start_quiz(self, quiz):
        self.current_quiz = quiz
        self.quiz_game_widget.start_quiz(quiz)
        self.stack.setCurrentWidget(self.quiz_game_widget)
    
    def show_results(self, result):
        quiz_name = self.current_quiz.get('name', 'kviz') if self.current_quiz else 'kviz'
        self.results_widget.show_results(result, quiz_name)
        self.stack.setCurrentWidget(self.results_widget)
    
    def show_quiz_list(self):
        self.quiz_list_widget.load_quizzes()
        self.stack.setCurrentWidget(self.quiz_list_widget)
    
    def replay_quiz(self):
        if self.current_quiz:
            self.start_quiz(self.current_quiz)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--quiz-id', type=int, default=None, help='ID kvízu pro přímé spuštění')
    parser.add_argument('--token', type=str, default=None, help='SSO token pro automatické přihlášení')
    args, unknown = parser.parse_known_args()
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Tmavé téma
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(15, 23, 42))
    palette.setColor(QPalette.WindowText, QColor(248, 250, 252))
    palette.setColor(QPalette.Base, QColor(30, 41, 59))
    palette.setColor(QPalette.AlternateBase, QColor(15, 23, 42))
    palette.setColor(QPalette.Text, QColor(248, 250, 252))
    palette.setColor(QPalette.Button, QColor(99, 102, 241))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.Highlight, QColor(99, 102, 241))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = MainWindow(target_quiz_id=args.quiz_id, sso_token=args.token)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()