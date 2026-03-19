from rest_framework import serializers
from .models import Quiz, Question, Choice, QuizAttempt, UserAnswer, UserStats


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ('id', 'text')


class ChoiceWithAnswerSerializer(serializers.ModelSerializer):
    """Shows whether choice is correct — only used in results."""
    class Meta:
        model = Choice
        fields = ('id', 'text', 'is_correct')


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'text', 'order', 'choices')


class QuestionWithAnswerSerializer(serializers.ModelSerializer):
    """Shows correct answer and explanation — only used in results."""
    choices = ChoiceWithAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'text', 'order', 'explanation', 'choices')


class QuizListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    created_by = serializers.StringRelatedField()
    attempt_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Quiz
        fields = (
            'id', 'title', 'topic', 'difficulty', 'question_count',
            'time_limit_minutes', 'is_public', 'status',
            'attempt_count', 'created_by', 'created_at'
        )


class QuizDetailSerializer(serializers.ModelSerializer):
    """Full quiz with questions — used when taking a quiz."""
    questions = QuestionSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Quiz
        fields = (
            'id', 'title', 'topic', 'difficulty', 'question_count',
            'time_limit_minutes', 'is_public', 'status',
            'created_by', 'created_at', 'questions'
        )


class QuizCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ('id', 'title', 'topic', 'difficulty', 'question_count', 'time_limit_minutes', 'is_public')

    def validate_question_count(self, value):
        if value < 1 or value > 20:
            raise serializers.ValidationError('Question count must be between 1 and 20.')
        return value

    def validate_topic(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Topic must be at least 2 characters.')
        return value.strip()


class UserAnswerSubmitSerializer(serializers.Serializer):
    """Used when submitting a single answer."""
    question_id = serializers.IntegerField()
    choice_id = serializers.IntegerField()


class AttemptSubmitSerializer(serializers.Serializer):
    """Used when submitting all answers at once."""
    answers = UserAnswerSubmitSerializer(many=True)

    def validate_answers(self, value):
        if len(value) == 0:
            raise serializers.ValidationError('At least one answer is required.')
        # Check for duplicate question answers
        question_ids = [a['question_id'] for a in value]
        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError('Duplicate answers for the same question.')
        return value


class UserAnswerResultSerializer(serializers.ModelSerializer):
    question = QuestionWithAnswerSerializer(read_only=True)
    chosen_choice = ChoiceWithAnswerSerializer(read_only=True)

    class Meta:
        model = UserAnswer
        fields = ('question', 'chosen_choice', 'is_correct')


class AttemptResultSerializer(serializers.ModelSerializer):
    answers = UserAnswerResultSerializer(many=True, read_only=True)
    quiz = QuizListSerializer(read_only=True)
    percentage = serializers.FloatField(read_only=True)
    passed = serializers.BooleanField(read_only=True)

    class Meta:
        model = QuizAttempt
        fields = (
            'id', 'quiz', 'status', 'score', 'correct_answers',
            'total_questions', 'percentage', 'passed',
            'started_at', 'completed_at', 'time_taken_seconds', 'answers'
        )


class AttemptListSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    quiz_topic = serializers.CharField(source='quiz.topic', read_only=True)
    percentage = serializers.FloatField(read_only=True)
    passed = serializers.BooleanField(read_only=True)

    class Meta:
        model = QuizAttempt
        fields = (
            'id', 'quiz_title', 'quiz_topic', 'status',
            'correct_answers', 'total_questions', 'percentage', 'passed',
            'started_at', 'completed_at', 'time_taken_seconds'
        )


class LeaderboardSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserStats
        fields = (
            'username', 'email', 'total_quizzes_taken',
            'average_score', 'best_streak', 'total_correct_answers'
        )


class UserStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStats
        fields = (
            'total_quizzes_taken', 'total_correct_answers',
            'total_questions_answered', 'current_streak',
            'best_streak', 'average_score', 'last_activity'
        )
