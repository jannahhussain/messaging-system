import unittest
import time
from app import create_app, db
from models import User, Message
from flask import json
from flask_login import login_user
from datetime import datetime

class LoadTestCase(unittest.TestCase):
    """Test case for load testing the application."""

    def setUp(self):
        """Set up the app and test client for load testing."""
        self.app = create_app('testing')  # Use the testing configuration
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create test users
        self.user = User(
            username="testuser",
            email="testuser@example.com",
            password="userpassword",
            role="user",
            created_at=datetime.utcnow()
        )
        db.session.add(self.user)
        db.session.commit()

        # Create messages for load testing
        self.messages = []
        for i in range(1000):  # Create 1000 messages
            message = Message(
                sender_id=self.user.id,
                content=f"This is test message {i}",
                created_at=datetime.utcnow()
            )
            self.messages.append(message)

        db.session.bulk_save_objects(self.messages)
        db.session.commit()

    def tearDown(self):
        """Teardown the test client and clean up the database."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # Test Load for User Login
    def test_user_login_load(self):
        """Test the load of multiple users logging in concurrently."""
        start_time = time.time()

        for i in range(100):  # Simulate 100 login requests
            response = self.client.post('/login', data={
                'email': 'testuser@example.com',
                'password': 'userpassword'
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Login successful', response.data)

        elapsed_time = time.time() - start_time
        print(f"User login load test executed in {elapsed_time} seconds.")

    # Test Load for Flagging Messages
    def test_flagging_message_load(self):
        """Test the load of flagging multiple messages."""
        start_time = time.time()

        for message in self.messages[:100]:  # Flag 100 messages
            response = self.client.post('/flag_message', json={
                'message_id': message.id,
                'reason': 'Inappropriate content'
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Message flagged successfully for review', response.data)

        elapsed_time = time.time() - start_time
        print(f"Flagging message load test executed in {elapsed_time} seconds.")

    # Test Load for Admin Reviewing Flagged Content
    def test_admin_review_flagged_content_load(self):
        """Test the load of multiple flagged content reviews by the admin."""
        start_time = time.time()

        # Flagging 100 messages for admin to review
        for message in self.messages[:100]:
            response = self.client.post('/flag_message', json={
                'message_id': message.id,
                'reason': 'Inappropriate content'
            })
            self.assertEqual(response.status_code, 200)

        flagged_content_list = [message.id for message in self.messages[:100]]

        for flagged_content_id in flagged_content_list:
            response = self.client.post(f'/review_flagged_content/{flagged_content_id}', json={
                'action': 'delete'
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Action taken: Message deleted', response.data)

        elapsed_time = time.time() - start_time
        print(f"Admin review flagged content load test executed in {elapsed_time} seconds.")

    # Test Load for Admin Dashboard Stats
    def test_admin_dashboard_load(self):
        """Test the load of fetching admin dashboard stats."""
        start_time = time.time()

        with self.client:
            login_user(self.user)  # Log in as admin
            response = self.client.get('/dashboard')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Total Users', response.data)

        elapsed_time = time.time() - start_time
        print(f"Admin dashboard load test executed in {elapsed_time} seconds.")

    # Test Load for Viewing Flagged Content
    def test_admin_view_flagged_content_load(self):
        """Test the load of admin viewing flagged content."""
        start_time = time.time()

        for message in self.messages[:100]:  # Flagging 100 messages
            response = self.client.post('/flag_message', json={
                'message_id': message.id,
                'reason': 'Inappropriate content'
            })
            self.assertEqual(response.status_code, 200)

        with self.client:
            login_user(self.user)  # Log in as admin
            response = self.client.get('/flagged-content')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Flagged Messages', response.data)

        elapsed_time = time.time() - start_time
        print(f"Admin view flagged content load test executed in {elapsed_time} seconds.")

    # Test Load for Admin Banning Users
    def test_admin_ban_user_load(self):
        """Test the load of admin banning multiple users."""
        start_time = time.time()

        for i in range(10):  # Simulate banning 10 users
            response = self.client.post(f'/ban-user/{self.user.id}')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'User testuser banned', response.data)

        elapsed_time = time.time() - start_time
        print(f"Admin ban user load test executed in {elapsed_time} seconds.")

    # Test Load for User Registration
    def test_user_registration_load(self):
        """Test the load of multiple users registering concurrently."""
        start_time = time.time()

        for i in range(100):  # Simulate 100 user registration requests
            response = self.client.post('/register', data={
                'username': f'newuser{i}',
                'email': f'newuser{i}@example.com',
                'password': 'newpassword',
                'confirm_password': 'newpassword'
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Account created successfully', response.data)

        elapsed_time = time.time() - start_time
        print(f"User registration load test executed in {elapsed_time} seconds.")

if __name__ == '__main__':
    unittest.main()
