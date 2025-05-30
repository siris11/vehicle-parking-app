from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user

bp = Blueprint('routes', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_routes.dashboard'))
        else:
            return redirect(url_for('user_routes.dashboard'))
    return render_template('index.html', title='Welcome')

# Example of how user dashboard route might look (to be moved to user_routes.py)
# @bp.route('/dashboard')
# @login_required
# def user_dashboard():
#     if current_user.is_admin:
#         return redirect(url_for('admin_routes.dashboard'))
#     return render_template('user/dashboard.html', title='User Dashboard') 