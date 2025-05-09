from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import User, db, Group, GroupMembership
from app import db
from app import chat_bp
from models import Group, GroupMembership

# Blueprint setup
user_auth_bp = Blueprint('user_auth_bp', __name__)
group_bp = Blueprint('group_bp', __name__)

# Registration Route
@user_auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        maiden_name = request.form.get('maiden_name')

        if not all([first_name, last_name, email, password, maiden_name]):
            flash('All fields are required.', 'error')
            return redirect(url_for('user_auth_bp.register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.', 'error')
            return redirect(url_for('user_auth_bp.register'))

        try:
            new_user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password_hash=generate_password_hash(password),
                maiden_name=maiden_name,
                role='user',
                created_at=datetime.utcnow(),
                last_login=None
            )
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('user_auth_bp.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'error')
            return redirect(url_for('user_auth_bp.register'))

    return render_template('register.html')


# Login Route
@user_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')  # Changed from 'email' to 'username'
        password = request.form.get('password')

        # Fetch user by username
        user = User.query.filter_by(username=username).first()  # Changed to filter by username

        if user and check_password_hash(user.password_hash, password):
            # Check if the account is banned or suspended
            if user.is_banned:
                flash('Your account has been banned.', 'error')
                return redirect(url_for('user_auth_bp.login'))

            if user.suspended_until and user.suspended_until > datetime.utcnow():
                flash('Your account is suspended.', 'error')
                return redirect(url_for('user_auth_bp.login'))

            # If everything is fine, log the user in
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard')) 

        # If invalid credentials, show an error
        flash('Invalid username or password.', 'error')
        return redirect(url_for('user_auth_bp.login'))

    return render_template('login.html')


# Logout Route (old)
#@user_auth_bp.route('/logout')
#@login_required
#def logout():
#    logout_user()
#    flash('You have been logged out.', 'success')
#    return redirect(url_for('user_auth_bp.login'))


# Reset Password (Security Question)
@user_auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        maiden_name = request.form.get('maiden_name')
        new_password = request.form.get('new_password')

        if not all([email, maiden_name, new_password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('user_auth_bp.reset_password'))

        user = User.query.filter_by(email=email, maiden_name=maiden_name).first()

        if not user:
            flash('Incorrect details. Please try again.', 'error')
            return redirect(url_for('user_auth_bp.reset_password'))

        try:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()

            flash('Password reset successful. Please log in.', 'success')
            return redirect(url_for('user_auth_bp.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error resetting password: {str(e)}', 'error')
            return redirect(url_for('user_auth_bp.reset_password'))

    return render_template('forgot_password.html')


# Profile Route (for user's own profile)
@user_auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@chat_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@user_auth_bp.route('/create_group', methods=['POST'])
@login_required
def create_group():
    group_name = request.form.get('group_name')

    if not group_name:
        flash("Group name is required.", "error")
        return redirect(url_for('chat'))

    existing = Group.query.filter_by(name=group_name).first()
    if existing:
        flash("Group already exists.", "error")
        return redirect(url_for('chat'))

    group = Group(name=group_name, created_by=current_user.id)
    db.session.add(group)
    db.session.commit()

    membership = GroupMembership(group_id=group.id, user_id=current_user.id)
    db.session.add(membership)
    db.session.commit()

    flash("Group created successfully!", "success")
    return redirect(url_for('chat'))

@group_bp.route('/leave_group/<int:group_id>', methods=['POST'])
@login_required
def leave_group(group_id):
    membership = GroupMembership.query.filter_by(group_id=group_id, user_id=current_user.id).first()

    if not membership:
        flash("You're not a member of this group.", "error")
        return redirect(url_for('chat'))

    db.session.delete(membership)
    db.session.commit()

    flash("You have left the group.", "success")
    return redirect(url_for('chat'))

@group_bp.route('/kick_member/<int:group_id>/<int:user_id>', methods=['POST'])
@login_required
def kick_member(group_id, user_id):
    group = Group.query.get_or_404(group_id)

    if current_user.role != 'admin':
        flash("Only admins can remove members.", "error")
        return redirect(url_for('chat'))

    membership = GroupMembership.query.filter_by(group_id=group_id, user_id=user_id).first()

    if not membership:
        flash("User not in group.", "error")
        return redirect(url_for('chat'))

    db.session.delete(membership)
    db.session.commit()

    flash("User removed from group.", "success")
    return redirect(url_for('chat'))