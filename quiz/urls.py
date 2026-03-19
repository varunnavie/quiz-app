from django.urls import path
from .views import (
    QuizListView, MyQuizListView, QuizCreateView, QuizDetailView,
    StartAttemptView, SubmitAttemptView, AbandonAttemptView,
    MyHistoryView, MyStatsView, LeaderboardView,
)

urlpatterns = [
    # Quizzes
    path('', QuizListView.as_view(), name='quiz-list'),
    path('mine/', MyQuizListView.as_view(), name='my-quizzes'),
    path('create/', QuizCreateView.as_view(), name='quiz-create'),
    path('<int:pk>/', QuizDetailView.as_view(), name='quiz-detail'),

    # Attempts
    path('<int:quiz_id>/start/', StartAttemptView.as_view(), name='attempt-start'),
    path('attempts/<int:attempt_id>/submit/', SubmitAttemptView.as_view(), name='attempt-submit'),
    path('attempts/<int:attempt_id>/abandon/', AbandonAttemptView.as_view(), name='attempt-abandon'),

    # Analytics
    path('history/', MyHistoryView.as_view(), name='my-history'),
    path('stats/', MyStatsView.as_view(), name='my-stats'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]
