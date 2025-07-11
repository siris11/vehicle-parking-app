from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all() #

        default_admin_username = 'root'
        default_admin_password = 'root098'

        admin_user = User.query.filter_by(username=default_admin_username, is_admin=True).first()

        if not admin_user:
            # Create a default admin user if none exists
            new_admin = User(
                username=default_admin_username, 
                full_name='Admin',
                email='root@parknxt.com', 
                password_hash=generate_password_hash(default_admin_password), 
                is_admin=True
            )
            db.session.add(new_admin)
            db.session.commit()
            print(f"Default admin user created: username '{default_admin_username}', password '{default_admin_password}'. **Change this password immediately!**")

    app.run(debug=True)