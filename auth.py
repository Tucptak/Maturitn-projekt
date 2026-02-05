"""
Autentizační routy a logika.
"""
import os
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from database import db
from models import User

auth_bp = Blueprint('auth', __name__)
login_manager = LoginManager()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    """Zkontroluje, zda je soubor povoleného typu."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(f):
    """Dekorátor pro povinné admin oprávnění."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Pro přístup k této stránce potřebujete administrátorská oprávnění.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    """Načte uživatele podle ID."""
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    """Handler pro nepřihlášené uživatele."""
    flash('Pro přístup k této stránce se musíte přihlásit.', 'warning')
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Přihlášení uživatele."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Vyplňte prosím email a heslo.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Vítejte zpět, {user.name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Neplatný email nebo heslo.', 'error')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registrace nového uživatele."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Validace
        errors = []
        if not name or len(name) < 2:
            errors.append('Jméno musí mít alespoň 2 znaky.')
        if not email or '@' not in email:
            errors.append('Zadejte platný email.')
        if not password or len(password) < 6:
            errors.append('Heslo musí mít alespoň 6 znaků.')
        if password != password_confirm:
            errors.append('Hesla se neshodují.')
        
        if User.query.filter_by(email=email).first():
            errors.append('Tento email je již zaregistrován.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html')
        
        # Vytvoření uživatele
        user = User(name=name, email=email)
        user.set_password(password)
        
        # První uživatel bude admin
        if User.query.count() == 0:
            user.role = 'admin'
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registrace úspěšná! Nyní se můžete přihlásit.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Odhlášení uživatele."""
    logout_user()
    flash('Byli jste úspěšně odhlášeni.', 'info')
    return redirect(url_for('index'))


@auth_bp.route('/profile')
@login_required
def profile():
    """Profil uživatele."""
    stats = current_user.get_stats()
    recent_games = current_user.game_results[-10:][::-1]  # Posledních 10 her
    return render_template('profile.html', stats=stats, recent_games=recent_games)


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Úprava profilu uživatele."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        
        if not name or len(name) < 2:
            flash('Jméno musí mít alespoň 2 znaky.', 'error')
            return render_template('edit_profile.html')
        
        current_user.name = name
        
        # Zpracování avataru
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"user_{current_user.id}_{file.filename}")
                filepath = os.path.join('static', 'assets', filename)
                file.save(filepath)
                current_user.avatar = filename
        
        db.session.commit()
        flash('Profil byl úspěšně aktualizován.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('edit_profile.html')


@auth_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Změna hesla."""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not current_user.check_password(current_password):
        flash('Současné heslo není správné.', 'error')
        return redirect(url_for('auth.profile'))
    
    if len(new_password) < 6:
        flash('Nové heslo musí mít alespoň 6 znaků.', 'error')
        return redirect(url_for('auth.profile'))
    
    if new_password != confirm_password:
        flash('Nová hesla se neshodují.', 'error')
        return redirect(url_for('auth.profile'))
    
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('Heslo bylo úspěšně změněno.', 'success')
    return redirect(url_for('auth.profile'))
