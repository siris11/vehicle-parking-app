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

## Local Setup Instructions

Follow these steps to get the application running on your local machine.

### Prerequisites
- Python 3.8+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/siris11/vehicle-parking-app/
cd vehicle-parking-app
```

### 2. Create and Activate a Virtual Environment
```bash
# Create the virtual environment
python3 -m venv venv
```
**Activate the environment:**
- **On macOS/Linux:**
  ```bash
  source venv/bin/activate
  ```
- **On Windows:**
  ```bash
  .\venv\Scripts\activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a local environment file 
```bash
     .env
```

Next, add a strong, unique `SECRET_KEY` in the .env file. 

**To generate a secure `SECRET_KEY`**, you can run this in a Python shell:
```python
import secrets
secrets.token_hex(24)
```
Paste the generated key into your `.env` file.

### 5. Run the Application
```bash
flask run
```
The application will be available at `http://127.0.0.1:5000`. The database will be created and configured automatically on the first run.

### 6. Create an Account
Navigate to the application in your browser and use the "Register" button to create a new user account.

---

### Optional: Creating an Admin Account
To use the administrative features (like creating parking lots), you need an admin account.

1.  **Set Admin Credentials (Optional):** You can add `ADMIN_USERNAME` and `ADMIN_PASSWORD` to your `.env` file.
2.  **Run the Admin Creation Command:**
    Use the custom CLI command to create the admin account.
    ```bash
    flask create-admin
    ```
    If you did not set an `ADMIN_PASSWORD` in your `.env` file, you will be prompted to enter and confirm a password securely in the terminal. After creating the admin, you can log in with those credentials to manage the application.
