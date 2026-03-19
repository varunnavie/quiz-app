# QuizMaster AI — Backend Developer Assignment

A fully deployed REST API for an AI-powered quiz platform built with Django, Django REST Framework, and PostgreSQL.

**Live API:** https://quiz-app-production-b4cd.up.railway.app/api/docs/
**Admin Panel:** https://quiz-app-production-b4cd.up.railway.app/admin/

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
10. [Edge Cases Handled](#edge-cases-handled)
11. [Security](#security)
12. [Performance](#performance)
13. [Local Setup](#local-setup)
14. [Deployment](#deployment)

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
**What it is:** A free AI API service that gives access to powerful language models (Llama 3.3).

**Why Groq instead of Gemini:**
- We initially chose Google Gemini (free tier) but the API key returned `limit: 0` — meaning zero quota was assigned to our account. This can happen based on Google account type or region restrictions.
- Groq provides a genuinely free tier with no quota issues, fast response times, and high-quality models
- The code architecture is identical — swapping AI providers only required changing ~5 lines in `ai_service.py`

### Jazzmin
**What it is:** A theme for Django's built-in admin panel.

**Why we added it:** Django's default admin UI is functional but looks very outdated. Jazzmin replaces it with a modern, clean interface with icons and a sidebar — much better for demo purposes and the interview.

### drf-spectacular (Swagger UI)
**What it is:** Automatically generates interactive API documentation from your code.

**Why we added it:** Instead of writing API docs manually, drf-spectacular reads our views and serializers and auto-generates a beautiful Swagger UI. Interviewers can test every endpoint directly in the browser without needing Postman or curl.

---

## Project Structure

```
quiz_application/
│
├── quiz_project/          ← Django configuration
│   ├── settings.py        ← All project settings (database, installed apps, JWT config)
│   ├── urls.py            ← Main URL router — maps URLs to apps
│   └── wsgi.py            ← Entry point for production server (gunicorn)
│
├── users/                 ← Everything related to users
│   ├── models.py          ← Custom User model
│   ├── serializers.py     ← Controls what user data looks like in API responses
│   ├── views.py           ← Register and profile endpoints
│   └── urls.py            ← User-specific URL patterns
│
├── quiz/                  ← Everything related to quizzes
│   ├── models.py          ← Quiz, Question, Choice, QuizAttempt, UserAnswer, UserStats
│   ├── serializers.py     ← Controls what quiz data looks like in API responses
│   ├── views.py           ← All quiz-related endpoint logic
│   ├── urls.py            ← Quiz-specific URL patterns
│   └── ai_service.py      ← Groq API integration for question generation
│
├── .env                   ← Secret keys and API keys (NOT committed to GitHub)
├── requirements.txt       ← All Python packages needed
├── Procfile               ← Tells Railway how to start the server
└── nixpacks.toml          ← Tells Railway how to build the project
```

**Why this structure?**
We split the project into two apps — `users` and `quiz`. This is called "separation of concerns" — each app handles one area of responsibility. If we wanted to add a `billing` feature later, we'd create a third app. This makes the codebase easier to navigate and maintain.

---

## Database Schema

Here are all the database tables (called "models" in Django) and how they relate to each other:

### User (in `users` app)
Extends Django's built-in user model. We added `email` as the login field instead of username.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| email | String (unique) | Used to log in |
| username | String | Display name |
| password | String (hashed) | Never stored as plain text |
| date_joined | DateTime | Auto-set on registration |

**Why extend the built-in user?** Django gives us a User model for free with password hashing, permissions, etc. We just customized it to use email as the login identifier — more user-friendly than username.

### Quiz
Represents a quiz that was created (with AI-generated questions).

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| title | String | e.g. "Python Basics" |
| topic | String | What the AI generates questions about |
| difficulty | Choice | easy / medium / hard |
| question_count | Integer | 1–20 questions |
| created_by | FK → User | Who created this quiz |
| is_public | Boolean | Whether others can see/take it |
| status | Choice | draft / ready / failed |
| time_limit_minutes | Integer (optional) | Optional time limit |
| created_at | DateTime | Auto-set |

**The `status` field explains the AI generation lifecycle:**
- `draft` → quiz was just created, AI generation hasn't finished
- `ready` → AI generated questions successfully, quiz is available
- `failed` → AI call failed (network error, bad response, etc.)

### Question
One question belonging to a quiz.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| quiz | FK → Quiz | Which quiz this belongs to |
| text | String | The question text |
| explanation | String | Shown after answering — why the answer is correct |
| order | Integer | Question number (1, 2, 3...) |

### Choice
One answer option for a question (always 4 per question).

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| question | FK → Question | Which question this belongs to |
| text | String | The answer option text |
| is_correct | Boolean | Whether this is the correct answer |

**Important design note:** When a user is taking a quiz, we send choices WITHOUT the `is_correct` field — otherwise they'd see the answers! We only send `is_correct` in the results response after submission.

### QuizAttempt
Represents one user's attempt at a quiz.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| user | FK → User | Who is attempting |
| quiz | FK → Quiz | Which quiz |
| status | Choice | in_progress / completed / abandoned / timed_out |
| score | Float | Percentage score (0–100) |
| correct_answers | Integer | Count of correct answers |
| total_questions | Integer | Total questions in quiz |
| started_at | DateTime | When attempt began |
| completed_at | DateTime | When attempt finished |
| time_taken_seconds | Integer | How long it took |

### UserAnswer
Records which choice a user picked for each question in an attempt.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| attempt | FK → QuizAttempt | Which attempt this answer belongs to |
| question | FK → Question | Which question was answered |
| chosen_choice | FK → Choice | Which option the user picked |
| is_correct | Boolean | Was it correct? (cached for performance) |

**Why store `is_correct` here when we can derive it from Choice?**
Performance. When loading results, we don't want to do extra database joins. Storing it directly means one simple query.

**The `unique_together` constraint on (attempt, question):**
This prevents a user from submitting two answers for the same question in the same attempt — a data integrity rule enforced at the database level.

### UserStats
Aggregated performance stats for a user. One row per user.

| Field | Type | Description |
|-------|------|-------------|
| user | OneToOne → User | One stats record per user |
| total_quizzes_taken | Integer | Lifetime quiz count |
| total_correct_answers | Integer | Lifetime correct answers |
| total_questions_answered | Integer | Lifetime questions answered |
| current_streak | Integer | Consecutive quizzes passed (≥60%) |
| best_streak | Integer | Highest streak ever achieved |
| average_score | Float | Overall average percentage |
| last_activity | DateTime | Last quiz completion time |

**Why a separate stats table instead of calculating on the fly?**
If we calculated stats by querying all attempts every time, it would be slow for users with hundreds of attempts. Instead, we update the stats row once when each attempt completes — this is called "pre-aggregation" and is much faster to read.

### Relationships Summary
```
User ──< Quiz              (one user creates many quizzes)
Quiz ──< Question          (one quiz has many questions)
Question ──< Choice        (one question has 4 choices)
User ──< QuizAttempt       (one user has many attempts)
Quiz ──< QuizAttempt       (one quiz has many attempts)
QuizAttempt ──< UserAnswer (one attempt has many answers)
Question ──< UserAnswer    (one question has many user answers across attempts)
Choice ──< UserAnswer      (one choice can be selected by many users)
User ──1 UserStats         (one user has exactly one stats record)
```

---

## API Endpoints

### Authentication
| Method | URL | Auth Required | Description |
|--------|-----|--------------|-------------|
| POST | `/api/auth/register/` | No | Create new account |
| POST | `/api/auth/login/` | No | Login, get JWT tokens |
| POST | `/api/auth/token/refresh/` | No | Get new access token using refresh token |
| GET/PATCH | `/api/auth/profile/` | Yes | View or update your profile |

### Quizzes
| Method | URL | Auth Required | Description |
|--------|-----|--------------|-------------|
| GET | `/api/quizzes/` | Yes | List all public ready quizzes |
| POST | `/api/quizzes/create/` | Yes | Create quiz + trigger AI generation |
| GET | `/api/quizzes/mine/` | Yes | List your own quizzes |
| GET | `/api/quizzes/<id>/` | Yes | Get quiz with all questions |
| DELETE | `/api/quizzes/<id>/` | Yes | Delete your own quiz |

### Attempts
| Method | URL | Auth Required | Description |
|--------|-----|--------------|-------------|
| POST | `/api/quizzes/<id>/start/` | Yes | Start a new attempt |
| POST | `/api/quizzes/attempts/<id>/submit/` | Yes | Submit answers and get score |
| POST | `/api/quizzes/attempts/<id>/abandon/` | Yes | Abandon an in-progress attempt |

### Analytics
| Method | URL | Auth Required | Description |
|--------|-----|--------------|-------------|
| GET | `/api/quizzes/history/` | Yes | Your completed attempts |
| GET | `/api/quizzes/stats/` | Yes | Your overall stats and streak |
| GET | `/api/quizzes/leaderboard/` | Yes | Top 20 users by average score |

### Docs
| URL | Description |
|-----|-------------|
| `/api/docs/` | Swagger UI — interactive API explorer |
| `/api/redoc/` | ReDoc — alternative documentation style |
| `/admin/` | Django admin panel (staff only) |

---

## How Each Feature Works

### Quiz Creation and AI Generation

When you POST to `/api/quizzes/create/`:

1. The request data is validated (topic must be at least 2 characters, question_count must be 1–20)
2. A `Quiz` record is saved to the database with `status='draft'`
3. We call `generate_quiz_questions()` in `ai_service.py`
4. This sends a carefully crafted prompt to Groq's Llama 3.3 model
5. The AI returns a JSON array of questions and choices
6. We validate the AI response (correct number of questions, exactly 4 choices each, exactly one correct answer)
7. We save each `Question` and its 4 `Choice` records to the database
8. We update the quiz `status` to `'ready'`
9. The full quiz with questions is returned to the user

**What if the AI fails?**
The quiz status is set to `'failed'` and a 503 error is returned. The draft quiz remains in the database so we can debug it.

**Why wrap the database saves in `transaction.atomic()`?**
If saving question 3 fails after saving questions 1 and 2, we don't want partial data in the database. `transaction.atomic()` means either ALL saves succeed or NONE do — it's all or nothing.

### Taking a Quiz (Attempt Flow)

```
User starts attempt → User submits answers → Score is calculated → Stats are updated
```

**Start:** POST `/api/quizzes/<id>/start/`
- Creates a `QuizAttempt` with `status='in_progress'`
- Returns the `attempt_id` which the user needs for submission
- **Edge case:** If you already have an in-progress attempt for this quiz, it returns the existing attempt_id instead of creating a duplicate

**Submit:** POST `/api/quizzes/attempts/<id>/submit/`
- Validates every question_id belongs to this quiz
- Validates every choice_id belongs to the correct question
- Saves each `UserAnswer` with `is_correct` flag
- Calculates `score = (correct_answers / total_questions) × 100`
- Sets `status='completed'`, records `completed_at` and `time_taken_seconds`
- Calls `stats.update_after_attempt()` to update the user's streak and averages
- Returns full results with explanations

**Time limit check:**
If the quiz has a `time_limit_minutes` set, we check if the time elapsed since `started_at` exceeds the limit. If it does, the attempt is marked `'timed_out'` before scoring.

### Streak Tracking

A "streak" counts consecutive quizzes where the user scored ≥60% (passing grade).

In `UserStats.update_after_attempt()`:
```python
if attempt.passed:          # passed = score >= 60%
    current_streak += 1
    if current_streak > best_streak:
        best_streak = current_streak
else:
    current_streak = 0      # streak is broken
```

This runs every time a quiz is completed. The `best_streak` field never decreases — it permanently records the highest streak ever achieved.

### Leaderboard

The leaderboard returns the top 20 users ranked by `average_score`, with `best_streak` as a tiebreaker.

**Why minimum 3 quizzes?**
A user who took one quiz and got 100% shouldn't rank above someone who consistently scores 95% over 50 quizzes. The 3-quiz minimum ensures the leaderboard reflects sustained performance, not luck.

### Scoring

```
score = (correct_answers / total_questions) × 100
passed = score >= 60
```

A quiz is considered "passed" at 60% — this is used to determine whether the streak continues or resets.

---

## Authentication Deep Dive

### How JWT Works

**Registration:** You send email, username, password → account is created → no token yet

**Login:** You send email + password → server verifies → server generates two tokens:
- **Access token** (valid for 1 hour): sent with every API request in the `Authorization` header
- **Refresh token** (valid for 7 days): used only to get a new access token when the old one expires

**Making authenticated requests:**
Every protected endpoint requires this header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Why two tokens?**
Access tokens expire quickly (1 hour) for security. If someone steals your access token, it's useless after an hour. The refresh token lives longer (7 days) and is used less frequently — only to renew the access token. This means you don't have to log in every hour.

**How the server verifies the token:**
JWT tokens are cryptographically signed using the `SECRET_KEY` from settings. The server can verify the signature without a database lookup — this is what makes JWT fast.

### Role-Based Permissions

We use three permission levels:
- **AllowAny** — anyone can access (register, login, docs)
- **IsAuthenticated** — must be logged in (most endpoints)
- **Owner check** — must own the resource (deleting a quiz checks `quiz.created_by == request.user`)

---

## AI Integration

### The Prompt Engineering

The prompt we send to Groq is carefully structured:
1. Tells the AI exactly how many questions to generate
2. Specifies the exact JSON format we expect back
3. Sets difficulty-appropriate instructions (easy = definitions, hard = analysis)
4. Enforces rules: exactly 4 choices, exactly 1 correct answer

### Parsing the AI Response

AI models sometimes wrap their response in markdown code blocks (` ```json `). Our code strips those out with regex before parsing the JSON:
```python
raw = re.sub(r'^```(?:json)?\s*', '', raw)
raw = re.sub(r'\s*```$', '', raw)
```

### Validation After Parsing

Even after the AI responds, we validate:
- Is the response a list?
- Does each question have `text` and `choices`?
- Does each question have exactly 4 choices?
- Does each question have exactly 1 correct answer?

This prevents bad AI output from corrupting our database.

### Why We Switched from Gemini to Groq

We initially integrated with Google Gemini (free tier). However, the API returned `limit: 0` for our account — meaning zero quota was assigned. This can happen due to regional restrictions or account type. Google AI Studio (the chat interface) worked fine because it uses a different quota system than the API.

Groq was chosen as the replacement because:
- Genuinely free tier with no quota issues
- Provides access to Meta's Llama 3.3 70B model — high quality responses
- Very fast inference (Groq builds custom hardware for AI)
- Simple REST API similar to OpenAI's format

The architecture was designed so the AI provider can be swapped by only changing `ai_service.py` — the rest of the codebase doesn't know or care which AI is being used.

---

## Design Decisions and Trade-offs

### Decision 1: Synchronous AI Generation
**What we did:** When a user requests a quiz, we call the AI and wait for it to respond before returning the HTTP response.

**Trade-off:** The user waits 2–5 seconds while the AI generates questions. The alternative (async/background task with Celery) is more complex to set up.

**Why we chose sync:** The assignment asked for incremental building. Background tasks are a bonus feature. The current approach works reliably and is easier to explain and debug.

### Decision 2: Storing `is_correct` in UserAnswer
**What we did:** We copy the `is_correct` value from the `Choice` into the `UserAnswer` when the answer is submitted.

**Trade-off:** Slight data redundancy — the information exists in both places.

**Why:** Performance. To show quiz results, we need to know which answers were correct. Storing it directly avoids a JOIN with the `Choice` table every time results are loaded.

### Decision 3: Pre-aggregated UserStats
**What we did:** We maintain a running `UserStats` record that updates after every attempt.

**Trade-off:** Extra write on every submission.

**Why:** Reading stats (for profile, leaderboard) is much more frequent than writing. Pre-aggregation makes reads fast at the cost of slightly more work on writes.

### Decision 4: Email as username
**What we did:** Users log in with email instead of username.

**Why:** Email is unique and people are more likely to remember it. More common in modern apps.

### Decision 5: Public/Private Quizzes
**What we did:** Each quiz has an `is_public` flag.

**Why:** Allows users to create private quizzes (e.g. practice material) that others can't see or take. Private quizzes still appear in the creator's "my quizzes" list.

### Decision 6: SQLite locally, PostgreSQL in production
**What we did:** The code checks for a `DATABASE_URL` environment variable. If present (Railway), use PostgreSQL. If not (local), use SQLite.

**Why:** SQLite requires zero setup — great for development. PostgreSQL is required for production reliability. `dj_database_url` handles the connection string parsing automatically.

---

## Edge Cases Handled

| Scenario | How We Handle It |
|----------|-----------------|
| User tries to start a second attempt on the same quiz | Returns existing attempt_id with a clear error message |
| User submits an answer for a question not in the quiz | Returns 400 with specific error |
| User submits a choice that doesn't belong to the question | Returns 400 with specific error |
| User submits duplicate answers for the same question | Serializer validation rejects it before database write |
| Quiz time limit exceeded during submission | Attempt marked as `timed_out`, answers not scored |
| AI returns malformed JSON | Exception caught, quiz marked `failed`, 503 returned |
| AI returns wrong number of choices | Validation raises `ValueError` before saving |
| User tries to delete someone else's quiz | Returns 403 Forbidden |
| User tries to take a private quiz they don't own | Returns 403 Forbidden |
| User tries to submit to a completed/abandoned attempt | Returns 400 with current status |
| AI quota exhausted | Caught as exception, returns 503 with details |

---

## Security

### Password Hashing
Django never stores plain text passwords. It uses PBKDF2-SHA256 hashing with a salt. Even if the database is compromised, passwords cannot be recovered.

### JWT Secret Key
Tokens are signed with `SECRET_KEY` from environment variables — never hardcoded in the source code.

### Input Validation
Every piece of user input goes through DRF serializers before touching the database. Invalid data is rejected with clear error messages.

### .env File
Sensitive data (API keys, secret key) lives in `.env` which is in `.gitignore` — it's never committed to GitHub.

### SQL Injection Prevention
Django's ORM (Object-Relational Mapper) uses parameterized queries by default. We never write raw SQL, so SQL injection is not possible.

### CORS
`django-cors-headers` is configured to allow all origins in development. In production, this should be restricted to the actual frontend domain.

---

## Performance

### Database Indexes
We added indexes on frequently queried fields:
- `Quiz.topic` — for topic-based filtering
- `Quiz.difficulty` — for difficulty filtering
- `Quiz.created_by` — for "my quizzes" queries
- `QuizAttempt(user, status)` — for history and in-progress checks
- `QuizAttempt(quiz, status)` — for quiz analytics

Indexes make lookups much faster — instead of scanning every row, PostgreSQL jumps directly to matching rows.

### select_related
In views where we need related data, we use `select_related()` to fetch it in a single SQL query instead of making separate queries for each object. For example, `QuizAttempt.objects.select_related('quiz')` fetches both the attempt and quiz data in one query.

### Pagination
All list endpoints return paginated results (10 per page by default). This prevents returning thousands of records in one response.

### Pre-aggregated Stats
As explained above, `UserStats` avoids recalculating averages and streaks from scratch on every request.

---

## Local Setup

### Prerequisites
- Python 3.11
- Git

### Steps

```bash
# Clone the repo
git clone https://github.com/varunnavie/quiz-app.git
cd quiz-app

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
# or
venv\Scripts\activate  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Create .env file
# Add these lines:
# SECRET_KEY=any-random-string-here
# DEBUG=True
# GROQ_API_KEY=your_groq_key_from_console.groq.com

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start server
python manage.py runserver
```

### Accessing the API
- Swagger UI: http://127.0.0.1:8000/api/docs/
- Admin Panel: http://127.0.0.1:8000/admin/

---

## Deployment

### Platform: Railway (railway.app)

Railway was chosen because:
- Free tier available
- Auto-detects Python projects
- Provides managed PostgreSQL
- Deploys directly from GitHub — push code, it deploys automatically

### Environment Variables on Railway
| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key for cryptographic signing |
| `DEBUG` | Set to `False` in production |
| `GROQ_API_KEY` | Groq API key for AI question generation |
| `DATABASE_URL` | Auto-set by Railway when PostgreSQL is added |

### How Deployment Works
1. Code is pushed to GitHub
2. Railway detects the push and starts a new build
3. `nixpacks.toml` tells Railway to install Python dependencies
4. `Procfile` tells Railway to run: `python manage.py migrate && gunicorn quiz_project.wsgi --bind 0.0.0.0:$PORT`
5. `manage.py migrate` runs database migrations on the production PostgreSQL
6. `gunicorn` starts the production-grade web server
7. Railway assigns the domain and routes traffic

### Why Gunicorn instead of Django's dev server?
Django's built-in server (`manage.py runserver`) is for development only — it handles one request at a time. Gunicorn is a production WSGI server that handles multiple simultaneous requests using worker processes.

### Why Whitenoise?
In production, Django doesn't serve static files (CSS, JS for admin). Whitenoise is a middleware that handles this efficiently without needing a separate nginx server.

---

## Bonus Features Implemented

- **Streak tracking** — consecutive quiz passes tracked in real-time
- **Leaderboard** — top 20 users by average score (minimum 3 quizzes)
- **Jazzmin admin theme** — polished admin interface
- **Swagger UI** — interactive API documentation
- **Time-limited quizzes** — optional per-quiz time limits
- **Question explanations** — AI generates explanations for correct answers
- **Public/private quizzes** — users control quiz visibility
- **AI rate limiting** — separate throttle for AI generation endpoint
- **Database indexes** — on all frequently queried fields
- **Atomic transactions** — prevents partial data on AI generation failure
