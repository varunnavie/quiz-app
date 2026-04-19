# QuizMaster AI — Backend 

A fully deployed REST API for an AI-powered quiz platform built with Django, Django REST Framework, and PostgreSQL.

**Live API:** https://quiz-app-production-b4cd.up.railway.app/api/docs/
**Admin Panel:** https://quiz-app-production-b4cd.up.railway.app/admin/
**GitHub:** https://github.com/varunnavie/quiz-app

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [Tech Stack and Why](#tech-stack-and-why)
3. [Project Structure](#project-structure)
4. [Database Schema](#database-schema)
5. [API Endpoints](#api-endpoints)
6. [How Each Feature Works](#how-each-feature-works)
7. [Authentication Deep Dive](#authentication-deep-dive)
8. [AI Integration](#ai-integration)
9. [Design Decisions and Trade-offs](#design-decisions-and-trade-offs)
10. [Challenges Faced and Solutions](#challenges-faced-and-solutions)
11. [Edge Cases Handled](#edge-cases-handled)
12. [Security](#security)
13. [Performance and Caching](#performance-and-caching)
14. [Testing Approach](#testing-approach)
15. [Local Setup](#local-setup)
16. [Deployment](#deployment)
17. [Bonus Features](#bonus-features)

---

## What This Project Does

QuizMaster AI is a backend REST API that lets users:
- Register and log in securely
- Request a quiz on any topic (e.g. "Python", "World History", "Maths")
- Get AI-generated questions automatically — no manual question entry needed
- Take the quiz and submit answers
- Get instant scoring with explanations for each answer
- Track their performance history, streaks, and overall stats
- See a leaderboard of top performers

This is a pure backend project — it exposes JSON API endpoints that any frontend (mobile app, website) can connect to.

---

## Tech Stack and Why

### Django + Django REST Framework (DRF)
**What it is:** Django is a Python web framework. DRF is a toolkit built on top of Django specifically for building REST APIs.

**Why we chose it:**
- Django gives us a lot out of the box: user authentication, database migrations, admin panel
- DRF makes it easy to convert Python objects into JSON responses
- It enforces clean, structured API design
- Large community, well-documented, widely used in production

### PostgreSQL
**What it is:** A powerful, open-source relational database.

**Why we chose it over SQLite:**
- SQLite is a file-based database — fine for local development but not suitable for production (can't handle multiple users simultaneously)
- PostgreSQL handles concurrent users, is hosted on Railway, and is industry standard
- We use SQLite locally for development (simpler setup) and PostgreSQL in production — this is a common real-world pattern

### JWT (JSON Web Tokens) via djangorestframework-simplejwt
**What it is:** A way to authenticate users without storing session data on the server.

**Why we chose it:**
- REST APIs are "stateless" — the server doesn't remember who you are between requests
- JWT solves this: when you log in, you get a token (like a digital ID card)
- You send that token with every request and the server verifies it
- No database lookup needed to verify the token — faster

### Groq (AI Provider)
**What it is:** A free AI API service that gives access to powerful language models (Llama 3.3 70B).

**Why Groq instead of Gemini:**
- We initially chose Google Gemini (free tier) but the API returned `limit: 0` — zero quota assigned
- Groq provides a genuinely free tier with no quota issues, fast response times, and high-quality models
- The code architecture is swappable — changing AI providers only requires updating `ai_service.py`

### Jazzmin
**What it is:** A modern theme for Django's built-in admin panel.

**Why we added it:** Django's default admin UI is functional but outdated. Jazzmin replaces it with a modern interface with icons and a sidebar — making quiz and user management much easier to navigate.

### drf-spectacular (Swagger UI)
**What it is:** Auto-generates interactive API documentation from your code.

**Why we added it:** Instead of writing docs manually, drf-spectacular reads our views and serializers and generates a full Swagger UI — anyone can test every endpoint in the browser without Postman.

---

## Project Structure

```
quiz_application/
│
├── quiz_project/          ← Django configuration
│   ├── settings.py        ← All settings (database, cache, JWT, installed apps)
│   ├── urls.py            ← Main URL router — maps URLs to apps
│   └── wsgi.py            ← Entry point for production server (gunicorn)
│
├── users/                 ← Everything related to users
│   ├── models.py          ← Custom User model (email-based login)
│   ├── serializers.py     ← Input validation and response shaping for users
│   ├── views.py           ← Register and profile endpoints
│   ├── urls.py            ← User-specific URL patterns
│   └── tests.py           ← 13 tests covering auth and profile
│
├── quiz/                  ← Everything related to quizzes
│   ├── models.py          ← Quiz, Question, Choice, QuizAttempt, UserAnswer, UserStats
│   ├── serializers.py     ← Input validation and response shaping for quizzes
│   ├── views.py           ← All quiz, attempt, and analytics endpoint logic
│   ├── urls.py            ← Quiz-specific URL patterns
│   ├── ai_service.py      ← Groq API integration for AI question generation
│   └── tests.py           ← 20 tests covering models, attempts, scoring, edge cases
│
├── .env                   ← Secret keys and API keys (NOT committed to GitHub)
├── requirements.txt       ← All Python packages needed
├── Procfile               ← Tells Railway how to start the server
└── nixpacks.toml          ← Tells Railway how to build the project
```

**Why two apps?**
Separation of concerns — `users` handles identity, `quiz` handles everything else. Adding a new feature (e.g. billing) would mean a third app, not cluttering existing ones.

---

## Database Schema

### User
Extends Django's built-in user model. Email is used as the login field.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| email | String (unique) | Login identifier |
| username | String | Display name |
| password | String (hashed) | Never stored as plain text |
| date_joined | DateTime | Auto-set on registration |

### Quiz

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| title | String | Quiz name |
| topic | String | What AI generates questions about |
| difficulty | Choice | easy / medium / hard |
| question_count | Integer | 1–20 |
| created_by | FK → User | Creator |
| is_public | Boolean | Visible to all users? |
| status | Choice | draft → ready → failed |
| time_limit_minutes | Integer (optional) | Optional time cap |
| created_at | DateTime | Auto-set |

**Status lifecycle:** `draft` (just created) → `ready` (AI succeeded) → `failed` (AI failed)

### Question

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| quiz | FK → Quiz | Parent quiz |
| text | String | Question text |
| explanation | String | Why the answer is correct (shown after submission) |
| order | Integer | Question number |

### Choice

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| question | FK → Question | Parent question |
| text | String | Answer option text |
| is_correct | Boolean | Is this the right answer? |

**Note:** `is_correct` is hidden from quiz-taking responses. It's only included in results after submission.

### QuizAttempt

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| user | FK → User | Who is attempting |
| quiz | FK → Quiz | Which quiz |
| status | Choice | in_progress / completed / abandoned / timed_out |
| score | Float | Percentage 0–100 |
| correct_answers | Integer | Count of correct answers |
| total_questions | Integer | Total questions |
| started_at | DateTime | Attempt start time |
| completed_at | DateTime | Attempt end time |
| time_taken_seconds | Integer | Duration |

### UserAnswer

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| attempt | FK → QuizAttempt | Parent attempt |
| question | FK → Question | Which question |
| chosen_choice | FK → Choice | What the user picked |
| is_correct | Boolean | Cached for performance |

**Constraint:** `unique_together('attempt', 'question')` — one answer per question per attempt, enforced at the database level.

### UserStats
One row per user. Updated after every completed attempt.

| Field | Type | Description |
|-------|------|-------------|
| user | OneToOne → User | Owner |
| total_quizzes_taken | Integer | Lifetime count |
| total_correct_answers | Integer | Lifetime correct |
| total_questions_answered | Integer | Lifetime answered |
| current_streak | Integer | Consecutive passes (≥60%) |
| best_streak | Integer | Highest streak ever |
| average_score | Float | Overall average % |
| last_activity | DateTime | Last completion time |

### Relationships Summary
```
User ──< Quiz              (one user creates many quizzes)
Quiz ──< Question          (one quiz has many questions)
Question ──< Choice        (one question has 4 choices)
User ──< QuizAttempt       (one user has many attempts)
Quiz ──< QuizAttempt       (one quiz has many attempts)
QuizAttempt ──< UserAnswer (one attempt has many answers)
Question ──< UserAnswer    (same question answered by many users)
Choice ──< UserAnswer      (one choice can be picked by many users)
User ──1 UserStats         (one user has exactly one stats record)
```

---

## API Endpoints

All endpoints are available at both `/api/v1/` (versioned) and `/api/` (legacy, backwards compatible).

### Authentication
| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/api/v1/auth/register/` | No | Create new account |
| POST | `/api/v1/auth/login/` | No | Login, receive JWT tokens |
| POST | `/api/v1/auth/token/refresh/` | No | Get new access token |
| GET/PATCH | `/api/v1/auth/profile/` | Yes | View or update profile |

### Quizzes
| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/v1/quizzes/` | Yes | List public quizzes (cached 2 min) |
| POST | `/api/v1/quizzes/create/` | Yes | Create quiz + AI generation |
| GET | `/api/v1/quizzes/mine/` | Yes | Your own quizzes |
| GET | `/api/v1/quizzes/<id>/` | Yes | Full quiz with questions |
| DELETE | `/api/v1/quizzes/<id>/` | Yes | Delete your own quiz |

### Attempts
| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/api/v1/quizzes/<id>/start/` | Yes | Start an attempt |
| POST | `/api/v1/quizzes/attempts/<id>/submit/` | Yes | Submit answers, get score |
| POST | `/api/v1/quizzes/attempts/<id>/abandon/` | Yes | Abandon in-progress attempt |

### Analytics
| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/v1/quizzes/history/` | Yes | Your completed attempts |
| GET | `/api/v1/quizzes/stats/` | Yes | Your stats and streak |
| GET | `/api/v1/quizzes/leaderboard/` | Yes | Top 20 users (cached 5 min) |

### Documentation & Admin
| URL | Description |
|-----|-------------|
| `/api/docs/` | Swagger UI — interactive API explorer |
| `/api/redoc/` | ReDoc — alternative documentation view |
| `/admin/` | Django admin panel (Jazzmin theme) |

---

## How Each Feature Works

### Quiz Creation and AI Generation

When POST `/api/v1/quizzes/create/` is called:

1. Serializer validates input (topic ≥ 2 chars, question_count 1–20)
2. Quiz saved to DB with `status='draft'`
3. `generate_quiz_questions()` called in `ai_service.py`
4. Prompt sent to Groq's Llama 3.3 70B model
5. Response parsed from JSON, markdown stripped if present
6. Each question validated: 4 choices, exactly 1 correct
7. All questions and choices saved inside `transaction.atomic()`
8. Quiz status updated to `'ready'`
9. Cache for quiz list invalidated so new quiz appears immediately
10. Full quiz returned in response

**If AI fails:** quiz marked `'failed'`, 503 returned, no partial data saved.

### Taking a Quiz

```
Start attempt → Submit all answers → Score calculated → Stats updated
```

- **Start:** Creates `QuizAttempt` with `status='in_progress'`. Blocks duplicate attempts.
- **Submit:** Validates all question/choice IDs, saves `UserAnswer` records, calculates score, updates `UserStats`.
- **Time limit:** If exceeded at submit time, attempt is marked `timed_out` and not scored.

### Scoring
```
score = (correct_answers / total_questions) × 100
passed = score >= 60%
```

### Streak Tracking
```python
if attempt.passed:
    current_streak += 1
    best_streak = max(best_streak, current_streak)
else:
    current_streak = 0
```
`best_streak` never decreases — it permanently records the highest streak ever.

### Leaderboard
Top 20 users by `average_score`, with `best_streak` as tiebreaker. Minimum 3 quizzes required to appear — prevents a single lucky attempt from topping the board.

---

## Authentication Deep Dive

**Login** returns two tokens:
- **Access token** — valid 1 hour, sent with every request as `Authorization: Bearer <token>`
- **Refresh token** — valid 7 days, used to get a new access token

**Why two tokens?** Short-lived access tokens limit damage if stolen. The refresh token renews silently without re-login.

**Verification:** Tokens are cryptographically signed with `SECRET_KEY`. No database lookup needed — just signature verification. This is what makes JWT fast.

**Permission levels:**
- `AllowAny` — register, login, docs
- `IsAuthenticated` — all other endpoints
- Owner check — delete quiz, access private quiz

---

## AI Integration

### How It Works

`quiz/ai_service.py` is the only file that knows about the AI provider. It:
1. Builds a structured prompt with topic, difficulty, count, and exact JSON format
2. Calls Groq's API with the Llama 3.3 70B model
3. Strips markdown formatting from response with regex
4. Parses JSON
5. Validates structure (4 choices, 1 correct per question)
6. Returns clean list of question dicts

### Why Groq over Gemini

We started with Google Gemini. The API returned `limit: 0` — zero quota — despite the free tier being advertised. This is a known issue in certain regions or account types. Google AI Studio's chat interface worked fine because it's on a separate quota system from the programmatic API.

Groq was chosen as the replacement:
- Truly free tier, instant access, no quota issues
- Llama 3.3 70B produces high-quality, well-structured quiz questions
- Groq's custom hardware makes inference very fast
- Only ~5 lines of code changed to switch providers — the architecture is provider-agnostic

### AI Rate Limiting

A custom `AIGenerationThrottle` limits quiz creation to 20 per hour per user. This protects against API abuse and excessive Groq API usage.

---

## Design Decisions and Trade-offs

### 1. Synchronous AI Generation
**Decision:** Wait for AI during the HTTP request (user waits 2–5 seconds).
**Trade-off:** Latency on quiz creation vs. simpler code.
**Why:** Celery + Redis for background tasks adds significant complexity. The synchronous approach is reliable, debuggable, and sufficient for this scale.

### 2. Storing `is_correct` in UserAnswer
**Decision:** Copy `is_correct` from Choice into UserAnswer at submission time.
**Trade-off:** Minor data redundancy.
**Why:** Avoids a JOIN to the Choice table every time results are loaded. Read performance wins over minimal storage cost.

### 3. Pre-aggregated UserStats
**Decision:** Maintain a running stats row updated after each attempt.
**Trade-off:** Extra write per submission.
**Why:** Stats are read far more often than written (profile page, leaderboard). Pre-aggregation makes reads O(1) regardless of history size.

### 4. Email as Login Field
**Decision:** `USERNAME_FIELD = 'email'` on the custom User model.
**Why:** Email is universally unique and users remember it more reliably than a chosen username.

### 5. SQLite Locally, PostgreSQL in Production
**Decision:** Check for `DATABASE_URL` env var; use PostgreSQL if present, SQLite otherwise.
**Why:** Zero-setup local development while using a production-grade database in deployment. `dj_database_url` handles the connection string automatically.

### 6. API Versioning via URL Prefix
**Decision:** All endpoints available at `/api/v1/` with legacy `/api/` kept for backwards compatibility.
**Why:** URL versioning is the most explicit and visible approach. If the API changes in a breaking way, a `/api/v2/` can be introduced without breaking existing clients.

### 7. Caching Strategy
**Decision:** Cache quiz list (2 min) and leaderboard (5 min). Invalidate quiz list when a new quiz is created.
**Why:** These are the most frequently read endpoints. Caching reduces database load significantly under concurrent usage. TTLs are short enough that stale data is acceptable.

---

## Challenges Faced and Solutions

### Challenge 1: Gemini API Quota Issue
**Problem:** Google Gemini returned `limit: 0` for every model — zero free tier quota despite the advertised free plan. The chat UI worked fine but the programmatic API did not.
**Solution:** Switched to Groq which provides a genuinely free API. The codebase was designed with a clean `ai_service.py` abstraction, so swapping providers took only a few minutes.

### Challenge 2: Multiple Django Servers Running Simultaneously
**Problem:** Running `python manage.py runserver` multiple times (as background processes) caused 10 server instances to accumulate. Each had its own in-memory throttle counter, causing confusing 429 errors.
**Solution:** Killed all Python processes and restarted cleanly. Going forward, always check for running instances before starting a new server.

### Challenge 3: Git Repository Root Mismatch
**Problem:** Git was initialized at the home directory (`C:/Users/tnvar`) instead of the project folder. This caused Railway to see `OneDrive/Desktop/quiz_application/` as a subfolder instead of the project root — it couldn't detect the Python project.
**Solution:** Removed the misplaced `.git` folder and re-initialized git inside the actual project directory. Railway then detected the Python project correctly.

### Challenge 4: AI Response Formatting
**Problem:** The AI sometimes wraps its JSON response in markdown code blocks (` ```json `) even when instructed not to.
**Solution:** Applied regex stripping before JSON parsing:
```python
raw = re.sub(r'^```(?:json)?\s*', '', raw)
raw = re.sub(r'\s*```$', '', raw)
```
Added multi-layer validation after parsing to catch any remaining structural issues.

### Challenge 5: Cache Bleeding Between Tests
**Problem:** Django's in-memory cache (`LocMemCache`) persisted between test cases. One test caching an empty quiz list caused the next test to read a stale empty cache, causing false failures.
**Solution:** Added `cache.clear()` in each test class's `setUp()` method to ensure a clean cache state before every test.

---

## Edge Cases Handled

| Scenario | How We Handle It |
|----------|-----------------|
| Duplicate in-progress attempt | Returns existing `attempt_id` with clear message |
| Answer for wrong quiz's question | Validated against quiz's question set — 400 returned |
| Choice not belonging to question | Cross-validated before saving — 400 returned |
| Duplicate answers for same question | Serializer validates uniqueness — 400 returned |
| Quiz time limit exceeded | Attempt marked `timed_out`, not scored |
| AI returns malformed JSON | Exception caught, quiz marked `failed`, 503 returned |
| AI returns wrong choice count | Validation before DB save raises `ValueError` |
| Deleting another user's quiz | Ownership check — 403 returned |
| Taking a private quiz you don't own | Ownership check — 403 returned |
| Submitting to a completed attempt | Status check — 400 with current status |
| AI quota exhausted | Caught, 503 returned with detail |
| Empty answers list | Serializer validation — 400 returned |

---

## Security

| Concern | How Addressed |
|---------|--------------|
| Passwords | PBKDF2-SHA256 hashing with salt — Django built-in |
| Secret keys | Stored in `.env`, loaded via `python-dotenv`, never committed |
| SQL injection | Django ORM uses parameterized queries by default |
| Input validation | All input goes through DRF serializers before DB write |
| Token signing | JWT signed with `SECRET_KEY` — tamper-proof |
| Resource ownership | Manual checks in views — 403 on unauthorized access |
| CORS | `django-cors-headers` — can be restricted to specific domains |

---

## Performance and Caching

### Caching

| Cache Key | TTL | What's Cached |
|-----------|-----|---------------|
| `quiz_list_{topic}_{difficulty}` | 2 minutes | Public quiz list per filter combination |
| `leaderboard_top20` | 5 minutes | Top 20 leaderboard results |

Cache backend:
- **Local development:** `LocMemCache` (in-memory, no setup required)
- **Production:** Redis via `REDIS_URL` environment variable (when configured)

Cache invalidation: quiz list cache is cleared when a new quiz is successfully created, so it appears immediately without waiting for the TTL to expire.

### Database Indexes
Indexes on all frequently filtered fields:
- `Quiz.topic`, `Quiz.difficulty`, `Quiz.created_by`
- `QuizAttempt(user, status)`, `QuizAttempt(quiz, status)`

### Query Optimization
`select_related()` used wherever related objects are needed — fetches data in a single SQL JOIN instead of N+1 queries.

### Pagination
All list endpoints return 10 results per page. Prevents large payloads as data grows.

### Pre-aggregated Stats
`UserStats` is updated on write, read as a single row lookup — O(1) regardless of attempt history size.

---

## Testing Approach

**33 tests** covering the full application. Run with:
```bash
python manage.py test --verbosity=2
```

### Test Coverage

**users/tests.py — 13 tests**

| Test Class | Tests |
|------------|-------|
| `UserRegistrationTests` | Valid registration, duplicate email, password mismatch, weak password, missing fields |
| `UserAuthenticationTests` | Successful login, wrong password, nonexistent user |
| `UserProfileTests` | Get profile, unauthenticated access blocked, profile update |

**quiz/tests.py — 20 tests**

| Test Class | Tests |
|------------|-------|
| `QuizModelTests` | `__str__`, attempt_count property, percentage calculation, passed/failed logic |
| `UserStatsTests` | Streak increase on pass, streak reset on fail, best_streak never decreases, average score calculation |
| `QuizAPITests` | Public quiz listing, draft quiz hidden, difficulty filter, auth required |
| `AttemptAPITests` | Start attempt, duplicate blocked, correct answer scoring, wrong answer scoring, cannot resubmit, invalid question ID, abandon, history, stats update |

### Testing Philosophy
- **No mocking the database** — tests run against a real SQLite database (created fresh per test run)
- **No mocking the AI** — quiz creation tests build quizzes directly via the model, bypassing the AI call (tests should be fast and deterministic)
- **Edge cases first** — duplicate attempts, wrong IDs, resubmission, and auth failures are all explicitly tested
- **Cache isolation** — `cache.clear()` called in `setUp()` to prevent state bleeding between tests

---

## Local Setup

### Prerequisites
- Python 3.11
- Git

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/varunnavie/quiz-app.git
cd quiz-app

# 2. Create virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
# venv\Scripts\activate        # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file in the project root with these contents:
# SECRET_KEY=any-long-random-string
# DEBUG=True
# GROQ_API_KEY=your_key_from_console.groq.com

# 5. Run database migrations
python manage.py migrate

# 6. Create an admin user (optional)
python manage.py createsuperuser

# 7. Run tests to verify everything works
python manage.py test

# 8. Start the development server
python manage.py runserver
```

### Accessing Locally
| URL | What |
|-----|------|
| `http://127.0.0.1:8000/api/docs/` | Swagger UI |
| `http://127.0.0.1:8000/admin/` | Admin panel |
| `http://127.0.0.1:8000/api/v1/auth/register/` | Register endpoint |

---

## Deployment

### Platform: Railway (railway.app)

**Why Railway:**
- Free tier with managed PostgreSQL
- Deploys directly from GitHub on every push
- Environment variables managed securely in dashboard

### Required Environment Variables
| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key for cryptographic signing |
| `DEBUG` | Set to `False` in production |
| `GROQ_API_KEY` | Groq API key for AI generation |
| `DATABASE_URL` | Auto-injected by Railway PostgreSQL plugin |

### Deployment Flow
1. Push to GitHub → Railway auto-detects change
2. `nixpacks.toml` → installs Python 3.11 and pip dependencies
3. Custom start command → `python manage.py migrate && gunicorn quiz_project.wsgi --bind 0.0.0.0:$PORT`
4. Migrations run on PostgreSQL
5. Gunicorn serves the application

**Why Gunicorn:** Django's dev server handles one request at a time. Gunicorn spawns multiple workers for concurrent requests.

**Why Whitenoise:** Serves Django admin static files (CSS/JS) from within the app — no separate nginx needed.

---

## Bonus Features

| Feature | Description |
|---------|-------------|
| Streak tracking | Consecutive quiz passes tracked per user |
| Leaderboard | Top 20 users by average score (min. 3 quizzes) |
| Jazzmin admin | Modern admin UI with icons and sidebar |
| Swagger + ReDoc | Auto-generated interactive API documentation |
| Time-limited quizzes | Optional per-quiz time caps |
| Question explanations | AI generates "why" for each correct answer |
| Public/private quizzes | Creator controls visibility |
| AI rate limiting | 20 quiz generations per hour per user |
| Database indexes | All frequently filtered fields indexed |
| Atomic transactions | No partial data on AI generation failure |
| Caching | Quiz list (2 min) and leaderboard (5 min) cached |
| API versioning | `/api/v1/` with backwards-compatible `/api/` |
| 33 automated tests | Full coverage of auth, models, attempts, edge cases |
