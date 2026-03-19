# QuizMaster AI — Interview Cheat Sheet

This document prepares you for every question the interviewer might ask about your project.
Read this multiple times. The goal is not to memorize — it's to understand.

---

## SECTION 1: Project Overview Questions

### Q: Walk me through your project.
**A:**
"I built a REST API for an AI-powered quiz platform using Django and Django REST Framework. The core idea is simple — a user registers, requests a quiz on any topic like Python or History, and our backend calls an AI service (Groq with Llama 3.3) to generate questions automatically. The user then takes the quiz, submits answers, and gets instant scoring with explanations. On top of that, I built streak tracking, a leaderboard, and a full analytics system. The whole thing is deployed on Railway with a PostgreSQL database."

---

### Q: Why Django? Why not Flask or FastAPI?
**A:**
"Django comes with a lot built in — user authentication, database migrations, an admin panel, and security features. For a project with user management, database models, and complex relationships, Django's batteries-included approach saves a lot of time. DRF (Django REST Framework) sits on top of Django and makes building REST APIs very clean with serializers, viewsets, and authentication classes. Flask would have required building a lot of these from scratch. FastAPI is newer and great for async performance, but Django has more mature tooling for what this project needed."

---

### Q: What does your API do exactly? Describe the full user journey.
**A:**
"A user starts by registering with email and password. They log in and get a JWT access token. They use that token for all subsequent requests. They can request a new quiz by specifying a topic, difficulty, and number of questions — the backend calls Groq's AI API, gets questions back, validates and saves them. The user gets the quiz with questions and choices. They start an attempt, submit their answers, and get back a full result — score, which answers were correct, and explanations for each question. Their stats (average score, streak) update automatically. They can check the leaderboard to see how they rank against others."

---

## SECTION 2: Database Design Questions

### Q: Walk me through your database schema.
**A:**
"I have 6 models. User stores account info — I customized Django's built-in user to use email as the login field. Quiz stores the quiz metadata — topic, difficulty, status. Question belongs to a Quiz, and Choice belongs to a Question — each question always has exactly 4 choices. QuizAttempt tracks a specific user taking a specific quiz — it records the score, status, and time taken. UserAnswer records which choice a user picked for each question in an attempt. And UserStats is a pre-aggregated stats table — one row per user storing their running average, streak, and totals."

---

### Q: Why did you create a separate UserStats table instead of calculating on the fly?
**A:**
"Performance. If I calculated stats by querying all of a user's attempts every time someone loads the leaderboard or profile, it would get slower as the data grows. Instead, I update the UserStats record once when each attempt completes. Reading stats becomes a simple single-row lookup regardless of how many attempts the user has. This is called pre-aggregation — trading a slightly more expensive write for a much faster read. Reads are far more common than writes in this system."

---

### Q: Why do you store `is_correct` in UserAnswer when you could derive it from Choice?
**A:**
"It's a deliberate denormalization for performance. When loading quiz results, I need to know which answers were correct. If I didn't store it in UserAnswer, I'd need to JOIN with the Choice table every time. By storing it directly, results load with one simple query. The small cost is a tiny bit of redundant data — a boolean per answer — which is completely acceptable."

---

### Q: What is `unique_together` on UserAnswer and why did you add it?
**A:**
"The `unique_together = ('attempt', 'question')` constraint means a user can only have one answer per question per attempt — enforced at the database level. Without this, a bug or a malicious request could insert multiple answers for the same question and inflate the score. This is data integrity — we let the database itself guarantee correctness, not just our application code."

---

### Q: Why do you have a `status` field on Quiz?
**A:**
"It tracks the AI generation lifecycle. When a quiz is first created, it's in `draft` status — the questions haven't been generated yet. After the AI successfully creates questions, status becomes `ready`. If the AI call fails for any reason, status becomes `failed`. This means the API can return meaningful information to users — only `ready` quizzes appear in the public list. And if a quiz fails, we can see it in the admin panel and debug it."

---

### Q: What indexes did you add and why?
**A:**
"I added indexes on fields that are frequently used in WHERE clauses and filters. Specifically: `Quiz.topic` and `Quiz.difficulty` for filtering the quiz list, `Quiz.created_by` for the 'my quizzes' query, and a composite index on `QuizAttempt(user, status)` for checking in-progress attempts and loading history. Without indexes, PostgreSQL would scan every row in the table for each query — with indexes, it jumps directly to matching rows. This makes queries much faster as data grows."

---

## SECTION 3: API Architecture Questions

### Q: How did you structure your API endpoints?
**A:**
"I followed RESTful principles. Resources are nouns — `/api/quizzes/`, `/api/quizzes/<id>/`. HTTP methods indicate the action — GET to read, POST to create, DELETE to remove. I split endpoints into logical groups: auth endpoints under `/api/auth/`, quiz endpoints under `/api/quizzes/`, and nested routes for attempts under `/api/quizzes/attempts/`. Actions that aren't pure CRUD — like starting an attempt or submitting answers — use action-style URLs like `/start/` and `/submit/`."

---

### Q: Why did you use class-based views instead of function-based views?
**A:**
"DRF's class-based views give a lot for free. `generics.ListAPIView` handles GET requests with pagination automatically. `generics.CreateAPIView` handles POST with validation. I only need to specify the serializer and queryset. For more complex logic like submit and score — where I need full control — I used `APIView` directly and wrote the logic manually. Class-based views reduce boilerplate while still letting me override behaviour when needed."

---

### Q: What is a serializer and why do you need it?
**A:**
"A serializer converts Python objects (Django model instances) into JSON for API responses, and converts incoming JSON back into validated Python data. It's the layer between the database and the API response. For example, my `QuizDetailSerializer` takes a Quiz object from the database and converts it to a JSON object with nested questions and choices. It also handles validation — if a required field is missing in a request, the serializer raises a validation error before the code even touches the database."

---

### Q: Why do you have multiple serializers for Quiz?
**A:**
"Different endpoints need different data shapes. `QuizListSerializer` is lightweight — just the summary fields needed for a list view. `QuizDetailSerializer` includes nested questions and choices — more data, used when actually taking a quiz. `QuizCreateSerializer` is for input validation only. Showing all questions and choices on every list request would be wasteful — over-fetching data the frontend doesn't need. Having separate serializers for different purposes is called 'right-sizing your responses'."

---

### Q: How do permissions work in your API?
**A:**
"I use three levels. `AllowAny` for public endpoints — registration, login, and API docs. `IsAuthenticated` for everything else — the user must send a valid JWT token. Then within views, I do manual ownership checks — for example, when deleting a quiz, I check `quiz.created_by == request.user` and return 403 if they don't match. For private quizzes, I check ownership before allowing access. DRF handles the token verification automatically — I just declare the permission class."

---

## SECTION 4: Authentication Questions

### Q: How does JWT authentication work in your system?
**A:**
"When a user logs in with email and password, the server verifies the credentials and generates two tokens — an access token and a refresh token. The access token is valid for 1 hour and must be sent in the Authorization header with every request as `Bearer <token>`. The server verifies the token's cryptographic signature using the SECRET_KEY — no database lookup needed. When the access token expires, the client uses the refresh token (valid 7 days) to get a new access token without logging in again."

---

### Q: Why two tokens? Why not just one long-lived token?
**A:**
"Security. If someone steals your token, we want to limit the damage window. The access token expires in 1 hour — so a stolen token is only useful for a short time. The refresh token lives longer but is used less frequently and can be stored more securely. If we had one token that lived for 7 days, a theft would give an attacker a full week of access. The two-token system is the industry standard for this reason."

---

### Q: How are passwords stored?
**A:**
"Passwords are never stored in plain text. Django uses PBKDF2 with SHA-256 hashing plus a random salt. When a user registers, the password is hashed before being saved. When they log in, the entered password is hashed and compared to the stored hash. Even if the database is compromised, the actual passwords cannot be recovered."

---

## SECTION 5: AI Integration Questions

### Q: How does the AI integration work?
**A:**
"When a user creates a quiz, I call `generate_quiz_questions()` in `ai_service.py`. This function builds a prompt that instructs the AI to generate a specific number of questions at a specific difficulty, and return them as a JSON array in a specific format. I send this to Groq's API which runs the Llama 3.3 70B model. The response comes back as text, I strip any markdown formatting, parse the JSON, and validate each question — checking that it has exactly 4 choices and exactly 1 correct answer. Then I save everything to the database."

---

### Q: Why Groq? Why not Gemini or OpenAI?
**A:**
"I originally chose Google Gemini because it has a free tier. However, the API returned `limit: 0` for my account — zero quota assigned — which can happen based on region or account type. The AI Studio chat interface worked fine because it uses a different quota system than the programmatic API. I switched to Groq because it provides a genuinely free tier with no quota issues, very fast inference on Llama 3.3 70B, and a simple API. I designed the `ai_service.py` module to be swappable — if we wanted to switch to OpenAI or Claude, we'd only change that one file."

---

### Q: What if the AI returns bad data?
**A:**
"Multiple layers of protection. First, the prompt explicitly tells the AI the exact JSON format. Second, we strip markdown code blocks in case the AI wraps the response. Third, we validate: is it a list? Does each question have `text` and `choices`? Does each question have exactly 4 choices? Exactly 1 correct answer? If any validation fails, we raise a ValueError, the quiz is marked `failed`, and a 503 error is returned. The `transaction.atomic()` block ensures no partial data is saved — if saving question 3 fails after questions 1 and 2 were saved, the database rolls back to before any were saved."

---

### Q: What is the AI rate limit and why?
**A:**
"AI generation is the most expensive operation — it involves a network call to an external service. I have a separate `AIGenerationThrottle` that limits users to 20 quiz creations per hour. This prevents abuse — someone writing a script that creates hundreds of quizzes and hammers the Groq API. The standard user throttle covers all other endpoints."

---

## SECTION 6: Performance Questions

### Q: What performance optimizations did you implement?
**A:**
"Four main ones. First, database indexes on all frequently filtered fields — topic, difficulty, created_by, and composite indexes on attempt status. Second, `select_related()` in views that need related data — this reduces multiple database queries to one JOIN query. Third, pagination on all list endpoints — we return 10 results per page instead of dumping thousands of records. Fourth, pre-aggregated UserStats — stats are calculated once on write, not recalculated on every read."

---

### Q: What is N+1 query problem and how did you avoid it?
**A:**
"The N+1 problem is when you load a list of objects and then make a separate database query for each one to get related data. For example, if you load 10 attempts and then query the quiz for each one, that's 11 queries. I avoid this using `select_related('quiz')` which tells Django to fetch the attempt and its related quiz in a single SQL JOIN query — always 1 query regardless of list size."

---

### Q: How would you scale this system?
**A:**
"Several ways. First, add Redis for caching — cache the leaderboard since it doesn't need to be real-time, cache frequent quiz lookups. Second, move AI generation to a background task with Celery — instead of making the user wait during the HTTP request, queue the generation job and notify when ready. Third, add database read replicas — route read queries to replicas, write queries to the primary. Fourth, add CDN for static files. Fifth, horizontal scaling — run multiple gunicorn instances behind a load balancer."

---

## SECTION 7: Code Quality Questions

### Q: How did you handle error responses?
**A:**
"Consistently. Every error returns a JSON object with an `error` key and a descriptive message. Validation errors from serializers return 400 with field-level messages. Permission errors return 403. Not found returns 404. AI failures return 503 with the detail message. This makes it easy for frontend developers to handle errors programmatically — they always know what to expect."

---

### Q: Why did you use `transaction.atomic()`?
**A:**
"Database transactions are all-or-nothing operations. When saving quiz questions, I loop through potentially 20 questions and 80 choices. If the 15th question fails to save due to any error, I don't want the first 14 to remain in the database — that's corrupted partial data. `transaction.atomic()` wraps all the saves in one transaction — if anything fails, everything is rolled back to the state before any saves happened."

---

### Q: What is the difference between authentication and authorization?
**A:**
"Authentication answers 'who are you?' — verifying your identity with a JWT token. Authorization answers 'what are you allowed to do?' — checking if you have permission to perform an action. In my API, JWT handles authentication. Authorization is handled by permission classes (`IsAuthenticated`) and manual ownership checks (can you delete this quiz?). They're separate concerns and I handle them separately."

---

## SECTION 8: Deployment Questions

### Q: How is your app deployed?
**A:**
"It's deployed on Railway. The code lives on GitHub. When I push to GitHub, Railway automatically detects the change and deploys. Railway provides a managed PostgreSQL database — the connection URL is injected as an environment variable. The app uses Gunicorn as the production web server, Whitenoise to serve static files, and all secrets are stored as Railway environment variables — never in the code."

---

### Q: Why Gunicorn? Why not use Django's built-in server?
**A:**
"Django's development server is single-threaded — it handles one request at a time. If two users make a request simultaneously, one has to wait. Gunicorn is a production WSGI server that spawns multiple worker processes, each handling requests independently. It's built for real traffic. Django's own docs say never use the dev server in production."

---

### Q: What is Whitenoise and why do you need it?
**A:**
"In production, Django doesn't serve static files (CSS, JavaScript for the admin panel) — that's considered the web server's job. Whitenoise is a Python middleware that handles static file serving efficiently from within the Django app. This means we don't need a separate nginx or CDN setup — Whitenoise compresses and caches the files automatically."

---

### Q: How do you handle different environments (local vs production)?
**A:**
"Through environment variables loaded from a `.env` file locally and set directly on Railway in production. The `settings.py` uses `os.getenv()` to read these. The database switches automatically — if `DATABASE_URL` is set (Railway injects this for PostgreSQL), we use PostgreSQL; otherwise we fall back to SQLite. `DEBUG` is `True` locally and `False` in production. Secrets like `SECRET_KEY` and `GROQ_API_KEY` are never hardcoded."

---

## SECTION 9: Live Modification Questions

These are questions where the interviewer might ask you to change something on the spot.

### Q: Can you add a field to track how many times a quiz has been taken?
**A:**
"I actually already have this — it's the `attempt_count` property on the Quiz model:
```python
@property
def attempt_count(self):
    return self.attempts.count()
```
It dynamically counts related QuizAttempt records. If I needed it to be faster at scale, I'd add a counter field to the Quiz model and increment it using `F()` expressions to avoid race conditions:
```python
Quiz.objects.filter(id=quiz_id).update(attempt_count=F('attempt_count') + 1)
```"

---

### Q: How would you add a feature where users can report bad questions?
**A:**
"I'd add a `QuestionReport` model with fields: `question` (FK), `reported_by` (FK to User), `reason` (text), `created_at`. Add a POST endpoint `/api/questions/<id>/report/`. In the admin panel, staff can review and delete flagged questions. If a question gets more than X reports, it could be auto-hidden by adding an `is_flagged` boolean to the Question model."

---

### Q: How would you add email verification on registration?
**A:**
"Add an `is_verified` boolean to the User model, defaulting to False. On registration, generate a unique token, save it, and send an email with a verification link. Add a GET endpoint `/api/auth/verify/<token>/` that sets `is_verified=True`. In the login view, check `is_verified` and return an error if not verified. Django has built-in email sending — just configure SMTP settings."

---

## SECTION 10: Trade-off Discussion Questions

### Q: What would you do differently if you had more time?
**A:**
"A few things. First, async AI generation — currently the user waits during the HTTP request while AI generates questions. I'd use Celery with Redis to queue this as a background job and use websockets or polling to notify the user when ready. Second, more comprehensive test coverage — I'd add unit tests for scoring logic, serializer validation, and integration tests for the full quiz flow. Third, caching the leaderboard with Redis since it doesn't need to be real-time. Fourth, restricting CORS to specific frontend domains instead of allowing all origins."

---

### Q: What are the limitations of your current design?
**A:**
"A few honest ones. The AI generation is synchronous — for slow AI responses, users experience latency on quiz creation. The streak tracking is simple — it only counts consecutive passed quizzes without considering time gaps between them. The leaderboard minimum of 3 quizzes is arbitrary. SQLite for local development means we can't test PostgreSQL-specific behaviour locally without extra setup. And there's no email notification system."

---

### Q: How would you handle the case where Groq goes down?
**A:**
"Currently, we return a 503 error and mark the quiz as `failed`. To handle this more gracefully, I'd add retry logic with exponential backoff — try 3 times with increasing delays. I'd also consider adding a fallback AI provider — if Groq fails, try Gemini. In the admin panel, staff could manually trigger regeneration for failed quizzes. For critical production systems, I'd store the quiz request and retry it as a background job."

---

## QUICK REFERENCE: Key Numbers to Remember

| Setting | Value | Why |
|---------|-------|-----|
| Access token lifetime | 1 hour | Security — limits theft window |
| Refresh token lifetime | 7 days | Convenience — don't log in daily |
| Max questions per quiz | 20 | Reasonable UX limit |
| Min questions per quiz | 1 | Flexibility |
| Passing score | 60% | Standard passing grade |
| Leaderboard entries | Top 20 | Reasonable display limit |
| Min quizzes for leaderboard | 3 | Ensures meaningful average |
| AI rate limit | 20/hour | Prevents API abuse |
| Default page size | 10 | Balanced load vs usability |

---

## QUICK REFERENCE: Key Terms to Know

**REST API** — A way of building web services where URLs represent resources and HTTP methods represent actions (GET=read, POST=create, DELETE=remove).

**JWT (JSON Web Token)** — A signed token that proves who you are without the server needing to check a database.

**Serializer** — Converts Python objects to JSON (and validates incoming JSON).

**ORM (Object-Relational Mapper)** — Django's way of interacting with the database using Python code instead of SQL.

**Migration** — A file that describes changes to the database schema (adding a table, adding a column). Applied with `python manage.py migrate`.

**WSGI** — The interface between Python web apps and web servers. Gunicorn is a WSGI server.

**Foreign Key (FK)** — A field that links one database row to a row in another table.

**Atomic Transaction** — A database operation where either everything succeeds or nothing does — no partial states.

**Denormalization** — Storing redundant data to improve read performance (e.g. storing `is_correct` in UserAnswer).

**Pre-aggregation** — Computing and storing summary data in advance so reads are fast.

**N+1 Problem** — Making N extra database queries for N objects in a list. Solved with `select_related()`.

**Index** — A database structure that speeds up lookups on a specific column at the cost of slightly slower writes.

**Throttling** — Rate limiting — restricting how many requests a user can make in a time window.

**CORS (Cross-Origin Resource Sharing)** — Browser security feature that controls which domains can make requests to your API.
