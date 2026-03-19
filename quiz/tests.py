from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from .models import Quiz, Question, Choice, QuizAttempt, UserAnswer, UserStats

User = get_user_model()

QUIZ_LIST_URL = '/api/v1/quizzes/'
QUIZ_CREATE_URL = '/api/v1/quizzes/create/'
HISTORY_URL = '/api/v1/quizzes/history/'
STATS_URL = '/api/v1/quizzes/stats/'
LEADERBOARD_URL = '/api/v1/quizzes/leaderboard/'


def create_user(email='user@example.com', username='user', password='TestPass123!'):
    return User.objects.create_user(email=email, username=username, password=password)


def create_quiz(user, topic='Python', difficulty='easy', question_count=3, status='ready'):
    return Quiz.objects.create(
        title=f'{topic} Quiz',
        topic=topic,
        difficulty=difficulty,
        question_count=question_count,
        created_by=user,
        is_public=True,
        status=status,
    )


def create_question_with_choices(quiz, text='What is Python?', order=1):
    question = Question.objects.create(
        quiz=quiz,
        text=text,
        explanation='Python is a high-level language.',
        order=order,
    )
    correct = Choice.objects.create(question=question, text='A high-level language', is_correct=True)
    Choice.objects.create(question=question, text='A database', is_correct=False)
    Choice.objects.create(question=question, text='A markup language', is_correct=False)
    Choice.objects.create(question=question, text='An OS', is_correct=False)
    return question, correct


class QuizModelTests(TestCase):

    def setUp(self):
        self.user = create_user()

    def test_quiz_str(self):
        """Quiz __str__ returns title and difficulty."""
        quiz = create_quiz(self.user)
        self.assertIn('Python', str(quiz))
        self.assertIn('easy', str(quiz))

    def test_quiz_attempt_count_property(self):
        """attempt_count returns correct number of attempts."""
        quiz = create_quiz(self.user)
        self.assertEqual(quiz.attempt_count, 0)
        QuizAttempt.objects.create(user=self.user, quiz=quiz, total_questions=3)
        self.assertEqual(quiz.attempt_count, 1)

    def test_quiz_attempt_percentage(self):
        """percentage property calculates correctly."""
        quiz = create_quiz(self.user)
        attempt = QuizAttempt.objects.create(
            user=self.user, quiz=quiz,
            total_questions=4, correct_answers=3
        )
        self.assertEqual(attempt.percentage, 75.0)

    def test_quiz_attempt_passed(self):
        """passed is True when score >= 60%."""
        quiz = create_quiz(self.user)
        attempt = QuizAttempt.objects.create(
            user=self.user, quiz=quiz,
            total_questions=10, correct_answers=6
        )
        self.assertTrue(attempt.passed)

    def test_quiz_attempt_failed(self):
        """passed is False when score < 60%."""
        quiz = create_quiz(self.user)
        attempt = QuizAttempt.objects.create(
            user=self.user, quiz=quiz,
            total_questions=10, correct_answers=5
        )
        self.assertFalse(attempt.passed)


class UserStatsTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.quiz = create_quiz(self.user)

    def _make_attempt(self, correct, total):
        from django.utils import timezone
        attempt = QuizAttempt.objects.create(
            user=self.user,
            quiz=self.quiz,
            total_questions=total,
            correct_answers=correct,
            status='completed',
            score=round((correct / total) * 100, 1),
            completed_at=timezone.now(),
        )
        return attempt

    def test_streak_increases_on_pass(self):
        """Streak increases when quiz is passed."""
        stats, _ = UserStats.objects.get_or_create(user=self.user)
        attempt = self._make_attempt(8, 10)  # 80% — pass
        stats.update_after_attempt(attempt)
        self.assertEqual(stats.current_streak, 1)

    def test_streak_resets_on_fail(self):
        """Streak resets to 0 when quiz is failed."""
        stats, _ = UserStats.objects.get_or_create(user=self.user)
        pass_attempt = self._make_attempt(8, 10)
        stats.update_after_attempt(pass_attempt)
        self.assertEqual(stats.current_streak, 1)

        fail_attempt = self._make_attempt(3, 10)  # 30% — fail
        stats.update_after_attempt(fail_attempt)
        self.assertEqual(stats.current_streak, 0)

    def test_best_streak_never_decreases(self):
        """best_streak stays at highest value even after streak resets."""
        stats, _ = UserStats.objects.get_or_create(user=self.user)
        for _ in range(3):
            stats.update_after_attempt(self._make_attempt(8, 10))
        self.assertEqual(stats.best_streak, 3)

        stats.update_after_attempt(self._make_attempt(3, 10))  # fail
        self.assertEqual(stats.current_streak, 0)
        self.assertEqual(stats.best_streak, 3)  # still 3

    def test_average_score_calculation(self):
        """Average score is correctly calculated across attempts."""
        stats, _ = UserStats.objects.get_or_create(user=self.user)
        stats.update_after_attempt(self._make_attempt(10, 10))  # 100%
        stats.update_after_attempt(self._make_attempt(6, 10))   # 60%
        # 16 correct out of 20 total = 80%
        self.assertEqual(stats.average_score, 80.0)


class QuizAPITests(TestCase):

    def setUp(self):
        cache.clear()  # prevent cached results from bleeding between tests
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)

    def test_list_public_quizzes(self):
        """Public ready quizzes are listed."""
        create_quiz(self.user, status='ready')
        response = self.client.get(QUIZ_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['count'], 0)

    def test_draft_quizzes_not_listed(self):
        """Draft quizzes don't appear in the public list."""
        create_quiz(self.user, status='draft')
        response = self.client.get(QUIZ_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_filter_by_difficulty(self):
        """Quiz list can be filtered by difficulty."""
        other_user = create_user(email='other@example.com', username='otheruser')
        create_quiz(self.user, difficulty='easy', status='ready')
        create_quiz(other_user, difficulty='hard', status='ready')
        response = self.client.get(QUIZ_LIST_URL + '?difficulty=easy')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for quiz in response.data['results']:
            self.assertEqual(quiz['difficulty'], 'easy')

    def test_quiz_list_requires_auth(self):
        """Unauthenticated users cannot list quizzes."""
        unauthenticated = APIClient()
        response = unauthenticated.get(QUIZ_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AttemptAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.quiz = create_quiz(self.user, status='ready')
        self.question, self.correct_choice = create_question_with_choices(self.quiz)

    def test_start_attempt(self):
        """User can start a quiz attempt."""
        response = self.client.post(f'/api/v1/quizzes/{self.quiz.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('attempt_id', response.data)

    def test_duplicate_attempt_blocked(self):
        """Starting a second attempt on the same quiz returns existing attempt."""
        self.client.post(f'/api/v1/quizzes/{self.quiz.id}/start/')
        response = self.client.post(f'/api/v1/quizzes/{self.quiz.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('attempt_id', response.data)

    def test_submit_correct_answer(self):
        """Submitting all correct answers gives 100% score."""
        start = self.client.post(f'/api/v1/quizzes/{self.quiz.id}/start/')
        attempt_id = start.data['attempt_id']

        response = self.client.post(
            f'/api/v1/quizzes/attempts/{attempt_id}/submit/',
            {'answers': [{'question_id': self.question.id, 'choice_id': self.correct_choice.id}]},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['score'], 100.0)
        self.assertTrue(response.data['passed'])

    def test_submit_wrong_answer(self):
        """Submitting wrong answers gives 0% score."""
        wrong_choice = Choice.objects.filter(
            question=self.question, is_correct=False
        ).first()
        start = self.client.post(f'/api/v1/quizzes/{self.quiz.id}/start/')
        attempt_id = start.data['attempt_id']

        response = self.client.post(
            f'/api/v1/quizzes/attempts/{attempt_id}/submit/',
            {'answers': [{'question_id': self.question.id, 'choice_id': wrong_choice.id}]},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['score'], 0.0)
        self.assertFalse(response.data['passed'])

    def test_cannot_submit_to_completed_attempt(self):
        """Submitting to an already completed attempt returns 400."""
        start = self.client.post(f'/api/v1/quizzes/{self.quiz.id}/start/')
        attempt_id = start.data['attempt_id']
        payload = {'answers': [{'question_id': self.question.id, 'choice_id': self.correct_choice.id}]}

        self.client.post(f'/api/v1/quizzes/attempts/{attempt_id}/submit/', payload, format='json')
        response = self.client.post(f'/api/v1/quizzes/attempts/{attempt_id}/submit/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_question_id_rejected(self):
        """Submitting an answer for a question not in the quiz returns 400."""
        start = self.client.post(f'/api/v1/quizzes/{self.quiz.id}/start/')
        attempt_id = start.data['attempt_id']

        response = self.client.post(
            f'/api/v1/quizzes/attempts/{attempt_id}/submit/',
            {'answers': [{'question_id': 9999, 'choice_id': self.correct_choice.id}]},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_abandon_attempt(self):
        """User can abandon an in-progress attempt."""
        start = self.client.post(f'/api/v1/quizzes/{self.quiz.id}/start/')
        attempt_id = start.data['attempt_id']
        response = self.client.post(f'/api/v1/quizzes/attempts/{attempt_id}/abandon/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_history_shows_completed_attempts(self):
        """Completed attempts appear in history."""
        start = self.client.post(f'/api/v1/quizzes/{self.quiz.id}/start/')
        attempt_id = start.data['attempt_id']
        self.client.post(
            f'/api/v1/quizzes/attempts/{attempt_id}/submit/',
            {'answers': [{'question_id': self.question.id, 'choice_id': self.correct_choice.id}]},
            format='json'
        )
        response = self.client.get(HISTORY_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_stats_updated_after_attempt(self):
        """User stats are updated after completing an attempt."""
        start = self.client.post(f'/api/v1/quizzes/{self.quiz.id}/start/')
        attempt_id = start.data['attempt_id']
        self.client.post(
            f'/api/v1/quizzes/attempts/{attempt_id}/submit/',
            {'answers': [{'question_id': self.question.id, 'choice_id': self.correct_choice.id}]},
            format='json'
        )
        response = self.client.get(STATS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_quizzes_taken'], 1)
        self.assertEqual(response.data['current_streak'], 1)
