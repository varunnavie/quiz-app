from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Confirm password')

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'password2')

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    stats = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'date_joined', 'stats')
        read_only_fields = ('id', 'email', 'date_joined')

    def get_stats(self, obj):
        try:
            s = obj.stats
            return {
                'total_quizzes_taken': s.total_quizzes_taken,
                'average_score': s.average_score,
                'current_streak': s.current_streak,
                'best_streak': s.best_streak,
                'total_correct_answers': s.total_correct_answers,
                'total_questions_answered': s.total_questions_answered,
            }
        except Exception:
            return None
