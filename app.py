import os
from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager
from flask_bootstrap import Bootstrap5
from datetime import datetime
from werkzeug.security import generate_password_hash 
from models import db, User 
from routes import main, auth, admin, user
from dotenv import load_dotenv 

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

if __name__ == '__main__':
    app = create_app() 

    with app.app_context():
        db.create_all() 
        
        default_admin_username = os.environ.get('ADMIN_USERNAME')
        default_admin_password = os.environ.get('ADMIN_PASSWORD')

        admin_user = User.query.filter_by(username=default_admin_username, is_admin=True).first()

        if not admin_user:
            new_admin = User(
                username=default_admin_username, 
                full_name='admin', 
                email='admin@admin.com', 
                password_hash=generate_password_hash(default_admin_password), 
                is_admin=True
            )
            db.session.add(new_admin)
            db.session.commit()
            print(f"The password for '{default_admin_username}' is set. Change it immediately after first login!**")
        else:
            print(f"Admin user '{default_admin_username}' already exists. No new admin user created.")

app.run(debug=True)