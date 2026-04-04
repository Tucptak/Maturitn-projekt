# Braniac - Maturitní projekt 2026

Webová a desktopová quiz aplikace podobná Kahoot.

## 📋 Požadavky

- Python 3.10+
- MySQL databáze
- pip (Python package manager)

## 🚀 Instalace

### 1. Klonování repozitáře

```bash
git clone <url-repozitare>
cd Maturitn-projekt
```

### 2. Vytvoření virtuálního prostředí

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalace závislostí

```bash
pip install -r requirements.txt
```

### 4. Konfigurace databáze

1. Vytvořte MySQL databázi:
```sql
CREATE DATABASE quiz_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Zkopírujte `.env.example` na `.env`:
```bash
cp .env.example .env
```

3. Upravte `.env` s vašimi údaji:
```
DB_HOST=localhost
DB_USER=vas_uzivatel
DB_PASSWORD=vase_heslo
DB_NAME=quiz_app
SECRET_KEY=nahodny-bezpecnostni-klic
```

### 5. Spuštění aplikace

#### Webová aplikace (Flask)

```bash
python main.py
```

Aplikace bude dostupná na: http://localhost:5000

#### Desktopová aplikace (PyQt5)

```bash
python desktop_app.py
```

## 📁 Struktura projektu

```
Maturitn-projekt/
├── main.py              # Hlavní Flask aplikace
├── database.py          # Databázové připojení
├── models.py            # Databázové modely
├── auth.py              # Autentizace a uživatelé
├── quiz.py              # Správa kvízů
├── admin.py             # Administrace
├── api.py               # API pro desktop app
├── desktop_app.py       # PyQt5 desktopová aplikace
├── requirements.txt     # Python závislosti
├── .env.example         # Vzor environment proměnných
├── templates/           # HTML šablony
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── profile.html
│   ├── quizzes.html
│   ├── quiz_detail.html
│   ├── quiz_play.html
│   ├── quiz_create.html
│   ├── quiz_edit.html
│   ├── leaderboard.html
│   ├── my_quizzes.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── users.html
│   │   └── quizzes.html
│   └── errors/
│       ├── 404.html
│       └── 500.html
└── static/
    ├── css/
    │   └── main.css
    ├── js/
    │   ├── main.js
    │   └── quiz.js
    ├── assets/
    └── data/
```

## 👥 Uživatelské role

### Běžný uživatel
- Registrace a přihlášení
- Profil se statistikami
- Procházení a hraní kvízů
- Vytváření vlastních kvízů

### Administrátor
- Všechny funkce běžného uživatele
- Správa uživatelů (změna rolí, mazání)
- Správa všech kvízů

**Poznámka:** První registrovaný uživatel se automaticky stane administrátorem.

## 🎮 Funkce

### Webová aplikace
- ✅ Registrace a přihlášení
- ✅ Profil uživatele se statistikami
- ✅ Vytváření kvízů (název, kategorie, obtížnost, časový limit)
- ✅ Přidávání otázek s 4 odpověďmi (A, B, C, D)
- ✅ Hraní kvízů s časovačem
- ✅ Výsledky po dokončení kvízu
- ✅ Žebříček nejlepších hráčů
- ✅ Administrátorský panel

### Desktopová aplikace (PyQt5)
- ✅ Přihlášení
- ✅ Seznam kvízů s filtry
- ✅ Hraní kvízů
- ✅ Zobrazení výsledků

## 🗄️ Databázové schéma

### Users (Uživatelé)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| name | VARCHAR(100) | Jméno uživatele |
| email | VARCHAR(255) | Email (unikátní) |
| password | VARCHAR(255) | Hashované heslo |
| role | VARCHAR(20) | Role (user/admin) |
| avatar | VARCHAR(255) | Cesta k avataru |
| created_at | DATETIME | Datum registrace |

### Quizzes (Kvízy)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| name | VARCHAR(200) | Název kvízu |
| category | VARCHAR(100) | Kategorie |
| difficulty | VARCHAR(50) | Obtížnost |
| time_limit | INT | Čas na otázku (s) |
| author_id | INT | FK na users |
| created_at | DATETIME | Datum vytvoření |

### Questions (Otázky)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| quiz_id | INT | FK na quizzes |
| text | TEXT | Text otázky |
| question_type | VARCHAR(50) | Typ otázky |

### Answers (Odpovědi)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| question_id | INT | FK na questions |
| text | TEXT | Text odpovědi |
| is_correct | BOOLEAN | Je správná? |

### Game Results (Výsledky her)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| user_id | INT | FK na users |
| quiz_id | INT | FK na quizzes |
| score | INT | Dosažené skóre |
| max_score | INT | Maximální skóre |
| time_spent | INT | Čas v sekundách |
| date | DATETIME | Datum hry |

### User Answers (Odpovědi uživatele)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| game_id | INT | FK na game_results |
| question_id | INT | FK na questions |
| answer_id | INT | FK na answers |
| is_correct | BOOLEAN | Byla správná? |

## 🔒 Bezpečnost

- Hesla jsou hashována pomocí Werkzeug
- Ochrana proti CSRF pomocí Flask sessions
- Role-based access control
- Environment proměnné pro citlivé údaje

## 📝 Licence

Maturitní projekt - 2026