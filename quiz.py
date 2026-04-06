"""
Routy pro správu a hraní kvízů.

Největší modul aplikace – obsahuje:
  - Výpis kvízů s filtrováním (kategorie, obtížnost)
  - Detail kvízu a detail pokusu (attempt)
  - Spuštění desktopové aplikace s SSO tokenem (play_quiz)
  - API endpoint pro získání otázek (quiz.js ho volá přes fetch)
  - Odeslání a vyhodnocení výsledků (submit_quiz)
  - Import kvízu z CSV souboru (import_csv)
  - CRUD operace: vytvoření, úprava, smazání kvízu a otázek
  - Žebříček (leaderboard) s více režimy
  - Mini-profil hráče pro leaderboard hover
  - Stránka "Moje kvízy"

Blueprint: quiz_bp (bez URL prefixu)
Propojeno s: quiz.js (frontendová logika hraní), api.py (desktopová verze)
"""
import csv
import io
import subprocess
import sys
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database import db
from models import Quiz, Question, Answer, GameResult, UserAnswer, User, Achievement, UserAchievement, pct

quiz_bp = Blueprint('quiz', __name__)


@quiz_bp.route('/quizzes')
def list_quizzes():
    """Seznam všech kvízů s volitelným filtrem podle kategorie a obtížnosti.
    
    Query parametry: ?category=X&difficulty=Y
    Šablona: templates/quizzes.html
    """
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')
    
    query = Quiz.query
    
    if category:
        query = query.filter_by(category=category)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    
    quizzes = query.order_by(Quiz.created_at.desc()).all()
    
    # Získání unikátních kategorií
    categories = db.session.query(Quiz.category).distinct().all()
    categories = [c[0] for c in categories]
    
    return render_template('quizzes.html', 
                         quizzes=quizzes, 
                         categories=categories,
                         selected_category=category,
                         selected_difficulty=difficulty)


@quiz_bp.route('/quiz/<int:quiz_id>')
def quiz_detail(quiz_id):
    """Detail kvízu."""
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('quiz_detail.html', quiz=quiz)


@quiz_bp.route('/attempt/<int:game_id>')
@login_required
def attempt_detail(game_id):
    """Detail pokusu – shrnutí odpovědí po dohrání kvízu.
    
    Zobrazuje každou otázku, co uživatel zvolil a co bylo správně.
    Přístup má jen vlastník pokusu nebo admin.
    Šablona: templates/attempt_detail.html
    """
    game = GameResult.query.get_or_404(game_id)

    if game.user_id != current_user.id and not current_user.is_admin():
        flash('Nemáte oprávnění zobrazit tento pokus.', 'error')
        return redirect(url_for('auth.profile'))

    quiz = Quiz.query.get_or_404(game.quiz_id)

    # Build question details with user answers
    questions_detail = []
    for ua in game.user_answers:
        question = Question.query.get(ua.question_id)
        if not question:
            continue

        correct_answers = [a for a in question.answers if a.is_correct]
        chosen_answer = Answer.query.get(ua.answer_id) if ua.answer_id else None

        questions_detail.append({
            'question': question,
            'all_answers': question.answers,
            'chosen_answer': chosen_answer,
            'chosen_text': ua.answer_text,
            'correct_answers': correct_answers,
            'is_correct': ua.is_correct
        })

    correct_count = sum(1 for q in questions_detail if q['is_correct'])
    total_count = len(questions_detail)
    percentage = round(correct_count / total_count * 100) if total_count > 0 else 0

    return render_template('attempt_detail.html',
                           game=game,
                           quiz=quiz,
                           questions=questions_detail,
                           correct_count=correct_count,
                           total_count=total_count,
                           percentage=percentage)


# Globální reference na běžící desktopovou aplikaci.
# Umožňuje ukončit předchozí instanci před spuštěním nové.
_desktop_process = None

@quiz_bp.route('/quiz/<int:quiz_id>/play')
@login_required
def play_quiz(quiz_id):
    """Spustí desktopovou aplikaci (desktop_app.py) pro hraní kvízu.
    
    Tok:
      1. Ukončí případnou běžící instanci desktopové aplikace
      2. Vygeneruje jednorázový SSO token (api.py: generate_sso_token)
      3. Spustí desktop_app.py jako subprocess s parametry --quiz-id a --token
      4. Desktop app se připojí na /api/auth/token a ověří token
    
    SSO token expiruje za 2 minuty a je jednorázový (viz api.py).
    """
    global _desktop_process
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if not quiz.questions:
        flash('Tento kvíz nemá žádné otázky.', 'warning')
        return redirect(url_for('quiz.quiz_detail', quiz_id=quiz_id))
    
    try:
        # Ukončit předchozí instanci desktopové aplikace, pokud běží
        if _desktop_process is not None and _desktop_process.poll() is None:
            _desktop_process.terminate()
            try:
                _desktop_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _desktop_process.kill()

        # Vygenerování SSO tokenu pro automatické přihlášení v desktopové aplikaci
        from api import generate_sso_token
        token = generate_sso_token(current_user.id)
        
        desktop_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'desktop_app.py')
        _desktop_process = subprocess.Popen([
            sys.executable, desktop_app_path,
            '--quiz-id', str(quiz_id),
            '--token', token
        ])
        flash('Desktopová aplikace se spouští... Budete automaticky přihlášeni.', 'success')
    except Exception as e:
        flash(f'Nepodařilo se spustit desktopovou aplikaci: {str(e)}', 'error')
    
    return redirect(url_for('quiz.quiz_detail', quiz_id=quiz_id))


@quiz_bp.route('/quiz/<int:quiz_id>/questions', methods=['GET'])
@login_required
def get_quiz_questions(quiz_id):
    """API endpoint pro získání otázek kvízu (JSON).
    
    Volá ho quiz.js přes fetch() při inicializaci hry.
    Vrací: quiz_id, quiz_name, time_limit, questions[{id, text, answers[{id, text}]}]
    Odpovědi neobsahují is_correct – správnost se kontroluje až při submit.
    """
    quiz = Quiz.query.get_or_404(quiz_id)
    
    questions_data = []
    for question in quiz.questions:
        answers_data = [
            {'id': a.id, 'text': a.text}
            for a in question.answers
        ]
        questions_data.append({
            'id': question.id,
            'text': question.text,
            'answers': answers_data
        })
    
    return jsonify({
        'quiz_id': quiz.id,
        'quiz_name': quiz.name,
        'time_limit': quiz.time_limit,
        'questions': questions_data
    })


@quiz_bp.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    """Odeslání výsledků kvízu (voláno z quiz.js přes fetch POST s JSON).
    
    Tok:
      1. Přijme JSON s odpověd'mi a časem {answers: [...], time_spent}
      2. Vytvoří GameResult záznam v DB
      3. Pro každou odpověď zkontroluje správnost a uloží UserAnswer
      4. Zkontroluje achievementy (check_achievements z achievements.py)
      5. Vrátí JSON s výsledky, skóre a případně novými achievementy
    
    CSRF token se přenáší přes hlavičku X-CSRFToken (viz quiz.js: finishQuiz).
    """
    quiz = Quiz.query.get_or_404(quiz_id)
    # data = JSON z quiz.js:finishQuiz() → fetch POST s {answers: [...], time_spent}
    data = request.get_json()
    
    if not data or 'answers' not in data:
        return jsonify({'error': 'Neplatná data'}), 400
    
    # answers = [{question_id: N, answer_id: N}, ...] z quiz.js:userAnswers[]
    answers = data['answers']
    time_spent = data.get('time_spent', 0)  # celkový čas z quiz.js:totalTimeSpent
    
    # Minimální čas 0.5s na otázku – ochrana proti příliš rychlému odeslání
    min_time = max(1, int(len(quiz.questions) * 0.5))
    if time_spent < min_time:
        time_spent = min_time

    # Výpočet skóre – počítá správné odpovědi
    score = 0
    max_score = len(quiz.questions)
    
    # Vytvoření záznamu o hře
    game_result = GameResult(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=0,
        max_score=max_score,
        time_spent=time_spent
    )
    db.session.add(game_result)
    # flush() získá ID záznamu bez commitování transakce – potřebujeme ID pro UserAnswer
    db.session.flush()  # Pro získání ID
    
    # Zpracování odpovědí – pro každou otázku najde správnou odpověď a porovná
    results = []
    for answer_data in answers:
        question_id = answer_data.get('question_id')
        answer_id = answer_data.get('answer_id')
        
        question = Question.query.get(question_id)
        if not question or question.quiz_id != quiz_id:
            continue
        
        # Kontrola správnosti
        is_correct = False
        correct_answer = None
        selected_answer = None
        
        for ans in question.answers:
            if ans.is_correct:
                correct_answer = ans
            if ans.id == answer_id:
                selected_answer = ans
                if ans.is_correct:
                    is_correct = True
                    score += 1
        
        # Uložení odpovědi uživatele
        user_answer = UserAnswer(
            game_id=game_result.id,
            question_id=question_id,
            answer_id=answer_id,
            is_correct=is_correct
        )
        db.session.add(user_answer)
        
        results.append({
            'question_id': question_id,
            'question_text': question.text,
            'selected_answer_id': answer_id,
            'selected_answer_text': selected_answer.text if selected_answer else None,
            'correct_answer_id': correct_answer.id if correct_answer else None,
            'correct_answer_text': correct_answer.text if correct_answer else None,
            'is_correct': is_correct
        })
    
    # Aktualizace skóre
    game_result.score = score
    db.session.commit()
    
    # check_achievements() → achievements.py:check_achievements() → vrátí list Achievement objektů
    # Každý Achievement má: name, description, icon (SVG), tier (bronze/silver/gold)
    from achievements import check_achievements
    new_achievements = check_achievements(current_user)
    # Převede Achievement objekty na dict pro JSON odpověď → quiz.js:showResults()
    achievements_popup = [
        {
            'name': a.name,
            'description': a.description,
            'icon': a.icon,     # název SVG souboru v static/assets/achievements/
            'tier': a.tier,     # 'bronze'/'silver'/'gold' – určuje barvu toastu v main.js
        }
        for a in new_achievements
    ]
    
    # Výsledek se vrátí do quiz.js:finishQuiz() → result.json()
    # quiz.js pak volá showResults(result) + showAchievementQueue(result.new_achievements)
    return jsonify({
        'success': True,
        'score': score,
        'max_score': max_score,
        'percentage': pct((score / max_score * 100) if max_score > 0 else 0),
        'time_spent': time_spent,
        'results': results,
        'new_achievements': achievements_popup
    })


@quiz_bp.route('/quiz/import-csv', methods=['POST'])
@login_required
def import_csv():
    """Import kvízu z CSV souboru.
    
    Formát CSV:
      - Volitelné metadata řádky: name, category, difficulty, time_limit (klíč, hodnota)
      - Hlavička: question, answer_a, answer_b, answer_c, answer_d, correct
      - Datové řádky: text otázky, 4 odpovědi, správná odpověď (A/B/C/D)
    
    Metadata priority: formulářová pole > CSV metadata > výchozí hodnoty.
    Limit velikosti: 1 MB. Podporuje UTF-8 (s BOM i bez) a Latin-1 fallback.
    """
    csv_file = request.files.get('csv_file')
    if not csv_file or not csv_file.filename:
        flash('Nebyl vybrán žádný soubor.', 'error')
        return redirect(url_for('quiz.create_quiz'))

    if not csv_file.filename.lower().endswith('.csv'):
        flash('Soubor musí být ve formátu CSV.', 'error')
        return redirect(url_for('quiz.create_quiz'))

    # Limit 1MB
    csv_file.seek(0, 2)
    size = csv_file.tell()
    csv_file.seek(0)
    if size > 1_048_576:
        flash('Soubor je příliš velký (max 1 MB).', 'error')
        return redirect(url_for('quiz.create_quiz'))

    # Read and decode
    raw = csv_file.read()
    # Handle UTF-8 BOM
    if raw[:3] == b'\xef\xbb\xbf':
        raw = raw[3:]
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('latin-1')

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    if len(rows) < 2:
        flash('CSV soubor musí obsahovat hlavičku a alespoň jeden řádek s otázkou.', 'error')
        return redirect(url_for('quiz.create_quiz'))

    # Extrakce metadat z řádků před hlavičkou otázek.
    # CSV může začínat řádky typu "name,Můj kvíz" před řádkem "question,..."
    csv_metadata = {}
    header_index = 0
    metadata_keys = {'name', 'category', 'difficulty', 'time_limit'}

    for i, row in enumerate(rows):
        if len(row) >= 1 and row[0].strip().lower() == 'question':
            header_index = i
            break
        if len(row) == 2 and row[0].strip().lower() in metadata_keys:
            csv_metadata[row[0].strip().lower()] = row[1].strip()

    data_rows = rows[header_index + 1:]

    # Parsování otázek z CSV řádků
    valid_correct = {'a': 0, 'b': 1, 'c': 2, 'd': 3}  # mapování písmena na index
    questions_data = []
    errors = []

    for i, row in enumerate(data_rows, start=2):
        if len(row) < 6:
            errors.append(f'Řádek {i}: nedostatek sloupců (potřeba 6, nalezeno {len(row)})')
            continue

        if len(row) > 6:
            # Extra sloupce – čárky v textu otázky; poslední sloupec = správná odpověď,
            # předchozí 4 = odpovědi, vše před = text otázky spojený zpět dohromady.
            correct_letter = row[-1].strip().lower()
            answers = [row[-5].strip(), row[-4].strip(), row[-3].strip(), row[-2].strip()]
            q_text = ','.join(row[:-5]).strip()
        else:
            q_text = row[0].strip()
            answers = [row[1].strip(), row[2].strip(), row[3].strip(), row[4].strip()]
            correct_letter = row[5].strip().lower()

        if not q_text:
            errors.append(f'Řádek {i}: prázdný text otázky')
            continue
        if any(not a for a in answers):
            errors.append(f'Řádek {i}: některá odpověď je prázdná')
            continue
        if correct_letter not in valid_correct:
            errors.append(f'Řádek {i}: neplatná správná odpověď "{row[5].strip()}" (povoleno A/B/C/D)')
            continue

        correct_idx = valid_correct[correct_letter]
        questions_data.append({
            'text': q_text,
            'answers': [
                {'text': answers[j], 'is_correct': j == correct_idx}
                for j in range(4)
            ]
        })

    if errors:
        flash('Chyby v CSV: ' + '; '.join(errors[:5]), 'error')
        if not questions_data:
            return redirect(url_for('quiz.create_quiz'))

    # Priorita metadat: formulář (uživatel vyplnil) > CSV > výchozí
    # Quiz metadata: form fields > CSV metadata > defaults
    name = request.form.get('name', '').strip()
    if not name or len(name) < 3:
        name = csv_metadata.get('name', '').strip()
    if not name or len(name) < 3:
        name = os.path.splitext(csv_file.filename)[0]
        if len(name) < 3:
            name = 'Importovaný kvíz'

    category = request.form.get('category', '').strip()
    if not category:
        category = csv_metadata.get('category', '').strip() or 'Všeobecné znalosti'

    difficulty = request.form.get('difficulty', '').strip()
    if difficulty not in ('easy', 'medium', 'hard'):
        difficulty = csv_metadata.get('difficulty', '').strip().lower()
    if difficulty not in ('easy', 'medium', 'hard'):
        difficulty = 'medium'

    time_limit = request.form.get('time_limit', 0, type=int)
    if time_limit < 5 or time_limit > 120:
        csv_tl = csv_metadata.get('time_limit', '')
        time_limit = int(csv_tl) if csv_tl.isdigit() and 5 <= int(csv_tl) <= 120 else 30

    # Vytvoření kvízu + otázek v jedné transakci – buď vše nebo nic
    # Create quiz + questions in single transaction
    quiz = Quiz(
        name=name,
        category=category,
        difficulty=difficulty,
        time_limit=time_limit,
        author_id=current_user.id
    )
    db.session.add(quiz)
    db.session.flush()

    for q_data in questions_data:
        question = Question(quiz_id=quiz.id, text=q_data['text'])
        db.session.add(question)
        db.session.flush()
        for ans in q_data['answers']:
            db.session.add(Answer(
                question_id=question.id,
                text=ans['text'],
                is_correct=ans['is_correct']
            ))

    db.session.commit()

    # check_achievements() po importu → může udělit 'Tvůrce' nebo 'Aktivní autor'
    from achievements import check_achievements
    new_achievements = check_achievements(current_user)
    # Flash s prefixem 'achievement:' → base.html Jinja šablona parsuje tento formát
    # a vyvolá JS showAchievementToast() z main.js pro zobrazení toastu
    for ach in new_achievements:
        flash(f'achievement:{ach.name}|{ach.icon}|{ach.tier}', 'achievement')

    flash(f'Kvíz byl importován s {len(questions_data)} otázkami.', 'success')
    return redirect(url_for('quiz.edit_quiz', quiz_id=quiz.id))


@quiz_bp.route('/quiz/create', methods=['GET', 'POST'])
@login_required
def create_quiz():
    """Vytvoření nového kvízu (pouze metadat – otázky se přidávají poté v edit_quiz).
    
    Po úspěšném vytvoření přesměruje na stránku úprav kvízu.
    Kontroluje achievementy po vytvoření (např. 'Tvůrce', 'Aktivní autor').
    Šablona: templates/quiz_create.html
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        difficulty = request.form.get('difficulty', 'medium')
        time_limit = request.form.get('time_limit', 30, type=int)
        
        # Validace
        if not name or len(name) < 3:
            flash('Název kvízu musí mít alespoň 3 znaky.', 'error')
            return render_template('quiz_create.html')
        
        if not category:
            flash('Zadejte kategorii kvízu.', 'error')
            return render_template('quiz_create.html')
        
        # Vytvoření kvízu
        quiz = Quiz(
            name=name,
            category=category,
            difficulty=difficulty,
            time_limit=time_limit,
            author_id=current_user.id
        )
        db.session.add(quiz)
        db.session.commit()
        
        # Kontrola achievementů po vytvoření kvízu → může udělit 'Tvůrce' (1 kvíz) nebo 'Aktivní autor' (3 kvízy)
        from achievements import check_achievements
        new_achievements = check_achievements(current_user)
        # Flash s prefixem 'achievement:' → base.html ho rozpozná a zobrazí toast (main.js)
        for ach in new_achievements:
            flash(f'achievement:{ach.name}|{ach.icon}|{ach.tier}', 'achievement')
        
        flash('Kvíz byl vytvořen! Nyní přidejte otázky.', 'success')
        return redirect(url_for('quiz.edit_quiz', quiz_id=quiz.id))
    
    return render_template('quiz_create.html')


@quiz_bp.route('/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_quiz(quiz_id):
    """Úprava kvízu – metadat a správa otázek.
    
    Přístup má pouze autor kvízu nebo admin.
    Otázky se přidávají/upravují/mažou přes AJAX (add_question, edit_question, delete_question).
    Šablona: templates/quiz_edit.html
    """
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kontrola oprávnění
    if quiz.author_id != current_user.id and not current_user.is_admin():
        flash('Nemáte oprávnění upravovat tento kvíz.', 'error')
        return redirect(url_for('quiz.list_quizzes'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        difficulty = request.form.get('difficulty', 'medium')
        time_limit = request.form.get('time_limit', 30, type=int)
        
        if name and len(name) >= 3:
            quiz.name = name
        if category:
            quiz.category = category
        quiz.difficulty = difficulty
        quiz.time_limit = time_limit
        
        db.session.commit()
        flash('Kvíz byl aktualizován.', 'success')
        return redirect(url_for('quiz.create_quiz'))
    
    return render_template('quiz_edit.html', quiz=quiz)


@quiz_bp.route('/quiz/<int:quiz_id>/add-question', methods=['POST'])
@login_required
def add_question(quiz_id):
    """Přidání otázky do kvízu (AJAX JSON endpoint).
    
    Očekává JSON: {text: '...', answers: [{text, is_correct}, ...]} (právě 4 odpovědi)
    """
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kontrola oprávnění
    if quiz.author_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Nemáte oprávnění'}), 403
    
    data = request.get_json()
    question_text = data.get('text', '').strip()
    answers_data = data.get('answers', [])
    
    if not question_text:
        return jsonify({'error': 'Text otázky je povinný'}), 400
    
    if len(answers_data) != 4:
        return jsonify({'error': 'Otázka musí mít přesně 4 odpovědi'}), 400
    
    # Kontrola, že alespoň jedna odpověď je správná
    has_correct = any(a.get('is_correct', False) for a in answers_data)
    if not has_correct:
        return jsonify({'error': 'Alespoň jedna odpověď musí být správná'}), 400
    
    # Vytvoření otázky
    question = Question(quiz_id=quiz_id, text=question_text)
    db.session.add(question)
    db.session.flush()
    
    # Vytvoření odpovědí
    for ans in answers_data:
        answer = Answer(
            question_id=question.id,
            text=ans.get('text', '').strip(),
            is_correct=ans.get('is_correct', False)
        )
        db.session.add(answer)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'question_id': question.id,
        'message': 'Otázka byla přidána'
    })


@quiz_bp.route('/question/<int:question_id>', methods=['DELETE'])
@login_required
def delete_question(question_id):
    """Smazání otázky."""
    question = Question.query.get_or_404(question_id)
    quiz = question.quiz
    
    # Kontrola oprávnění
    if quiz.author_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Nemáte oprávnění'}), 403
    
    db.session.delete(question)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Otázka byla smazána'})


@quiz_bp.route('/question/<int:question_id>', methods=['PUT'])
@login_required
def edit_question(question_id):
    """Úprava otázky (AJAX JSON endpoint).
    
    Staré odpovědi se smažou a nahradí novými (jednodušší než UPDATE každé).
    """
    question = Question.query.get_or_404(question_id)
    quiz = question.quiz
    
    # Kontrola oprávnění
    if quiz.author_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Nemáte oprávnění'}), 403
    
    data = request.get_json()
    question_text = data.get('text', '').strip()
    answers_data = data.get('answers', [])
    
    if not question_text:
        return jsonify({'error': 'Text otázky je povinný'}), 400
    
    if len(answers_data) != 4:
        return jsonify({'error': 'Otázka musí mít přesně 4 odpovědi'}), 400
    
    has_correct = any(a.get('is_correct', False) for a in answers_data)
    if not has_correct:
        return jsonify({'error': 'Alespoň jedna odpověď musí být správná'}), 400
    
    # Aktualizace textu otázky
    question.text = question_text
    
    # Smazání starých odpovědí a vytvoření nových – jednodušší než aktualizovat každou zvlášť
    Answer.query.filter_by(question_id=question.id).delete()
    
    for ans in answers_data:
        answer = Answer(
            question_id=question.id,
            text=ans.get('text', '').strip(),
            is_correct=ans.get('is_correct', False)
        )
        db.session.add(answer)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Otázka byla upravena'
    })


@quiz_bp.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    """Smazání kvízu."""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kontrola oprávnění
    if quiz.author_id != current_user.id and not current_user.is_admin():
        flash('Nemáte oprávnění smazat tento kvíz.', 'error')
        return redirect(url_for('quiz.list_quizzes'))
    
    db.session.delete(quiz)
    db.session.commit()
    
    flash('Kvíz byl smazán.', 'success')
    return redirect(url_for('quiz.list_quizzes'))


@quiz_bp.route('/leaderboard')
def leaderboard():
    """Žebříček nejlepších hráčů – více režimů, filtrování, časové období.
    
    Režimy (mode):
      - overall:  vážený průměr skóre (min 10 her)
      - activity: počet odehraných her (min 10)
      - perfects: počet 100% výsledků (min 10 her)
      - speed:    průměrný čas na otázku (min 5 her s ≥ 50% skóre)
    
    Filtry: difficulty (easy/medium/hard), period (daily/weekly/alltime), quiz_id (konkrétní kvíz)
    Pro konkrétní kvíz: nejlepší pokus každého hráče.
    Pinned user: aktuálně přihlášený uživatel je zvýrazněný v žebříčku.
    Šablona: templates/leaderboard.html
    """
    from sqlalchemy import func, case
    from datetime import datetime, timedelta

    # ── Parse parameters ──
    mode = request.args.get('mode', 'overall')
    if mode not in ('overall', 'activity', 'perfects', 'speed'):
        mode = 'overall'
    difficulty = request.args.get('difficulty', '')
    if difficulty not in ('easy', 'medium', 'hard'):
        difficulty = ''
    period = request.args.get('period', 'alltime')
    if period not in ('daily', 'weekly', 'alltime'):
        period = 'alltime'
    quiz_id = request.args.get('quiz_id', 0, type=int) or None

    selected_quiz = None
    if quiz_id:
        selected_quiz = Quiz.query.get(quiz_id)
        if not selected_quiz:
            quiz_id = None

    all_quizzes = Quiz.query.order_by(Quiz.name).all()

    # ── Time period filter ──
    now = datetime.utcnow()
    date_from = None
    if period == 'daily':
        date_from = now - timedelta(days=1)
    elif period == 'weekly':
        date_from = now - timedelta(weeks=1)

    perfect_expr = case(
        (db.and_(GameResult.score == GameResult.max_score, GameResult.max_score > 0), 1),
        else_=0
    )

    all_data = []

    if quiz_id:
        # ── Specific quiz leaderboard: best attempt per user ──
        q = GameResult.query.filter(
            GameResult.quiz_id == quiz_id,
            GameResult.max_score > 0
        )
        if date_from:
            q = q.filter(GameResult.date >= date_from)
        attempts = q.all()

        best_per_user = {}
        for a in attempts:
            uid = a.user_id
            if uid not in best_per_user:
                best_per_user[uid] = a
            else:
                prev = best_per_user[uid]
                if (a.score > prev.score) or (a.score == prev.score and a.time_spent < prev.time_spent):
                    best_per_user[uid] = a

        user_ids = list(best_per_user.keys())
        users_map = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

        sorted_attempts = sorted(
            best_per_user.values(),
            key=lambda a: (-a.score / a.max_score, a.time_spent)
        )
        for a in sorted_attempts:
            user = users_map.get(a.user_id)
            if not user:
                continue
            score_pct = pct(a.score / a.max_score * 100)
            all_data.append({
                'rank': len(all_data) + 1,
                'user': user,
                'primary': score_pct,
                'secondary': a.time_spent,
                '_sort': (-a.score / a.max_score, a.time_spent, user.name.lower())
            })

    elif mode == 'speed':
        # ── Speed mode ──
        base = db.session.query(GameResult).filter(
            GameResult.max_score > 0,
            GameResult.score >= GameResult.max_score * 0.5
        )
        if difficulty:
            base = base.join(Quiz, GameResult.quiz_id == Quiz.id).filter(Quiz.difficulty == difficulty)
        if date_from:
            base = base.filter(GameResult.date >= date_from)

        rows = base.with_entities(
            GameResult.user_id,
            func.avg(GameResult.time_spent * 1.0 / GameResult.max_score).label('speed_score'),
            (func.sum(GameResult.score) * 100.0 / func.sum(GameResult.max_score)).label('weighted_avg'),
            func.count(GameResult.id).label('qualifying_runs'),
            func.sum(perfect_expr).label('perfects')
        ).group_by(GameResult.user_id).having(
            func.count(GameResult.id) >= 5
        ).all()

        user_ids = [r.user_id for r in rows]
        users_map = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

        for row in rows:
            user = users_map.get(row.user_id)
            if not user:
                continue
            all_data.append({
                'rank': 0,
                'user': user,
                'primary': round(row.speed_score, 2),
                'secondary': int(row.qualifying_runs),
                'tertiary': pct(row.weighted_avg),
                '_sort': (row.speed_score, -row.weighted_avg, -row.qualifying_runs, -row.perfects, user.name.lower())
            })

    else:
        # ── Overall / Activity / Perfects ──
        base = db.session.query(GameResult).filter(GameResult.max_score > 0)
        if difficulty:
            base = base.join(Quiz, GameResult.quiz_id == Quiz.id).filter(Quiz.difficulty == difficulty)
        if date_from:
            base = base.filter(GameResult.date >= date_from)

        weighted_avg = (func.sum(GameResult.score) * 100.0 / func.sum(GameResult.max_score)).label('weighted_avg')
        games_played = func.count(GameResult.id).label('games_played')
        perfects = func.sum(perfect_expr).label('perfects')

        if mode == 'overall':
            rows = base.with_entities(
                GameResult.user_id, weighted_avg, games_played, perfects
            ).group_by(GameResult.user_id).having(
                func.count(GameResult.id) >= 10
            ).all()
        elif mode == 'activity':
            rows = base.with_entities(
                GameResult.user_id, games_played, weighted_avg, perfects
            ).group_by(GameResult.user_id).having(
                func.count(GameResult.id) >= 10
            ).all()
        elif mode == 'perfects':
            rows = base.with_entities(
                GameResult.user_id, perfects, weighted_avg, games_played
            ).group_by(GameResult.user_id).having(
                db.and_(func.sum(perfect_expr) > 0, func.count(GameResult.id) >= 10)
            ).all()

        user_ids = [r.user_id for r in rows]
        users_map = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

        for row in rows:
            user = users_map.get(row.user_id)
            if not user:
                continue
            entry = {'rank': 0, 'user': user}
            if mode == 'overall':
                entry['primary'] = pct(row.weighted_avg)
                entry['secondary'] = row.games_played
                entry['_sort'] = (-row.weighted_avg, -row.games_played, -row.perfects, user.name.lower())
            elif mode == 'activity':
                entry['primary'] = row.games_played
                entry['secondary'] = pct(row.weighted_avg)
                entry['_sort'] = (-row.games_played, -row.weighted_avg, -row.perfects, user.name.lower())
            elif mode == 'perfects':
                entry['primary'] = int(row.perfects)
                entry['secondary'] = pct(row.weighted_avg)
                entry['_sort'] = (-row.perfects, -row.weighted_avg, -row.games_played, user.name.lower())
            all_data.append(entry)

    # ── Sort, rank, pinned user ──
    all_data.sort(key=lambda e: e['_sort'])
    for i, entry in enumerate(all_data, 1):
        entry['rank'] = i

    pinned_user = None
    if current_user.is_authenticated:
        for entry in all_data:
            if entry['user'].id == current_user.id:
                pinned_user = dict(entry)
                break

    leaderboard_data = all_data[:50]

    return render_template('leaderboard.html',
                           leaderboard=leaderboard_data,
                           mode=mode,
                           difficulty=difficulty,
                           period=period,
                           quiz_id=quiz_id,
                           selected_quiz=selected_quiz,
                           all_quizzes=all_quizzes,
                           pinned_user=pinned_user)


@quiz_bp.route('/leaderboard/profile/<int:user_id>')
def mini_profile(user_id):
    """Mini profil hráče pro leaderboard hover popover (JSON).
    
    Volá ho main.js přes fetch() při najetí myší na jméno hráče.
    Vrací: jméno, avatar, statistiky, oblíbená/nejlepší kategorie, top 3 achievementy.
    """
    from sqlalchemy import func

    user = User.query.get_or_404(user_id)
    stats = user.get_stats()

    # Perfect score count
    perfect_count = sum(
        1 for r in user.game_results
        if r.max_score > 0 and r.score == r.max_score
    )

    # Favorite category (most played)
    fav_cat = db.session.query(
        Quiz.category, func.count(GameResult.id).label('cnt')
    ).join(Quiz, GameResult.quiz_id == Quiz.id).filter(
        GameResult.user_id == user_id
    ).group_by(Quiz.category).order_by(
        func.count(GameResult.id).desc()
    ).first()

    # Best category (highest weighted avg)
    best_cat = db.session.query(
        Quiz.category,
        (func.sum(GameResult.score) * 100.0 / func.sum(GameResult.max_score)).label('avg')
    ).join(Quiz, GameResult.quiz_id == Quiz.id).filter(
        GameResult.user_id == user_id,
        GameResult.max_score > 0
    ).group_by(Quiz.category).order_by(
        (func.sum(GameResult.score) * 100.0 / func.sum(GameResult.max_score)).desc()
    ).first()

    # Top 3 achievements (gold first)
    top_achs = db.session.query(Achievement).join(
        UserAchievement, UserAchievement.achievement_id == Achievement.id
    ).filter(
        UserAchievement.user_id == user_id
    ).order_by(
        db.case(
            (Achievement.tier == 'gold', 1),
            (Achievement.tier == 'silver', 2),
            (Achievement.tier == 'bronze', 3),
            else_=4
        ),
        UserAchievement.earned_at.desc()
    ).limit(3).all()

    return jsonify({
        'name': user.name,
        'avatar': user.name[0].upper() if user.name else '?',
        'avatar_img': user.avatar if user.avatar and user.avatar != 'default.png' else None,
        'stats': {
            'total_games': stats['total_games'],
            'average_score': stats['average_score'],
            'best_score': stats['best_score'],
            'perfect_count': perfect_count
        },
        'favorite_category': fav_cat[0] if fav_cat else None,
        'best_category': {
            'name': best_cat[0],
            'score': pct(best_cat[1])
        } if best_cat else None,
        'achievements': [
            {'name': a.name, 'icon': a.icon, 'tier': a.tier, 'description': a.description}
            for a in top_achs
        ]
    })


@quiz_bp.route('/my-quizzes')
@login_required
def my_quizzes():
    """Moje kvízy."""
    quizzes = Quiz.query.filter_by(author_id=current_user.id).order_by(Quiz.created_at.desc()).all()
    return render_template('my_quizzes.html', quizzes=quizzes)
