from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema

from .serializers import RegisterSerializer, UserProfileSerializer


@extend_schema(tags=['Auth'])
class RegisterView(generics.CreateAPIView):
    """Register a new user account."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(tags=['Profile'])
class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the authenticated user's profile."""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
