from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Quiz(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]

    title = models.CharField(max_length=255)
    topic = models.CharField(max_length=255)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    question_count = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quizzes'
    )
    is_public = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    time_limit_minutes = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Optional time limit in minutes. Leave blank for unlimited.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['topic']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.title} ({self.difficulty})"

    @property
    def attempt_count(self):
        return self.attempts.count()


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    explanation = models.TextField(
        blank=True,
        help_text='Explanation shown after answering'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        marker = '✓' if self.is_correct else '✗'
        return f"{marker} {self.text[:50]}"


class QuizAttempt(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
        ('timed_out', 'Timed Out'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='in_progress')
    score = models.FloatField(null=True, blank=True, help_text='Percentage score 0-100')
    correct_answers = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['quiz', 'status']),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.quiz.title} ({self.status})"

    @property
    def percentage(self):
        if self.total_questions == 0:
            return 0
        return round((self.correct_answers / self.total_questions) * 100, 1)

    @property
    def passed(self):
        return self.percentage >= 60


class UserAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name='user_answers')
    chosen_choice = models.ForeignKey(
        Choice,
        on_delete=models.PROTECT,
        related_name='user_answers',
        null=True,
        blank=True
    )
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One answer per question per attempt
        unique_together = ('attempt', 'question')

    def __str__(self):
        return f"Attempt#{self.attempt.id} Q#{self.question.id} — {'✓' if self.is_correct else '✗'}"


class UserStats(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stats'
    )
    total_quizzes_taken = models.PositiveIntegerField(default=0)
    total_correct_answers = models.PositiveIntegerField(default=0)
    total_questions_answered = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0, help_text='Consecutive quizzes passed')
    best_streak = models.PositiveIntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    last_activity = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} — streak: {self.current_streak}"

    def update_after_attempt(self, attempt):
        """Recalculate stats after a completed attempt."""
        self.total_quizzes_taken += 1
        self.total_correct_answers += attempt.correct_answers
        self.total_questions_answered += attempt.total_questions
        self.last_activity = attempt.completed_at

        # Recalculate average score
        if self.total_questions_answered > 0:
            self.average_score = round(
                (self.total_correct_answers / self.total_questions_answered) * 100, 1
            )

        # Update streak
        if attempt.passed:
            self.current_streak += 1
            if self.current_streak > self.best_streak:
                self.best_streak = self.current_streak
        else:
            self.current_streak = 0

        self.save()
