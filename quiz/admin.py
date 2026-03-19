from django.contrib import admin
from .models import Quiz, Question, Choice, QuizAttempt, UserAnswer, UserStats


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    max_num = 4


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'difficulty', 'question_count', 'status', 'created_by', 'attempt_count', 'created_at')
    list_filter = ('difficulty', 'status', 'is_public')
    search_fields = ('title', 'topic', 'created_by__email')
    readonly_fields = ('created_at', 'updated_at', 'attempt_count')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'order', 'text')
    list_filter = ('quiz__difficulty',)
    search_fields = ('text', 'quiz__title')
    inlines = [ChoiceInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'status', 'score', 'correct_answers', 'total_questions', 'started_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'quiz__title')
    readonly_fields = ('started_at',)


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_quizzes_taken', 'average_score', 'current_streak', 'best_streak')
    search_fields = ('user__email',)
