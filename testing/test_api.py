import pytest
from app import create_app, db
from models import User, Message, FlaggedContent

@pytest.fixture
def client():
    """Fixture for testing API with a test client."""
    app = create_app('testing')  # Create the app in testing mode
    with app.test_client() as client:
        with app.app_context():
            db.create_all()  # Create the database tables
        yield client
        with app.app_context():
            db.drop_all()  # Drop the tables after tests

@pytest.fixture
def user(client):
    """Fixture to create a test user."""
    user = User(
        username="testuser",
        email="testuser@example.com",
        password="password123"
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def admin(client):
    """Fixture to create a test admin user."""
    admin = User(
        username="adminuser",
        email="admin@example.com",
        password="adminpassword123",
        role="admin"
    )
    db.session.add(admin)
    db.session.commit()
    return admin

def test_user_registration(client):
    """Test user registration endpoint."""
    response = client.post('/register', json={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert response.status_code == 200
    assert response.json['message'] == "User registered successfully."

def test_user_login(client, user):
    """Test user login endpoint."""
    response = client.post('/login', json={
        'email': user.email,
        'password': 'password123'
    })
    assert response.status_code == 200
    assert response.json['message'] == "Login successful."

def test_user_login_invalid(client):
    """Test invalid login."""
    response = client.post('/login', json={
        'email': 'invaliduser@example.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 401
    assert response.json['error'] == "Invalid credentials."

def test_flag_message(client, user):
    """Test flagging a message."""
    message = Message(sender_id=user.id, content="This is a test message")
    db.session.add(message)
    db.session.commit()

    response = client.post('/flag_message', json={
        'message_id': message.id,
        'reason': 'Inappropriate content'
    })
    assert response.status_code == 200
    assert response.json['message'] == "Message flagged successfully for review."

def test_flag_message_invalid(client, user):
    """Test flagging a non-existing message."""
    response = client.post('/flag_message', json={
        'message_id': 9999,  # Non-existent message ID
        'reason': 'Inappropriate content'
    })
    assert response.status_code == 404
    assert response.json['error'] == "Message not found"

def test_admin_review_flagged_content(client, admin, user):
    """Test admin reviewing flagged content."""
    message = Message(sender_id=user.id, content="Test message")
    db.session.add(message)
    db.session.commit()

    flagged_content = FlaggedContent(
        message_id=message.id,
        user_id=user.id,
        reason="Inappropriate content"
    )
    db.session.add(flagged_content)
    db.session.commit()

    response = client.post('/review_flagged_content/1', json={
        'action': 'delete'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert response.json['message'] == "Action taken: Message deleted"

def test_admin_review_flagged_content_invalid_action(client, admin):
    """Test admin providing invalid action on flagged content."""
    flagged_content = FlaggedContent.query.first()
    
    response = client.post(f'/review_flagged_content/{flagged_content.id}', json={
        'action': 'invalid_action'
    }, follow_redirects=True)
    
    assert response.status_code == 400
    assert response.json['error'] == "Invalid action"

def test_admin_dashboard_stats(client, admin):
    """Test that the admin dashboard stats are returned correctly."""
    response = client.get('/admin/dashboard', follow_redirects=True)
    assert response.status_code == 200
    data = response.get_json()
    assert 'total_users' in data
    assert 'active_users' in data
    assert 'flagged_messages' in data
    assert 'banned_users' in data
    assert 'recent_flags' in data
    assert 'recent_users' in data

def test_admin_ban_user(client, admin):
    """Test banning a user."""
    user = User.query.first()
    response = client.post(f'/ban-user/{user.id}', follow_redirects=True)
    assert response.status_code == 200
    assert user.is_banned == True

def test_admin_suspend_user(client, admin):
    """Test suspending a user."""
    user = User.query.first()
    response = client.post(f'/suspend-user/{user.id}', follow_redirects=True)
    assert response.status_code == 200
    assert user.suspended_until is not None

def test_create_notification(client, admin):
    """Test creating a notification."""
    response = client.post('/notifications/create', json={
        'user_id': admin.id,
        'notification_type': 'admin_alert',
        'message': 'This is a test notification'
    })
    assert response.status_code == 200
    assert response.json['message'] == "Notification created successfully."

def test_get_notifications(client, admin):
    """Test retrieving notifications for an admin."""
    response = client.get('/notifications', follow_redirects=True)
    assert response.status_code == 200
    assert isinstance(response.json, list)  # Ensure it's a list of notifications

def test_flagged_content(client, admin):
    """Test fetching flagged content."""
    flagged_contents = FlaggedContent.query.all()
    response = client.get('/admin/flagged-content', follow_redirects=True)
    assert response.status_code == 200
    assert len(response.json) == len(flagged_contents)
