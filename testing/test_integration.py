import unittest
from app import create_app, db
from models import User, Message, FlaggedContent, ActivityLog
from flask import json
from flask_login import login_user
from datetime import datetime, timedelta


class IntegrationTestCase(unittest.TestCase):
    """Test case for integration testing of the app."""

    def setUp(self):
        """Set up the app and the test client."""
        self.app = create_app('testing')  # Use the testing configuration
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create test users
        self.admin = User(
            username="admin",
            email="admin@example.com",
            password="adminpassword",
            role="admin",
            created_at=datetime.utcnow()
        )
        self.user = User(
            username="testuser",
            email="testuser@example.com",
            password="userpassword",
            role="user",
            created_at=datetime.utcnow()
        )

        db.session.add(self.admin)
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        """Teardown the test client."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # Test User Registration
    def test_user_registration(self):
        """Test user registration process."""
        response = self.client.post('/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword',
            'confirm_password': 'newpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Account created successfully', response.data)

    # Test User Login
    def test_user_login(self):
        """Test user login functionality."""
        response = self.client.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'userpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login successful', response.data)

    # Test Admin Login
    def test_admin_login(self):
        """Test admin login functionality."""
        response = self.client.post('/login', data={
            'email': 'admin@example.com',
            'password': 'adminpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login successful', response.data)

    # Test User Logout
    def test_user_logout(self):
        """Test user logout functionality."""
        with self.client:
            login_user(self.user)
            response = self.client.get('/logout')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'You have been logged out', response.data)

    # Test Flagging a Message
    def test_flag_message(self):
        """Test flagging a message for review."""
        message = Message(
            sender_id=self.user.id,
            content="This is a test message",
            created_at=datetime.utcnow()
        )
        db.session.add(message)
        db.session.commit()

        response = self.client.post('/flag_message', json={
            'message_id': message.id,
            'reason': 'Inappropriate content'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Message flagged successfully for review', response.data)

    # Test Reviewing Flagged Content (Admin)
    def test_review_flagged_content(self):
        """Test admin reviewing flagged content."""
        message = Message(
            sender_id=self.user.id,
            content="This is a test message",
            created_at=datetime.utcnow()
        )
        db.session.add(message)
        db.session.commit()

        flagged_content = FlaggedContent(
            message_id=message.id,
            user_id=self.user.id,
            reason="Inappropriate content",
            created_at=datetime.utcnow()
        )
        db.session.add(flagged_content)
        db.session.commit()

        # Admin login
        with self.client:
            login_user(self.admin)
            response = self.client.post(f'/review_flagged_content/{flagged_content.id}', json={
                'action': 'delete'
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Action taken: Message deleted', response.data)

    # Test Banning a User (Admin)
    def test_ban_user(self):
        """Test admin banning a user."""
        with self.client:
            login_user(self.admin)
            response = self.client.post(f'/ban-user/{self.user.id}')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'User testuser banned', response.data)

    # Test Suspending a User (Admin)
    def test_suspend_user(self):
        """Test admin suspending a user."""
        with self.client:
            login_user(self.admin)
            response = self.client.post(f'/suspend-user/{self.user.id}')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'User testuser suspended', response.data)

    # Test Admin Dashboard Stats
    def test_admin_dashboard_stats(self):
        """Test admin retrieving stats on the dashboard."""
        with self.client:
            login_user(self.admin)
            response = self.client.get('/dashboard')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Total Users', response.data)

    # Test Accessing Unauthorized Pages (Admin)
    def test_unauthorized_admin_access(self):
        """Test non-admin user accessing admin pages."""
        with self.client:
            login_user(self.user)
            response = self.client.get('/dashboard')
            self.assertEqual(response.status_code, 403)
            self.assertIn(b'Unauthorized', response.data)

    # Test Viewing Flagged Content (Admin)
    def test_view_flagged_content(self):
        """Test admin viewing flagged content."""
        message = Message(
            sender_id=self.user.id,
            content="This is a test message",
            created_at=datetime.utcnow()
        )
        db.session.add(message)
        db.session.commit()

        flagged_content = FlaggedContent(
            message_id=message.id,
            user_id=self.user.id,
            reason="Inappropriate content",
            created_at=datetime.utcnow()
        )
        db.session.add(flagged_content)
        db.session.commit()

        with self.client:
            login_user(self.admin)
            response = self.client.get('/flagged-content')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Flagged Messages', response.data)

    # Test Admin Viewing Recent Activity
    def test_admin_activity_log(self):
        """Test admin viewing activity log."""
        log = ActivityLog(
            user_id=self.admin.id,
            action="Logged in",
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()

        with self.client:
            login_user(self.admin)
            response = self.client.get('/activity-log')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Activity Log', response.data)

if __name__ == '__main__':
    unittest.main()
