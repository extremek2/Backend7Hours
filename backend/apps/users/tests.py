from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from faker import Faker

User = get_user_model()

class CustomUserIntegrationTest(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.faker = Faker()

        # Admin 계정 생성
        cls.admin = User.objects.create_user(
            # username='admin',
            email='admin@example.com',
            password='admin1234',
            full_name='Administrator'
        )

        # Faker 더미 유저 5명 생성
        cls.dummy_users = []
        for _ in range(5):
            user = User.objects.create_user(
                # username=cls.faker.user_name(),
                email=cls.faker.email(),
                password='test1234',
                full_name=cls.faker.name(),
                nickname=cls.faker.first_name(),
            )
            cls.dummy_users.append(user)

    def authenticate(self, email='admin@example.com', password='admin1234'):
        """JWT 토큰 발급 후 인증 헤더 설정"""
        url = reverse('token_obtain_pair')
        response = self.client.post(url, {'email': email, 'password': password}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    def test_user_list_authenticated(self):
        """로그인 후 전체 유저 조회"""
        self.authenticate()
        url = reverse('user-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 6)  # admin + 5 dummy

    def test_user_register_and_login(self):
        """회원가입 후 JWT 로그인 테스트"""
        register_url = reverse('user-register')
        new_user_data = {
            'email': 'newuser@example.com',
            'full_name': 'New User',
            'password': 'NewPass1234!',
            'password_verification': 'NewPass1234!'
        }
        # 회원가입
        response = self.client.post(register_url, new_user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'newuser@example.com')

        # 새 유저 JWT 로그인
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {'email': 'newuser@example.com', 'password': 'NewPass1234!'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_retrieve_update_delete_user(self):
        """개별 유저 조회, 수정, 삭제"""
        self.authenticate()
        user = self.dummy_users[0]
        url = reverse('user-detail', args=[user.id])

        # 조회
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], user.id)

        # 수정
        update_data = {
            'email': user.email,
            'full_name': user.full_name,
            'nickname': 'UpdatedNick'
        }
        response = self.client.put(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.nickname, 'UpdatedNick')

        # 삭제
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(id=user.id).exists())
