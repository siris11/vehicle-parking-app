import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bootstrap import Bootstrap5
from datetime import datetime

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Redirect to login page if user is not authenticated
login_manager.login_message_category = 'info' # Flash message category

def create_app(config_class=None):
    """Application factory function."""
    app = Flask(__name__, instance_relative_config=True)

    # Configure application
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_secret_key'), # Change in production!
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'app.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        BOOTSTRAP_SERVE_LOCAL=True, # Serve Bootstrap files locally
    )

    if config_class:
        # Load configuration from a config class, if provided
        app.config.from_object(config_class)
    else:
        # Load instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass # Already exists

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    Bootstrap5(app)

    # Context processor to make datetime available in templates
    @app.context_processor
    def inject_now():
        return {'datetime': datetime}

    # Register blueprints
    from . import routes, auth, admin_routes, user_routes #, user_routes (add later)
    app.register_blueprint(routes.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin_routes.bp, url_prefix='/admin')
    app.register_blueprint(user_routes.bp, url_prefix='/user')


    # Define user loader for Flask-Login
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Create database tables if they don't exist (for initial setup)
    # This is generally handled by Flask-Migrate in production
    with app.app_context():
        db.create_all() 
        # Create a default admin user if one doesn't exist
        if not User.query.filter_by(username='root').first():
            from werkzeug.security import generate_password_hash
            admin_user = User(
                username='root',
                email='root@gmail.com',
                password_hash=generate_password_hash('123456'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created with username 'root' and password '123456'")


    return app 