# ParkNxt: Parking Management Application
This is a web application designed to streamline parking lot management and reservations for both adminisand users.

## Features
- User Authentication: Secure sign-up and login for admin and regular users.

- Admin Dashboard: Manage parking lots, spots, and view user/reservation data.
   - Manage Parking lot: Admin can add a new lot, view the spots, delete a lot (if it's not occupied)
   - Search: Admin can search Users and also search lots by location, pincode,

- User Functionality: Search for lots, book spots, check-in/out, and manage reservations.

## Tech Stack

- Backend: Python, Flask, Flask-SQLAlchemy

- Database: SQLite

- Frontend: HTML5, CSS3, Jinja2, Bootstrap 5, Chart.js

- Authentication: Flask-Login, Werkzeug

## API Endpoints


- ``GET POST /auth/login`` - User login
- ```GET POST /auth/register``` - New user registration
- ``` GET /admin/dashboard``` - Admin dashboard overview
- ``` GET /admin/parking_lots``` - List all parking lots
- ```GET /admin/users``` - List all users
- ``` GET, POST /admin/parking_lot/new``` - Add a new parking lot
- ``` GET, POST /admin/parking_lot/edit/:lot_id``` - Edit an existing parking lot
- ```POST /admin/parking_lot/delete/:lot_id```  - Delete a parking lot
- ```GET /admin/view_spots/:lot_id``` - View spots within a lot
- ```GET /admin/view_spot_details/:spot_id``` - View details of a specific spot
- ```GET /admin/user_details/:user_id``` - View details of a specific user

- ```GET, POST /user/dashboard ``` - User dashboard (includes search/booking)
-  ```GET, POST /user/book_spot/:lot_id``` - Book a spot in a lot
- ```GET /user/park_out_page/:reservation_id``` -  Display park-out confirmation

- ``` GET, POST /user/edit_profile``` - Admin,User's own profile edit
- ```GET, POST /user/change_password``` - Admin, User's own password change


## Setup Instructions


Prerequisites
1. Clone the Repository
1. Clone the repository and start the backend server:
   ```bash
   git clone [<repo_url>](https://github.com/22f3001809/vehicle-parking-app/)
   cd [<repo_name>](https://github.com/22f3001809/vehicle-parking-app/)/server
   ```

2. Set up a Virtual Environment
`python3/python -m venv venv`
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

3. Install Dependencies
```pip install -r requirements.txt```

(If requirements.txt is missing, create it after installing core dependencies: pip freeze > requirements.txt)

4. Configure Environment Variables
Create a .env file in the project root with the following:

SECRET_KEY=your_secret_key_here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin098
(Replace your_secret_key_here with a strong, randomly generated key.)

6. Run the Application
```python run.py```

Default Admin Credentials:

Username: admin
Password: admin098
(Remember to change these after first login)