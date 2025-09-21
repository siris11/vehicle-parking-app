import os
from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager
from flask_bootstrap import Bootstrap5
from datetime import datetime
from werkzeug.security import generate_password_hash 
from models import db, User 
from routes import main, auth, admin, user
from dotenv import load_dotenv 
from flask_migrate import Migrate, upgrade

load_dotenv() 

login_manager = LoginManager()

def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'app.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        BOOTSTRAP_SERVE_LOCAL=True, 
    )

    if not app.config.get('SECRET_KEY'):
        raise RuntimeError("SECRET_KEY environment variable is not set.")

    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_pyfile('config.py', silent=True)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass 

    db.init_app(app) 
    Migrate(app, db)

    # Automatically apply migrations on startup
    with app.app_context():
        upgrade()

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info' 
    Bootstrap5(app)

    @app.context_processor
    def inject_now():
        return {'datetime': datetime}

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
   
    app.register_blueprint(main.bp) 
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp, url_prefix='/admin')
    app.register_blueprint(user.bp, url_prefix='/user') 
   
    return app

app = create_app() 

@app.cli.command("create-admin")
def create_admin():
    """Creates the default admin user."""
    default_admin_username = os.environ.get('ADMIN_USERNAME')
    default_admin_password = os.environ.get('ADMIN_PASSWORD')

    if not default_admin_username or not default_admin_password:
        print("ADMIN_USERNAME and ADMIN_PASSWORD environment variables must be set.")
        return

    admin_user = User.query.filter_by(username=default_admin_username, is_admin=True).first()

    if not admin_user:
        new_admin = User(
            username=default_admin_username, 
            full_name='admin', 
            email='admin@admin.com', 
            is_admin=True
        )
        new_admin.set_password(default_admin_password)
        db.session.add(new_admin)
        db.session.commit()
        print(f"Admin user '{default_admin_username}' created.")
        print(f"**The password for '{default_admin_username}' is set. Change it immediately after first login!**")
    else:
        print(f"Admin user '{default_admin_username}' already exists. No new admin user created.")

if __name__ == '__main__':
    app.run(debug=True)