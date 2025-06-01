# 1. Import necessary objects
# Enter the Flask shell: flask shell
# Inside the >>> prompt, type: exec(open('create_admin_user.py').read())
# After the script finishes, type exit() to leave the Flask shell.

from app import db 
from app.models import User 

# 2. Create all database tables 
db.create_all()
print("Database tables created (if they didn't exist).")

# 3. Define the credentials for the root user
username = 'root'
email = 'root@example.com' 
password = 'root098' 

# 4. Check if a user with this username already exists to prevent errors on re-runs
existing_user = User.query.filter_by(username=username).first()

if existing_user:
    print(f"User '{username}' already exists. Updating admin status if needed.")
    # If the user exists, ensure they are an admin
    if not existing_user.is_admin:
        existing_user.is_admin = True
        db.session.commit()
        print(f"User '{username}' promoted to admin.")
    else:
        print(f"User '{username}' is already an admin.")
else:
    # 5. Create the new User instance
    new_user = User(username=username, email=email)

    # 6. Set the password (this will hash it using your set_password method from app.models)
    new_user.set_password(password)

    # 7. Set the user as an administrator
    new_user.is_admin = True

    # 8. Add the new user to the database session and commit
    db.session.add(new_user)
    db.session.commit()
    print(f"User '{username}' created successfully and set as admin!")

# 9. Verify the user was created and is an admin
all_users = User.query.all()
print("\nAll users in database:")
for user in all_users:
    print(f"  - Username: {user.username}, Email: {user.email}, Admin: {user.is_admin}")

# Note: You do NOT need 'exit()' in this script.
# You will type 'exit()' in the Flask shell manually after running this script.

