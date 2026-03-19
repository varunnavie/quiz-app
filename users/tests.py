from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

REGISTER_URL = '/api/v1/auth/register/'
LOGIN_URL = '/api/v1/auth/login/'
PROFILE_URL = '/api/v1/auth/profile/'


class UserRegistrationTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_register_success(self):
        """A user can register with valid data."""
        payload = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        response = self.client.post(REGISTER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('email', response.data)
        self.assertNotIn('password', response.data)  # password must never be returned

    def test_register_duplicate_email(self):
        """Registration fails if email already exists."""
        User.objects.create_user(email='dup@example.com', username='existing', password='Pass123!')
        payload = {
            'email': 'dup@example.com',
            'username': 'newuser',
            'password': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        response = self.client.post(REGISTER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch(self):
        """Registration fails if passwords don't match."""
        payload = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'StrongPass123!',
            'password2': 'WrongPass123!',
        }
        response = self.client.post(REGISTER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password(self):
        """Registration fails if password is too weak."""
        payload = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': '123',
            'password2': '123',
        }
        response = self.client.post(REGISTER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        """Registration fails if required fields are missing."""
        response = self.client.post(REGISTER_URL, {'email': 'test@example.com'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserAuthenticationTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='login@example.com',
            username='loginuser',
            password='TestPass123!'
        )

    def test_login_success(self):
        """User gets access and refresh tokens on valid login."""
        response = self.client.post(LOGIN_URL, {
            'email': 'login@example.com',
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password(self):
        """Login fails with wrong password."""
        response = self.client.post(LOGIN_URL, {
            'email': 'login@example.com',
            'password': 'WrongPassword!'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        """Login fails if user doesn't exist."""
        response = self.client.post(LOGIN_URL, {
            'email': 'nobody@example.com',
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='profile@example.com',
            username='profileuser',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)

    def test_get_profile(self):
        """Authenticated user can retrieve their profile."""
        response = self.client.get(PROFILE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)

    def test_profile_requires_authentication(self):
        """Unauthenticated request to profile returns 401."""
        unauthenticated = APIClient()
        response = unauthenticated.get(PROFILE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile(self):
        """User can update their first and last name."""
        response = self.client.patch(PROFILE_URL, {
            'first_name': 'John',
            'last_name': 'Doe'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'John')
