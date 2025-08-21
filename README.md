# ParkNxt: Parking Management Application
This is a web application designed to streamline parking lot management and reservations for both adminisand users.

# Demo : 
[Cick here to view the demo](https://drive.google.com/file/d/1h5pkJpwSGMF71U0dpJjQC3Ow2KmkrC-Y/view?usp=sharing)  
## Features
- User Authentication: Secure sign-up and login for admin and regular users.

- Admin Dashboard: Manage parking lots, spots, and view user/reservation data.
   - Manage Parking lot: Admin can add a new lot, view the spots, delete a lot (if it's not occupied)
   - Search: Admin can search Users and also search lots by location, pincode,

- User Functionality: Search for lots, book spots, check-in/out, and manage reservations.

## Tech Stack

- Backend: Python, Flask, Flask-SQLAlchemy

- Database: SQLite

- Frontend: HTML5, CSS, Jinja2, Bootstrap 5, Chart.js

- Authentication: Flask-Login, Werkzeug

## Setup Instructions


Prerequisites
1. Clone the Repository:
   ```bash
   git clone [<repo_url>](https://github.com/siris11/vehicle-parking-app/)
   cd [<repo_name>](https://github.com/siris11/vehicle-parking-app/)
   ```


2. Set up a Virtual Environment:
   
   `python3/python -m venv venv`
   
   ### On Windows:
   `.\venv\Scripts\activate`
   ### On macOS/Linux:
   `source venv/bin/activate`
   
3. Install Dependencies:
   
    `pip install -r requirements.txt`

(If requirements.txt is missing, create it after installing core dependencies: pip freeze > requirements.txt)

4. Configure Environment Variables
   Create a .env file in the project root with the following:
   
   ``` bash
   SECRET_KEY=your_secret_key_here
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD= default_password
   (Replace your_secret_key_here with a strong, randomly generated key, same with the ADMIN_PASSWORD)

6. Run the Application
   
     `python3 app.py`

Default Admin Credentials:
``` bash
Username: admin
Password: default_password
(Remember to change these after first login)
