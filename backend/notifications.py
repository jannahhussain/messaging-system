
from app import db
from models import Notification
from datetime import datetime
import logging
from flask import jsonify
from models import Message, FlaggedContent
from flask import Flask
app = Flask(__name__)

logger = logging.getLogger(__name__)

def create_notification(user_id, message, notif_type, is_read=False):
    """
    Create a notification for a user.
    
    Parameters:
    - user_id: ID of the user receiving the notification.
    - message: The message content of the notification.
    - notif_type: Type of notification ('error', 'report', 'admin', 'ban', etc.)
    - is_read: Whether the notification has been read by the user.
    """
    try:
        # Creating the notification object
        notification = Notification(
            user_id=user_id,
            message=message,
            type=notif_type,
            is_read=is_read,
            created_at=datetime.utcnow()
        )
        
        # Add to the session and commit to the database
        db.session.add(notification)
        db.session.commit()
        logger.info(f"Notification created for user {user_id}: {message}")
        return True
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating notification for user {user_id}: {str(e)}")
        return False


def get_user_notifications(user_id, limit=10, unread_only=False):
    """
    Retrieve notifications for a specific user.
    
    Parameters:
    - user_id: ID of the user whose notifications are being fetched.
    - limit: Limit the number of notifications returned.
    - unread_only: Filter to only show unread notifications if True.
    """
    try:
        query = db.session.query(Notification).filter(Notification.user_id == user_id)
        
        # Optionally filter unread notifications
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        # Order by creation time (most recent first)
        query = query.order_by(Notification.created_at.desc()).limit(limit)
        
        notifications = query.all()
        
        # Return notifications
        return notifications
    
    except Exception as e:
        logger.error(f"Error retrieving notifications for user {user_id}: {str(e)}")
        return []


def mark_notification_as_read(notification_id):
    """
    Mark a notification as read.
    
    Parameters:
    - notification_id: The ID of the notification to mark as read.
    """
    try:
        notification = Notification.query.get(notification_id)
        if notification:
            notification.is_read = True
            db.session.commit()
            logger.info(f"Notification {notification_id} marked as read.")
            return True
        else:
            logger.warning(f"Notification {notification_id} not found.")
            return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        return False


def delete_notification(notification_id):
    """
    Delete a notification from the database.
    
    Parameters:
    - notification_id: The ID of the notification to delete.
    """
    try:
        notification = Notification.query.get(notification_id)
        if notification:
            db.session.delete(notification)
            db.session.commit()
            logger.info(f"Notification {notification_id} deleted.")
            return True
        else:
            logger.warning(f"Notification {notification_id} not found.")
            return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting notification {notification_id}: {str(e)}")
        return False


def send_error_notification(user_id, error_message):
    """
    Send an error notification to an admin or user.
    
    Parameters:
    - user_id: The user to notify.
    - error_message: The error message content.
    """
    return create_notification(user_id, error_message, notif_type='error')


def send_report_notification(user_id, report_details):
    """
    Send a report notification for flagged content.
    
    Parameters:
    - user_id: The admin to notify about flagged content.
    - report_details: Details about the flagged content.
    """
    message = f"New report received: {report_details}"
    return create_notification(user_id, message, notif_type='report')


def send_admin_action_notification(admin_id, action_details):
    """
    Send a notification to an admin about an action taken by another admin.
    
    Parameters:
    - admin_id: The admin to notify about another admin's action.
    - action_details: Details of the admin action.
    """
    message = f"Admin action taken: {action_details}"
    return create_notification(admin_id, message, notif_type='admin')


def send_ban_notification(user_id, ban_details):
    """
    Send a ban notification to a user who is banned.
    
    Parameters:
    - user_id: The user who has been banned.
    - ban_details: Reason and details for the ban.
    """
    message = f"You have been banned: {ban_details}"
    return create_notification(user_id, message, notif_type='ban')


def send_suspend_notification(user_id, suspend_details):
    """
    Send a suspension notification to a user who is suspended.
    
    Parameters:
    - user_id: The user who is suspended.
    - suspend_details: Reason and details for the suspension.
    """
    message = f"You have been suspended: {suspend_details}"
    return create_notification(user_id, message, notif_type='suspend')


# Admin can view all notifications for review
def get_all_notifications(limit=10):
    """
    Retrieve all notifications for admin review.
    
    Parameters:
    - limit: Limit the number of notifications returned.
    """
    try:
        notifications = db.session.query(Notification).order_by(Notification.created_at.desc()).limit(limit).all()
        return notifications
    except Exception as e:
        logger.error(f"Error retrieving all notifications: {str(e)}")
        return []


def flag_content(message_id, user_id, reason):
    # Flag the message in the database
    flag = FlaggedContent(message_id=message_id, user_id=user_id, reason=reason)
    db.session.add(flag)
    db.session.commit()

    # Create notification for admin about the flagged content
    create_notification(
        user_id=1,  # assuming admin has ID 1
        notification_type='admin_alert',
        message=f'Content flagged for review. Message ID: {message_id}. Reason: {reason}'
    )

    # Create notification for the user who flagged the content
    create_notification(
        user_id=user_id,
        notification_type='flagged_content',
        message='You have successfully flagged the content for review.'
    )

@app.route('/delete_message/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    message = Message.query.get(message_id)
    if message:
        db.session.delete(message)
        db.session.commit()

        # Notify admin about the deletion
        create_notification(
            user_id=1,  # dummy admin user ID
            notification_type='admin_alert',
            message=f'Message {message_id} has been deleted.'
        )

        # Notify the user who posted the message
        create_notification(
            user_id=message.sender_id,
            notification_type='message_deleted',
            message='Your message has been deleted by the admin.'
        )

        return jsonify({"message": "Message deleted and notifications sent."}), 200
    return jsonify({"error": "Message not found"}), 404

