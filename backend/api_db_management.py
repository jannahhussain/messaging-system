
# This file handles all database-related functionality, such as:
# - Opening and closing database connections
# - Executing SQL queries
# - Handling migrations if needed
# - Helper functions to manage interactions with the database
# - Specialized queries for future features like notifications, activity logs, flagged content, etc.

from flask import current_app
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import logging
from datetime import datetime, timedelta


# Initialize logger for database actions
logger = logging.getLogger(__name__)

# Database connection setup
def get_db_engine():
    """
    Returns the SQLAlchemy engine based on app config settings.
    This engine is responsible for connecting to the database.
    """
    db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
    engine = create_engine(db_url, pool_recycle=3600)  # Recycle the connection every hour
    return engine

# Establish a scoped session for database interaction
engine = get_db_engine()
Session = scoped_session(sessionmaker(bind=engine))

# Context manager for managing database transactions
@contextmanager
def get_db_session():
    """
    Context manager for handling database sessions.
    Ensures that the session is properly closed after use.
    """
    session = Session()  # Open a new session
    try:
        yield session
        session.commit()  # Commit changes on success
    except Exception as e:
        session.rollback()  # Rollback on failure
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        session.close()  # Ensure session is always closed

# Helper function to execute raw SQL queries
def execute_query(query, params=None, one=False):
    """
    Executes a raw SQL query with parameters.
    Returns the first result if `one=True`, otherwise returns all results.
    """
    try:
        with get_db_session() as session:
            result = session.execute(text(query), params or {})
            if one:
                return result.fetchone()  # Return a single record
            return result.fetchall()  # Return all records
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return None

# Helper function to execute database migrations
def run_migrations():
    """
    Executes database migrations using Alembic or other migrations framework.
    This function will be important for managing schema changes over time.
    """
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")  # Upgrade to the latest migration
        logger.info("Migrations applied successfully.")
    except Exception as e:
        logger.error(f"Error during migrations: {str(e)}")

# Function to initialize the database (for testing or first-time setup)
def init_db():
    """
    Initializes the database by creating tables based on the models.
    This is typically used for development or testing.
    """
    try:
        # Create all tables based on the models
        from models import db
        db.create_all()  # This will create tables for all registered models
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing the database: {str(e)}")

# Function to drop all tables (useful for testing or reset)
def drop_db():
    """
    Drops all tables in the database.
    Be cautious when using this in production.
    """
    try:
        # Drop all tables based on models
        from models import db
        db.drop_all()
        logger.info("Database tables dropped successfully.")
    except Exception as e:
        logger.error(f"Error dropping database tables: {str(e)}")

# Example query function for fetching user details
def get_user_by_id(user_id):
    """
    Fetches a user by their unique user ID.
    """
    query = "SELECT * FROM users WHERE id = :user_id"
    params = {'user_id': user_id}
    return execute_query(query, params, one=True)

# Example function to update user details (e.g., suspend a user)
def update_user_status(user_id, status):
    """
    Update the status of a user (e.g., suspend, ban, etc.).
    """
    query = "UPDATE users SET status = :status WHERE id = :user_id"
    params = {'status': status, 'user_id': user_id}
    return execute_query(query, params)

# Helper function to get user notifications
def get_user_notifications(user_id):
    """
    Retrieves all notifications for a given user.
    """
    query = """
        SELECT * FROM notifications
        WHERE user_id = :user_id
        ORDER BY created_at DESC
    """
    params = {'user_id': user_id}
    return execute_query(query, params)

# Helper function to insert a new notification
def create_notification(user_id, message, notification_type='info'):
    """
    Creates a new notification for the user.
    """
    query = """
        INSERT INTO notifications (user_id, message, notification_type, created_at)
        VALUES (:user_id, :message, :notification_type, :created_at)
    """
    params = {
        'user_id': user_id,
        'message': message,
        'notification_type': notification_type,
        'created_at': datetime.utcnow()
    }
    return execute_query(query, params)

# Function for inserting a flagged message for review
def flag_message(user_id, message_id, reason):
    """
    Flags a message for review by the admin.
    """
    query = """
        INSERT INTO flagged_content (user_id, message_id, reason, created_at)
        VALUES (:user_id, :message_id, :reason, :created_at)
    """
    params = {
        'user_id': user_id,
        'message_id': message_id,
        'reason': reason,
        'created_at': datetime.utcnow()
    }
    return execute_query(query, params)

# Function to get all flagged content
def get_flagged_content():
    """
    Fetches content that has been flagged by users for admin review.
    """
    query = """
        SELECT fc.*, m.content, u.username FROM flagged_content fc
        JOIN messages m ON fc.message_id = m.id
        JOIN users u ON m.sender_id = u.id
        WHERE fc.reviewed = false
        ORDER BY fc.created_at DESC
    """
    return execute_query(query)

# Function for fetching recent user activity logs
def get_user_activity_logs(user_id, days=30):
    """
    Fetches user activity logs within a given timeframe (default 30 days).
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = """
        SELECT * FROM activity_logs
        WHERE user_id = :user_id AND timestamp >= :cutoff
        ORDER BY timestamp DESC
    """
    params = {'user_id': user_id, 'cutoff': cutoff}
    return execute_query(query, params)

# Function for detecting user interaction trends
def get_user_interaction_trends():
    """
    Detects user interaction trends (e.g., who interacted with whom).
    """
    query = """
        SELECT sender_id, receiver_id, COUNT(*) as interaction_count
        FROM messages
        GROUP BY sender_id, receiver_id
        HAVING interaction_count > 10  -- Example: more than 10 interactions
        ORDER BY interaction_count DESC
    """
    return execute_query(query)

# Utility function to fetch all tables (helpful for debugging)
def list_tables():
    """
    Returns a list of all table names in the database.
    Useful for debugging or inspecting the schema.
    """
    query = "SELECT name FROM sqlite_master WHERE type='table'"
    return execute_query(query)

# Cleanup function to close the session manually (if needed)
def close_session():
    """
    Manually closes the database session.
    Typically used in certain edge cases.
    """
    Session.remove()  # Close the scoped session
    logger.info("Database session closed manually.")
