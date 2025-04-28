# admin_management.py
from datetime import datetime, timedelta
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
import logging

from app import db
from models import ActivityLog, FlaggedContent, Message, User
from notifications import create_notification
from utils import verify_admin

# Blueprint setup
admin_bp = Blueprint('admin_bp', __name__)
logger = logging.getLogger(__name__)


def verify_admin(user_id):
    """Check if the user is an admin."""
    user = User.query.get(user_id)
    return user and user.role == 'admin'


def flag_message(message_id, user_id, reason):
    """Flag a message for review by admin."""
    try:
        message = Message.query.get(message_id)
        if not message:
            return {"error": "Message not found"}, 404

        flagged_content = FlaggedContent(
            message_id=message_id,
            user_id=user_id,
            reason=reason
        )
        db.session.add(flagged_content)
        db.session.commit()

        # Notify user
        create_notification(
            user_id=user_id,
            notification_type='flagged_content',
            message=f'You have successfully flagged message ID {message_id}. Reason: {reason}'
        )

        # Notify all admins
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            create_notification(
                user_id=admin.id,
                notification_type='admin_alert',
                message=f'Message ID {message_id} flagged. Reason: {reason}'
            )

        return {"message": "Message flagged successfully for review."}, 200

    except Exception as e:
        db.session.rollback()
        return {"error": f"Error flagging message: {str(e)}"}, 500


def review_flagged_content(flagged_content_id, action, admin_id):
    """Admin reviews flagged content and takes action."""
    try:
        if not verify_admin(admin_id):
            return {"error": "Unauthorized"}, 403

        flagged_content = FlaggedContent.query.get(flagged_content_id)
        if not flagged_content:
            return {"error": "Flag not found"}, 404

        message = Message.query.get(flagged_content.message_id)
        if not message:
            return {"error": "Message not found"}, 404

        # Update flag status
        flagged_content.reviewed = True
        flagged_content.reviewed_by = admin_id
        flagged_content.reviewed_at = datetime.utcnow()

        # Process action
        action_taken = process_admin_action(action, message)
        if not action_taken:
            return {"error": "Invalid action"}, 400

        db.session.commit()
        log_admin_action(admin_id, f"Action '{action}' on message {message.id}")

        # Notify admin
        create_notification(
            user_id=1,
            notification_type='admin_alert',
            message=f'Action taken: {action_taken} on message ID {message.id}'
        )

        return {"message": f"Action taken: {action_taken}"}, 200

    except Exception as e:
        db.session.rollback()
        return {"error": f"Error reviewing content: {str(e)}"}, 500

def process_admin_action(action, message):
    """Helper to process different admin actions."""
    actions = {
        'delete': lambda: ("Message deleted", db.session.delete(message)),
        'warn': lambda: ("User warned", None),
        'ban': lambda: ("User banned", setattr(User.query.get(message.sender_id), 'is_banned', True)),
        'ignore': lambda: ("Flag ignored", None)
    }
    
    if action not in actions:
        return None
    
    action_taken, action_func = actions[action]
    if action_func:
        action_func()
    return action_taken

def log_admin_action(admin_id, action):
    """Log admin actions for auditing."""
    try:
        activity_log = ActivityLog(
            user_id=admin_id,
            action=action,
            timestamp=datetime.utcnow()
        )
        db.session.add(activity_log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to log admin action: {str(e)}")

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if not verify_admin(current_user.id):
        return redirect('/unauthorized')
    stats = get_admin_dashboard_stats()
    return render_template('admin_dashboard.html', stats=stats)

def get_admin_dashboard_stats():
    """Get statistics for admin dashboard."""
    try:
        return {
            'total_users': User.query.count(),
            'active_users': User.query.filter(
                User.last_login >= datetime.utcnow() - timedelta(days=30)
            ).count(),
            'flagged_messages': FlaggedContent.query.filter_by(reviewed=False).count(),
            'banned_users': User.query.filter_by(is_banned=True).count(),
            'recent_flags': FlaggedContent.query.order_by(
                FlaggedContent.created_at.desc()
            ).limit(5).all(),
            'recent_users': User.query.order_by(
                User.created_at.desc()
            ).limit(5).all(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve admin stats: {str(e)}")
        return {}

# API Routes
@admin_bp.route('/flag_message', methods=['POST'])
def flag_content():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    message_id = data.get('message_id')
    reason = data.get('reason')

    if not message_id or not reason:
        return jsonify({"error": "Missing message ID or reason"}), 400

    return flag_message(message_id, user_id, reason)

@admin_bp.route('/review_flagged_content/<int:flagged_content_id>', methods=['POST'])
def review_flagged_content_route(flagged_content_id):
    admin_id = session.get('user_id')
    if not admin_id or not verify_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    action = data.get('action')

    if not action:
        return jsonify({"error": "Action is required"}), 400

    return review_flagged_content(flagged_content_id, action, admin_id)

# Admin UI Routes
@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if not verify_admin(current_user.id):
        return redirect('/unauthorized')
    return render_template('admin_dashboard.html', stats=get_admin_dashboard_stats())

@admin_bp.route('/flagged-content')
@login_required
def flagged_content():
    if not verify_admin(current_user.id):
        return redirect('/unauthorized')
    
    flagged_messages = FlaggedContent.query.filter_by(reviewed=False).all()
    messages = []
    for flag in flagged_messages:
        message = Message.query.get(flag.message_id)
        messages.append(message)
    
    return render_template('admin_flagged_content.html', flagged_messages=messages)

@admin_bp.route('/flagged-content/action/<int:flag_id>', methods=['POST'])
@login_required
def flag_action(flag_id):
    if not verify_admin(current_user.id):
        return redirect('/unauthorized')

    flag = FlaggedContent.query.get(flag_id)
    if not flag:
        flash('Flag not found', 'error')
        return redirect(url_for('admin_bp.flagged_content'))

    action = request.form.get('action')
    message = Message.query.get(flag.message_id)

    try:
        action_taken = process_admin_action(action, message)
        if not action_taken:
            flash('Invalid action', 'error')
            return redirect(url_for('admin_bp.flagged_content'))

        # Mark flag as reviewed and save to DB
        flag.reviewed = True
        flag.reviewed_by = current_user.id
        flag.reviewed_at = datetime.utcnow()
        db.session.commit()

        flash(f'{action_taken} on message {message.id}', 'success')
        return redirect(url_for('admin_bp.flagged_content'))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to process action: {str(e)}")
        flash('Failed to process action', 'error')
        return redirect(url_for('admin_bp.flagged_content'))


@admin_bp.route('/ban-user/<int:user_id>', methods=['POST'])
@login_required
def ban_user(user_id):
    if not verify_admin(current_user.id):
        return redirect('/unauthorized')
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin_bp.admin_dashboard'))
    
    try:
        user.is_banned = True
        db.session.commit()
        log_admin_action(current_user.id, f"Banned user {user.username}")
        flash(f'User {user.username} banned', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to ban user: {str(e)}")
        flash('Failed to ban user', 'error')
    
    return redirect(url_for('admin_bp.admin_dashboard'))

@admin_bp.route('/suspend-user/<int:user_id>', methods=['POST'])
@login_required
def suspend_user(user_id):
    if not verify_admin(current_user.id):
        return redirect('/unauthorized')
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin_bp.admin_dashboard'))

    try:
        suspension_days = int(request.form.get('suspension_days', 30))  # Default to 30 if not provided
        user.suspended_until = datetime.utcnow() + timedelta(days=suspension_days)
        db.session.commit()
        log_admin_action(current_user.id, f"Suspended user {user.username} for {suspension_days} days")
        flash(f'User {user.username} suspended for {suspension_days} days', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to suspend user: {str(e)}")
        flash('Failed to suspend user', 'error')
    
    return redirect(url_for('admin_bp.admin_dashboard'))


