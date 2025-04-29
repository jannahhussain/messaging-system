from datetime import datetime, timedelta
from collections import Counter
from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy import func, and_
from admin_management import verify_admin
from app import db
from models import User, Message, ActivityLog
from utils import verify_admin

# Blueprint Setup
analytics_bp = Blueprint('analytics_bp', __name__)

@analytics_bp.route('/admin/analytics/overview')
@login_required
def analytics_overview():
    """Provides general statistics for admin charts."""
    admin_id = request.args.get('admin_id', type=int)
    if not verify_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        stats = {
            "total_users": User.query.count(),
            "messages_sent": Message.query.count(),
            "active_users_past_7_days": User.query.filter(
                User.last_login >= datetime.utcnow() - timedelta(days=7)
            ).count(),
            "banned_users": User.query.filter_by(is_banned=True).count(),
            "suspended_users": User.query.filter(User.suspended_until > datetime.utcnow()).count()
        }
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analytics_bp.route('/admin/analytics/messages_trend')
@login_required
def messages_trend():
    """Returns number of messages sent per day in the last 30 days."""
    admin_id = request.args.get('admin_id', type=int)
    if not verify_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        days_ago = datetime.utcnow() - timedelta(days=30)
        message_counts = (
            db.session.query(
                func.date(Message.timestamp).label('day'),
                func.count(Message.id)
            )
            .filter(Message.timestamp >= days_ago)
            .group_by('day')
            .order_by('day')
            .all()
        )

        results = [{"day": str(day), "count": count} for day, count in message_counts]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analytics_bp.route('/admin/analytics/connection_network')
@login_required
def connection_network():
    """Returns connection relationships between users based on messaging."""
    admin_id = request.args.get('admin_id', type=int)
    if not verify_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Fetch sender/receiver pairs
        connections = (
            db.session.query(Message.sender_id, Message.receiver_id)
            .distinct()
            .all()
        )

        network = []
        for sender_id, receiver_id in connections:
            network.append({
                "source": sender_id,
                "target": receiver_id
            })

        return jsonify(network), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analytics_bp.route('/admin/analytics/active_users')
@login_required
def active_users():
    """Returns the most active users by number of messages sent."""
    admin_id = request.args.get('admin_id', type=int)
    if not verify_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        top_users = (
            db.session.query(User.username, func.count(Message.id).label('message_count'))
            .join(Message, User.id == Message.sender_id)
            .group_by(User.id)
            .order_by(func.count(Message.id).desc())
            .limit(10)
            .all()
        )

        results = [{"username": username, "messages_sent": message_count} for username, message_count in top_users]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analytics_bp.route('/admin/analytics/activity_log')
@login_required
def activity_log():
    """Returns a summarized view of admin activities."""
    admin_id = request.args.get('admin_id', type=int)
    if not verify_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        recent_actions = (
            ActivityLog.query
            .order_by(ActivityLog.timestamp.desc())
            .limit(20)
            .all()
        )

        results = [{
            "admin_id": action.user_id,
            "action": action.action,
            "timestamp": action.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        } for action in recent_actions]

        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
