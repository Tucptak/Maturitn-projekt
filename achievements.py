"""
Logika pro systém úspěchů (achievements).
"""
from datetime import datetime
from database import db
from models import Achievement, UserAchievement, GameResult, Quiz, UserAnswer


# Definice všech úspěchů pro seed
ACHIEVEMENT_DEFINITIONS = [
    # === BRONZE - Gameplay ===
    {
        'name': 'První kroky',
        'description': 'Odehraj svůj první kvíz.',
        'icon': 'first_game.svg',
        'tier': 'bronze',
        'category': 'gameplay',
        'requirement_type': 'games_played',
        'requirement_value': 1,
    },
    {
        'name': 'Začátečník',
        'description': 'Odehraj 5 kvízů.',
        'icon': 'beginner.svg',
        'tier': 'bronze',
        'category': 'gameplay',
        'requirement_type': 'games_played',
        'requirement_value': 5,
    },
    {
        'name': 'Pravidelný hráč',
        'description': 'Odehraj 10 kvízů.',
        'icon': 'regular_player.svg',
        'tier': 'silver',
        'category': 'gameplay',
        'requirement_type': 'games_played',
        'requirement_value': 10,
    },
    {
        'name': 'Veterán',
        'description': 'Odehraj 25 kvízů.',
        'icon': 'veteran.svg',
        'tier': 'silver',
        'category': 'gameplay',
        'requirement_type': 'games_played',
        'requirement_value': 25,
    },
    {
        'name': 'Kvízový maratonec',
        'description': 'Odehraj 50 kvízů.',
        'icon': 'marathon.svg',
        'tier': 'gold',
        'category': 'gameplay',
        'requirement_type': 'games_played',
        'requirement_value': 50,
    },
    # === BRONZE - Creation ===
    {
        'name': 'Tvůrce',
        'description': 'Vytvoř svůj první kvíz.',
        'icon': 'creator.svg',
        'tier': 'bronze',
        'category': 'creation',
        'requirement_type': 'quizzes_created',
        'requirement_value': 1,
    },
    {
        'name': 'Aktivní autor',
        'description': 'Vytvoř 3 kvízy.',
        'icon': 'active_author.svg',
        'tier': 'bronze',
        'category': 'creation',
        'requirement_type': 'quizzes_created',
        'requirement_value': 3,
    },
    {
        'name': 'Kvízový designér',
        'description': 'Vytvoř 5 kvízů.',
        'icon': 'designer.svg',
        'tier': 'silver',
        'category': 'creation',
        'requirement_type': 'quizzes_created',
        'requirement_value': 5,
    },
    {
        'name': 'Kvízový architekt',
        'description': 'Vytvoř 10 kvízů.',
        'icon': 'architect.svg',
        'tier': 'gold',
        'category': 'creation',
        'requirement_type': 'quizzes_created',
        'requirement_value': 10,
    },
    # === Mastery ===
    {
        'name': 'Bezchybný',
        'description': 'Získej 100% v kvízu.',
        'icon': 'perfect.svg',
        'tier': 'silver',
        'category': 'mastery',
        'requirement_type': 'perfect_score',
        'requirement_value': 1,
    },
    {
        'name': 'Perfekcionista',
        'description': 'Získej 100% v 5 různých kvízech.',
        'icon': 'perfectionist.svg',
        'tier': 'gold',
        'category': 'mastery',
        'requirement_type': 'perfect_score',
        'requirement_value': 5,
    },
    {
        'name': 'Nadějný student',
        'description': 'Dosáhni průměrného skóre alespoň 50%.',
        'icon': 'student.svg',
        'tier': 'bronze',
        'category': 'mastery',
        'requirement_type': 'score_average',
        'requirement_value': 50,
    },
    {
        'name': 'Šikovný hráč',
        'description': 'Dosáhni průměrného skóre alespoň 70%.',
        'icon': 'skilled.svg',
        'tier': 'silver',
        'category': 'mastery',
        'requirement_type': 'score_average',
        'requirement_value': 70,
    },
    {
        'name': 'Mistr kvízů',
        'description': 'Dosáhni průměrného skóre alespoň 90%.',
        'icon': 'master.svg',
        'tier': 'gold',
        'category': 'mastery',
        'requirement_type': 'score_average',
        'requirement_value': 90,
    },
    # === Speed ===
    {
        'name': 'Blesk',
        'description': 'Dokonči kvíz za méně než 30 sekund.',
        'icon': 'lightning.svg',
        'tier': 'silver',
        'category': 'speed',
        'requirement_type': 'fast_completion',
        'requirement_value': 30,
    },
    {
        'name': 'Rychlonožka',
        'description': 'Dokonči kvíz za méně než 60 sekund.',
        'icon': 'speedster.svg',
        'tier': 'bronze',
        'category': 'speed',
        'requirement_type': 'fast_completion',
        'requirement_value': 60,
    },
    # === Streak ===
    {
        'name': 'Série správných',
        'description': 'Odpověz správně na 5 otázek v řadě v jednom kvízu.',
        'icon': 'streak5.svg',
        'tier': 'bronze',
        'category': 'streak',
        'requirement_type': 'correct_streak',
        'requirement_value': 5,
    },
    {
        'name': 'Neporazitelný',
        'description': 'Odpověz správně na 10 otázek v řadě v jednom kvízu.',
        'icon': 'streak10.svg',
        'tier': 'silver',
        'category': 'streak',
        'requirement_type': 'correct_streak',
        'requirement_value': 10,
    },
    {
        'name': 'Neomylný',
        'description': 'Odpověz správně na 20 otázek v řadě v jednom kvízu.',
        'icon': 'streak20.svg',
        'tier': 'gold',
        'category': 'streak',
        'requirement_type': 'correct_streak',
        'requirement_value': 20,
    },
    # === Milestones ===
    {
        'name': 'Stovka odpovědí',
        'description': 'Odpověz celkem na 100 otázek.',
        'icon': 'answers100.svg',
        'tier': 'silver',
        'category': 'gameplay',
        'requirement_type': 'total_answers',
        'requirement_value': 100,
    },
    {
        'name': 'Tisíc odpovědí',
        'description': 'Odpověz celkem na 1000 otázek.',
        'icon': 'answers1000.svg',
        'tier': 'gold',
        'category': 'gameplay',
        'requirement_type': 'total_answers',
        'requirement_value': 1000,
    },
]


def seed_achievements():
    """Naplní tabulku achievements výchozími daty, pokud je prázdná."""
    if Achievement.query.count() > 0:
        return
    
    for ach_data in ACHIEVEMENT_DEFINITIONS:
        achievement = Achievement(**ach_data)
        db.session.add(achievement)
    
    db.session.commit()


def get_user_progress(user):
    """Spočítá aktuální progres uživatele pro všechny typy achievementů."""
    from sqlalchemy import func
    
    games = user.game_results
    total_games = len(games)
    total_quizzes_created = len(user.quizzes)
    
    # Průměrné skóre
    if total_games > 0:
        scores = [(r.score / r.max_score * 100) if r.max_score > 0 else 0 for r in games]
        avg_score = sum(scores) / len(scores)
    else:
        avg_score = 0
    
    # Počet perfektních skóre (100%)
    perfect_count = sum(
        1 for r in games
        if r.max_score > 0 and r.score == r.max_score
    )
    
    # Nejrychlejší dokončení
    fast_times = [r.time_spent for r in games if r.time_spent > 0]
    fastest_time = min(fast_times) if fast_times else 9999
    
    # Nejdelší série správných odpovědí v jednom kvízu
    best_streak = 0
    for game in games:
        streak = 0
        for ua in game.user_answers:
            if ua.is_correct:
                streak += 1
                best_streak = max(best_streak, streak)
            else:
                streak = 0
    
    # Celkový počet odpovědí
    total_answers = sum(len(g.user_answers) for g in games)
    
    return {
        'games_played': total_games,
        'quizzes_created': total_quizzes_created,
        'score_average': avg_score,
        'perfect_score': perfect_count,
        'fast_completion': fastest_time,
        'correct_streak': best_streak,
        'total_answers': total_answers,
    }


def get_progress_for_achievement(achievement, progress):
    """Vrátí (current, target) pro daný achievement a aktuální progres."""
    req_type = achievement.requirement_type
    req_value = achievement.requirement_value
    
    if req_type == 'games_played':
        return progress['games_played'], req_value
    elif req_type == 'quizzes_created':
        return progress['quizzes_created'], req_value
    elif req_type == 'score_average':
        return round(progress['score_average'], 1), req_value
    elif req_type == 'perfect_score':
        return progress['perfect_score'], req_value
    elif req_type == 'fast_completion':
        # Pro speed: current je čas; splněno pokud current <= target
        current = progress['fast_completion']
        return current, req_value
    elif req_type == 'correct_streak':
        return progress['correct_streak'], req_value
    elif req_type == 'total_answers':
        return progress['total_answers'], req_value
    
    return 0, req_value


def is_achievement_met(achievement, progress):
    """Zkontroluje, zda je achievement splněn."""
    current, target = get_progress_for_achievement(achievement, progress)
    
    if achievement.requirement_type == 'fast_completion':
        # Splněno pokud čas <= cíl (a aspoň 1 hra)
        return progress['games_played'] > 0 and current <= target
    else:
        return current >= target


def check_achievements(user):
    """
    Zkontroluje všechny achievementy pro uživatele.
    Vrátí seznam nově získaných Achievement objektů.
    """
    progress = get_user_progress(user)
    all_achievements = Achievement.query.all()
    
    # Které už uživatel má
    earned_ids = set(
        ua.achievement_id for ua in
        UserAchievement.query.filter_by(user_id=user.id).all()
    )
    
    newly_earned = []
    
    for achievement in all_achievements:
        if achievement.id in earned_ids:
            continue
        
        if is_achievement_met(achievement, progress):
            user_ach = UserAchievement(
                user_id=user.id,
                achievement_id=achievement.id
            )
            db.session.add(user_ach)
            newly_earned.append(achievement)
    
    if newly_earned:
        db.session.commit()
    
    return newly_earned


def get_user_achievements_data(user):
    """
    Vrátí strukturovaná data pro zobrazení na profilu.
    Vrací seznam dicts s achievement info, earned status, progress.
    """
    progress = get_user_progress(user)
    all_achievements = Achievement.query.all()
    
    # Mapa earned achievementů s datem
    earned_map = {}
    for ua in UserAchievement.query.filter_by(user_id=user.id).all():
        earned_map[ua.achievement_id] = ua.earned_at
    
    completed = []
    uncompleted = []
    
    tier_order = {'gold': 0, 'silver': 1, 'bronze': 2}
    
    for ach in all_achievements:
        current, target = get_progress_for_achievement(ach, progress)
        
        # Pro fast_completion: zobrazit jinak
        if ach.requirement_type == 'fast_completion':
            display_current = current if progress['games_played'] > 0 else '—'
            display_target = f'{target}s'
        else:
            display_current = current
            display_target = target
        
        data = {
            'id': ach.id,
            'name': ach.name,
            'description': ach.description,
            'icon': ach.icon,
            'tier': ach.tier,
            'category': ach.category,
            'current': display_current,
            'target': display_target,
            'percentage': min(100, round((current / target * 100) if target > 0 else 0)) if ach.requirement_type != 'fast_completion' else (100 if progress['games_played'] > 0 and current <= target else min(100, round((target / current * 100) if current > 0 else 0))),
            'tier_order': tier_order.get(ach.tier, 3),
        }
        
        if ach.id in earned_map:
            data['earned'] = True
            data['earned_at'] = earned_map[ach.id]
            completed.append(data)
        else:
            data['earned'] = False
            data['earned_at'] = None
            uncompleted.append(data)
    
    # Řazení: Gold first, pak Silver, pak Bronze
    completed.sort(key=lambda x: x['tier_order'])
    uncompleted.sort(key=lambda x: x['tier_order'])
    
    return completed + uncompleted
