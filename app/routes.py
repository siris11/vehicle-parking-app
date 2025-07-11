from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user

bp = Blueprint('routes', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('user.dashboard'))
    return render_template('index.html', title='Welcome')

# @bp.route('/dashboard')
# @login_required
# def user_dashboard():
#     if current_user.is_admin:
#         return redirect(url_for('admin.dashboard'))
#     return render_template('user/dashboard.html', title='User Dashboard') 