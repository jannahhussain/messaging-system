from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_session import Session
from datetime import timedelta
import logging
import os
import random
import string
from notifications import create_notification, get_notifications, mark_as_read
from models import User
import random
import string
from flask import jsonify, render_template, redirect
from flask import session
from user_management_authentication import user_auth_bp
from analytics import analytics_bp
from flask_login import login_required, current_user
from user_management_authentication import user_auth_bp
from chat import chat_bp
from user_management_authentication import user_bp
from admin_management import admin_bp
from notifications import notifications_bp
from analytics import analytics_bp



app = Flask(__name__)

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
session = Session()


app.register_blueprint(user_auth_bp)
app.register_blueprint(analytics_bp)

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)

    # Basic Config
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config.from_object('config.Config')

    # Session Config
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    session.init_app(app)


    # Register blueprints
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(notifications_bp, url_prefix='/notifications')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(user_auth_bp, url_prefix='/auth')
    app.register_blueprint(chat_bp, url_prefix='/chat')

    # Register error handlers and CLI commands
    register_error_handlers(app)
    register_cli_commands(app)

    logger.info("Application initialized successfully.")
    return app

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    """The dashboard for regular users showing their messages, notifications, etc."""
    user = current_user  # Get the currently logged-in user
    return render_template('user_dashboard.html', user=user)

def register_error_handlers(app):
    """Register global error handlers"""

    @app.errorhandler(404)
    def not_found_error(error):
        return {"error": "Resource not found"}, 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return {"error": "Access forbidden"}, 403

    @app.errorhandler(500)
    def internal_server_error(error):
        return {"error": "Internal server error"}, 500

def register_cli_commands(app):
    """Register custom CLI commands for development"""

    from models import User, Message, FlaggedContent

    @app.cli.command("create-db")
    def create_db():
        """Create all database tables"""
        db.create_all()
        logger.info("Database created successfully.")

    @app.cli.command("drop-db")
    def drop_db():
        """Drop all database tables"""
        db.drop_all()
        logger.warning("Database dropped.")

    @app.cli.command("seed-db")
    def seed_db():
        """Seed the database with sample users and messages"""
        try:
            # Create an admin user
            admin_user = User(
                first_name="Admin",
                last_name="User",
                username="admin",
                email="admin@example.com",
                role="admin",
                password_hash="adminhashedpassword",
                maiden_name="adminmom"
            )
            db.session.add(admin_user)

            # Create random users
            for i in range(5):
                user = User(
                    first_name=f"User{i}",
                    last_name="Tester",
                    username=f"user{i}",
                    email=f"user{i}@example.com",
                    role="user",
                    password_hash="userhashedpassword",
                    maiden_name="usermaiden"
                )
                db.session.add(user)

            db.session.commit()

            # Create random messages
            users = User.query.all()
            for _ in range(20):
                msg = Message(
                    sender_id=random.choice(users).id,
                    content="".join(random.choices(string.ascii_letters + string.digits, k=50))
                )
                db.session.add(msg)

            db.session.commit()
            logger.info("Database seeded with users and messages.")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Seeding failed: {str(e)}")

    @app.cli.command("list-users")
    def list_users():
        """List all registered users"""
        users = User.query.all()
        for user in users:
            print(f"{user.id}: {user.username} ({user.role}) - {user.email}")

    @app.cli.command("clear-flags")
    def clear_flags():
        """Clear all flagged content (for test reset)"""
        try:
            num_deleted = FlaggedContent.query.delete()
            db.session.commit()
            logger.info(f"Deleted {num_deleted} flagged entries.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to clear flags: {str(e)}")

@app.route('/notifications', methods=['GET'])
def view_notifications():
    user_id = session.get('user_id')  # Ensure user is logged in
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 403  # Return an error if no user is logged in

    # Fetch notifications for the logged-in user
    notifications = get_notifications(user_id)
    return render_template('notifications.html', notifications=notifications)  # Render notifications to UI

@app.route('/notifications/mark-read/<int:id>', methods=['POST'])
def mark_notification_as_read(id):
    user_id = session.get('user_id')  # Ensure user is logged in
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 403  # Return an error if no user is logged in

    # Mark the specific notification as read
    mark_as_read(id)
    return redirect('/notifications')  # Redirect back to notifications page after marking as read

@app.route('/ban_user/<int:user_id>', methods=['POST'])
def ban_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.is_banned = True
        db.session.commit()

        # Create notification for the banned user
        create_notification(
            user_id=user.id,
            notification_type='ban',
            message='Your account has been banned.'
        )

        # Create notification for the admin
        create_notification(
            user_id=1,  # dummy admin user ID
            notification_type='admin_alert',
            message=f'User {user.username} has been banned.'
        )

        return jsonify({"message": "User banned and notification sent."}), 200
    return jsonify({"error": "User not found"}), 404


# Run the application
if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
