import json
import re
from groq import Groq
from django.conf import settings


def generate_quiz_questions(topic: str, difficulty: str, count: int) -> list:
    """
    Call Groq API to generate quiz questions using Llama.
    Returns a list of question dicts or raises an exception.
    """
    if difficulty == 'easy':
        diff_desc = 'simple facts and definitions'
    elif difficulty == 'medium':
        diff_desc = 'conceptual understanding and application'
    else:
        diff_desc = 'advanced analysis and edge cases'

    prompt = f"""Generate {count} multiple choice quiz questions about "{topic}" at {difficulty} difficulty level ({diff_desc}).

Return ONLY a valid JSON array. No markdown, no explanation, just the JSON.

Format:
[
  {{
    "text": "Question text here?",
    "explanation": "Brief explanation of the correct answer.",
    "choices": [
      {{"text": "Option A", "is_correct": false}},
      {{"text": "Option B", "is_correct": true}},
      {{"text": "Option C", "is_correct": false}},
      {{"text": "Option D", "is_correct": false}}
    ]
  }}
]

Rules:
- Each question must have exactly 4 choices
- Exactly one choice must be correct
- Questions must be clear and unambiguous
- Return exactly {count} questions"""

    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.7,
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown code blocks if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    questions = json.loads(raw)

    if not isinstance(questions, list):
        raise ValueError("AI did not return a list of questions.")

    for i, q in enumerate(questions):
        if 'text' not in q or 'choices' not in q:
            raise ValueError(f"Question {i+1} is missing required fields.")
        correct_count = sum(1 for c in q['choices'] if c.get('is_correct'))
        if correct_count != 1:
            raise ValueError(f"Question {i+1} must have exactly one correct answer.")
        if len(q['choices']) != 4:
            raise ValueError(f"Question {i+1} must have exactly 4 choices.")

    return questions
