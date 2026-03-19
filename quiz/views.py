from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import Quiz, Question, Choice, QuizAttempt, UserAnswer, UserStats
from .serializers import (
    QuizListSerializer, QuizDetailSerializer, QuizCreateSerializer,
    AttemptSubmitSerializer, AttemptResultSerializer, AttemptListSerializer,
    LeaderboardSerializer, UserStatsSerializer,
)
from .ai_service import generate_quiz_questions


class AIGenerationThrottle(UserRateThrottle):
    scope = 'ai_generation'


# ─── Quiz Views ───────────────────────────────────────────────────────────────

@extend_schema(tags=['Quizzes'])
class QuizListView(generics.ListAPIView):
    """Browse all public quizzes. Results cached for 2 minutes."""
    serializer_class = QuizListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        topic = self.request.query_params.get('topic', '')
        difficulty = self.request.query_params.get('difficulty', '')
        cache_key = f'quiz_list_{topic}_{difficulty}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        qs = Quiz.objects.filter(status='ready', is_public=True)
        if topic:
            qs = qs.filter(topic__icontains=topic)
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        qs = list(qs)
        cache.set(cache_key, qs, settings.CACHE_TTL_QUIZ_LIST)
        return qs


@extend_schema(tags=['Quizzes'])
class MyQuizListView(generics.ListAPIView):
    """List all quizzes created by the authenticated user."""
    serializer_class = QuizListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Quiz.objects.filter(created_by=self.request.user)


@extend_schema(tags=['Quizzes'])
class QuizCreateView(generics.CreateAPIView):
    """
    Create a new quiz and trigger AI question generation.
    The quiz is saved immediately; questions are generated synchronously.
    """
    serializer_class = QuizCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIGenerationThrottle]

    def perform_create(self, serializer):
        quiz = serializer.save(created_by=self.request.user, status='draft')
        self._generate_and_save_questions(quiz)

    def _generate_and_save_questions(self, quiz):
        try:
            questions_data = generate_quiz_questions(
                topic=quiz.topic,
                difficulty=quiz.difficulty,
                count=quiz.question_count,
            )
            with transaction.atomic():
                for i, q_data in enumerate(questions_data):
                    question = Question.objects.create(
                        quiz=quiz,
                        text=q_data['text'],
                        explanation=q_data.get('explanation', ''),
                        order=i + 1,
                    )
                    for c_data in q_data['choices']:
                        Choice.objects.create(
                            question=question,
                            text=c_data['text'],
                            is_correct=c_data['is_correct'],
                        )
                quiz.status = 'ready'
                quiz.save()
                # Invalidate quiz list cache so new quiz appears immediately
                cache.delete_pattern('quiz_list_*') if hasattr(cache, 'delete_pattern') else cache.clear()
        except Exception as e:
            quiz.status = 'failed'
            quiz.save()
            raise e

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except Exception as e:
            return Response(
                {'error': 'AI generation failed.', 'detail': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        return Response(
            QuizDetailSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Quizzes'])
class QuizDetailView(generics.RetrieveDestroyAPIView):
    """
    GET: Retrieve a quiz with all questions (for taking the quiz).
    DELETE: Only the quiz creator can delete their quiz.
    """
    serializer_class = QuizDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Quiz.objects.filter(status='ready')

    def destroy(self, request, *args, **kwargs):
        quiz = self.get_object()
        if quiz.created_by != request.user:
            return Response(
                {'error': 'You can only delete your own quizzes.'},
                status=status.HTTP_403_FORBIDDEN
            )
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Attempt Views ────────────────────────────────────────────────────────────

@extend_schema(tags=['Attempts'])
class StartAttemptView(APIView):
    """Start a new quiz attempt. Prevents duplicate in-progress attempts."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, quiz_id):
        try:
            quiz = Quiz.objects.get(id=quiz_id, status='ready')
        except Quiz.DoesNotExist:
            return Response({'error': 'Quiz not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Block access to private quizzes from other users
        if not quiz.is_public and quiz.created_by != request.user:
            return Response({'error': 'This quiz is private.'}, status=status.HTTP_403_FORBIDDEN)

        # Prevent duplicate in-progress attempts
        existing = QuizAttempt.objects.filter(
            user=request.user, quiz=quiz, status='in_progress'
        ).first()
        if existing:
            return Response(
                {'error': 'You already have an in-progress attempt for this quiz.', 'attempt_id': existing.id},
                status=status.HTTP_400_BAD_REQUEST
            )

        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            total_questions=quiz.questions.count(),
        )
        return Response(
            {'attempt_id': attempt.id, 'quiz_id': quiz.id, 'total_questions': attempt.total_questions},
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Attempts'], request=AttemptSubmitSerializer, responses=AttemptResultSerializer)
class SubmitAttemptView(APIView):
    """Submit all answers for an attempt and receive scored results."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, attempt_id):
        try:
            attempt = QuizAttempt.objects.select_related('quiz').get(
                id=attempt_id, user=request.user
            )
        except QuizAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found.'}, status=status.HTTP_404_NOT_FOUND)

        if attempt.status != 'in_progress':
            return Response(
                {'error': f'Attempt is already {attempt.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check time limit
        if attempt.quiz.time_limit_minutes:
            elapsed = (timezone.now() - attempt.started_at).total_seconds() / 60
            if elapsed > attempt.quiz.time_limit_minutes:
                attempt.status = 'timed_out'
                attempt.completed_at = timezone.now()
                attempt.save()
                return Response(
                    {'error': 'Time limit exceeded. Attempt marked as timed out.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = AttemptSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answers_data = serializer.validated_data['answers']

        # Validate all question/choice IDs belong to this quiz
        quiz_question_ids = set(
            attempt.quiz.questions.values_list('id', flat=True)
        )
        for answer in answers_data:
            if answer['question_id'] not in quiz_question_ids:
                return Response(
                    {'error': f"Question {answer['question_id']} does not belong to this quiz."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                choice = Choice.objects.get(
                    id=answer['choice_id'],
                    question_id=answer['question_id']
                )
            except Choice.DoesNotExist:
                return Response(
                    {'error': f"Choice {answer['choice_id']} is not valid for question {answer['question_id']}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Save answers and calculate score
        correct_count = 0
        with transaction.atomic():
            for answer in answers_data:
                choice = Choice.objects.get(
                    id=answer['choice_id'],
                    question_id=answer['question_id']
                )
                is_correct = choice.is_correct
                if is_correct:
                    correct_count += 1

                UserAnswer.objects.get_or_create(
                    attempt=attempt,
                    question_id=answer['question_id'],
                    defaults={'chosen_choice': choice, 'is_correct': is_correct}
                )

            now = timezone.now()
            attempt.correct_answers = correct_count
            attempt.score = round((correct_count / attempt.total_questions) * 100, 1) if attempt.total_questions else 0
            attempt.status = 'completed'
            attempt.completed_at = now
            attempt.time_taken_seconds = int((now - attempt.started_at).total_seconds())
            attempt.save()

        # Update user stats
        stats, _ = UserStats.objects.get_or_create(user=request.user)
        stats.update_after_attempt(attempt)

        return Response(AttemptResultSerializer(attempt).data, status=status.HTTP_200_OK)


@extend_schema(tags=['Attempts'])
class AbandonAttemptView(APIView):
    """Abandon an in-progress attempt."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, attempt_id):
        try:
            attempt = QuizAttempt.objects.get(
                id=attempt_id, user=request.user, status='in_progress'
            )
        except QuizAttempt.DoesNotExist:
            return Response(
                {'error': 'In-progress attempt not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        attempt.status = 'abandoned'
        attempt.completed_at = timezone.now()
        attempt.save()
        return Response({'message': 'Attempt abandoned.'}, status=status.HTTP_200_OK)


# ─── Analytics Views ──────────────────────────────────────────────────────────

@extend_schema(tags=['Analytics'])
class MyHistoryView(generics.ListAPIView):
    """List all completed quiz attempts for the authenticated user."""
    serializer_class = AttemptListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return QuizAttempt.objects.filter(
            user=self.request.user,
            status='completed'
        ).select_related('quiz')


@extend_schema(tags=['Analytics'])
class MyStatsView(APIView):
    """Get the authenticated user's overall stats and streak."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        stats, _ = UserStats.objects.get_or_create(user=request.user)
        return Response(UserStatsSerializer(stats).data)


@extend_schema(tags=['Analytics'])
class LeaderboardView(generics.ListAPIView):
    """Top users ranked by average score (minimum 3 quizzes taken). Cached for 5 minutes."""
    serializer_class = LeaderboardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        cache_key = 'leaderboard_top20'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        qs = list(
            UserStats.objects.filter(
                total_quizzes_taken__gte=3
            ).select_related('user').order_by('-average_score', '-best_streak')[:20]
        )
        cache.set(cache_key, qs, settings.CACHE_TTL_LEADERBOARD)
        return qs
