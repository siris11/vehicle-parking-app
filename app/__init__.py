import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap5
from datetime import datetime

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Redirect to login page if user is not authenticated
login_manager.login_message_category = 'info' # Flash message category

def create_app(config_class=None):
    """Application factory function."""
    app = Flask(__name__, instance_relative_config=True)

    # Configure application
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_secret_key'),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'app.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        BOOTSTRAP_SERVE_LOCAL=True, 
    )

    if config_class:
        app.config.from_object(config_class)
    else:
        # Load instance config, if it exists, when not testing
        # This is a good place for sensitive config that's NOT version controlled
        app.config.from_pyfile('config.py', silent=True)

    # Ensure the instance folder exists (where app.db will be created)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass # Already exists

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    Bootstrap5(app)

    @app.context_processor
    def inject_now():
        return {'datetime': datetime}

    # Register blueprints
    from . import routes, auth, admin_routes, user_routes
    app.register_blueprint(routes.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin_routes.bp, url_prefix='/admin')
    app.register_blueprint(user_routes.bp, url_prefix='/user')


    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # CREATE DATABASE TABLES ON APP STARTUP

    with app.app_context():
        from . import models
        db.create_all()

    return app