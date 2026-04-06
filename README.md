# Brainiac - Maturitní projekt 2026

Webová a desktopová quiz aplikace

## 📋 Požadavky

- Python 3.10+
- MySQL / MariaDB databáze
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

1. Vytvořte MySQL databázi (název si zvolte, výchozí je `vyuka9`):
```sql
CREATE DATABASE vyuka9 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Zkopírujte `.env.example` na `.env`:
```bash
copy .env.example .env
```

3. Upravte `.env` s vašimi údaji:
```
DB_HOST=localhost
DB_USER=vas_uzivatel(databáze je vytvořena na vyuka9 ve školní databázi na phpmyadmin)
DB_PASSWORD=vase_heslo
DB_NAME=vyuka9
SECRET_KEY=nahodny-bezpecnostni-klic
API_URL=http://localhost:5000
```

> **Poznámka:** Tabulky se vytvoří automaticky při prvním spuštění aplikace. Soubor `schema.sql` slouží jako referenční dokumentace databázového schématu.

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
V průběhu aplikace je spouštěna když uživatel zapne kvíz

> **Důležité:** Desktopová aplikace komunikuje s webovou aplikací přes API. Před spuštěním desktop app musí běžet webová aplikace (`python main.py`).

### 6. Spuštění testů (volitelné)

```bash
pytest test_brainiac.py
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
├── stats.py             # Statistiky a grafy
├── achievements.py      # Systém úspěchů (achievementy)
├── desktop_app.py       # PyQt5 desktopová aplikace
├── schema.sql           # SQL schéma databáze (referenční)
├── test_brainiac.py     # Automatické testy
├── requirements.txt     # Python závislosti
├── .env.example         # Vzor environment proměnných
├── er_diagram.drawio    # ER diagram databáze
├── templates/           # HTML šablony
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── profile.html
│   ├── edit_profile.html
│   ├── quizzes.html
│   ├── quiz_detail.html
│   ├── quiz_play.html
│   ├── quiz_create.html
│   ├── quiz_edit.html
│   ├── leaderboard.html
│   ├── my_quizzes.html
│   ├── stats.html
│   ├── user_stats.html
│   ├── attempt_detail.html
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
    └── assets/
        └── achievements/
```

## 👥 Uživatelské role

### Běžný uživatel
- Registrace a přihlášení
- Profil se statistikami a grafy
- Procházení a hraní kvízů
- Vytváření vlastních kvízů (ručně nebo import z CSV)
- Systém úspěchů (achievementy)

### Administrátor
- Všechny funkce běžného uživatele
- Správa uživatelů (změna rolí, mazání)
- Správa všech kvízů
- Administrátorský dashboard se statistikami

**Poznámka:** První registrovaný uživatel se automaticky stane administrátorem.

## 🎮 Funkce

### Webová aplikace
- ✅ Registrace a přihlášení s validací emailu
- ✅ Profil uživatele se statistikami a grafy
- ✅ Vytváření kvízů (název, kategorie, obtížnost, časový limit)
- ✅ Import kvízů z CSV souboru
- ✅ Přidávání otázek s 4 odpověďmi (A, B, C, D)
- ✅ Hraní kvízů s časovačem
- ✅ Výsledky po dokončení kvízu s exportem
- ✅ Žebříček nejlepších hráčů
- ✅ Statistiky a porovnání s ostatními hráči
- ✅ Systém úspěchů (achievementy)
- ✅ Administrátorský panel

### Desktopová aplikace (PyQt5)
- ✅ Přihlášení přes SSO token
- ✅ Seznam kvízů s filtry
- ✅ Hraní kvízů
- ✅ Zobrazení výsledků

## 🗄️ Databázové schéma

Databáze obsahuje 8 tabulek. Kompletní SQL schéma je v souboru `schema.sql`, ER diagram v `er_diagram.drawio`.

### users1 (Uživatelé)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| name | VARCHAR(100) | Jméno uživatele |
| email | VARCHAR(255) | Email (unikátní) |
| password | VARCHAR(255) | Hashované heslo |
| role | VARCHAR(20) | Role (user/admin) |
| avatar | VARCHAR(255) | Cesta k avataru |
| created_at | DATETIME | Datum registrace |

### quizzes (Kvízy)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| name | VARCHAR(200) | Název kvízu |
| category | VARCHAR(100) | Kategorie |
| difficulty | VARCHAR(50) | Obtížnost |
| time_limit | INT | Čas na otázku (s) |
| author_id | INT | FK na users1 |
| created_at | DATETIME | Datum vytvoření |

### questions (Otázky)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| quiz_id | INT | FK na quizzes |
| text | TEXT | Text otázky |
| question_type | VARCHAR(50) | Typ otázky |

### answers (Odpovědi)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| question_id | INT | FK na questions |
| text | TEXT | Text odpovědi |
| is_correct | BOOLEAN | Je správná? |

### game_results (Výsledky her)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| user_id | INT | FK na users1 |
| quiz_id | INT | FK na quizzes |
| score | INT | Dosažené skóre |
| max_score | INT | Maximální skóre |
| time_spent | INT | Čas v sekundách |
| date | DATETIME | Datum hry |

### user_answers (Odpovědi uživatele)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| game_id | INT | FK na game_results |
| question_id | INT | FK na questions |
| answer_id | INT | FK na answers (nullable) |
| answer_text | TEXT | Text odpovědi |
| is_correct | BOOLEAN | Byla správná? |

### achievements (Úspěchy)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| name | VARCHAR(200) | Název úspěchu |
| description | VARCHAR(500) | Popis |
| icon | VARCHAR(255) | Ikona |
| tier | VARCHAR(20) | Úroveň (bronze/silver/gold) |
| category | VARCHAR(100) | Kategorie |
| requirement_type | VARCHAR(100) | Typ podmínky |
| requirement_value | INT | Hodnota podmínky |

### user_achievements (Získané úspěchy)
| Sloupec | Typ | Popis |
|---------|-----|-------|
| id | INT | Primární klíč |
| user_id | INT | FK na users1 |
| achievement_id | INT | FK na achievements |
| earned_at | DATETIME | Datum získání |

## 🔒 Bezpečnost

- Hesla jsou hashována pomocí Werkzeug
- Ochrana proti CSRF pomocí Flask-WTF
- Ochrana proti XSS v uživatelském obsahu
- Role-based access control (uživatel / administrátor)
- Environment proměnné pro citlivé údaje (.env)
- Validace emailu při registraci

## 📝 Licence

Maturitní projekt - 2026
