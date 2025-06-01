# app/auth.py (assuming this file is directly in the 'app/' directory)

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
# If forms.py and models.py are directly in 'app/', these imports are correct
from .forms import LoginForm, RegistrationForm
from .models import User
from . import db # This assumes 'db' is initialized in app/__init__.py and imported via 'from app import db' in other files
from werkzeug.security import generate_password_hash, check_password_hash # ADD THIS IMPORT (if not already present)

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_routes.dashboard'))
        # Using 'routes.index' as per your existing setup for regular users
        return redirect(url_for('routes.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        # MODIFIED: Use full_name in flash message for a more personal welcome
        flash(f'Welcome back, {user.full_name}!', 'success')
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            if user.is_admin:
                next_page = url_for('admin_routes.dashboard')
            else:
                # Using 'routes.index' as per your existing setup for regular users
                next_page = url_for('routes.index')
        return redirect(next_page)
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    # Using 'routes.index' as per your existing setup after logout
    return redirect(url_for('routes.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        # Using 'routes.index' as per your existing setup if already authenticated
        return redirect(url_for('routes.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # MODIFIED: Pass full_name from the form to the User constructor
        user = User(username=form.username.data, full_name=form.full_name.data, email=form.email.data, is_admin=False)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        login_user(user) # Log in the user automatically after registration
        # Using 'routes.index' as per your existing setup after registration
        return redirect(url_for('routes.index'))
    return render_template('auth/register.html', title='Register', form=form)