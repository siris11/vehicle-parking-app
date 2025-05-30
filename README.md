# Vehicle Parking App

A Flask-based web application for managing vehicle parking lots.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-link>
    cd vehicle-parking-app
    ```

2.  **Create a virtual environment and activate it:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize the database:**
    ```bash
    flask db init
    flask db migrate -m "Initial migration."
    flask db upgrade
    ```

5.  **Run the application:**
    ```bash
    python run.py
    ```

    The application will be available at `http://127.0.0.1:5000/`.

## Roles

*   **Admin:** Superuser with full control. Default credentials will be created during database initialization.
*   **User:** Can register, login, book, and release parking spots.

## Project Structure

```
vehicle-parking-app/
├── app/                    # Main application package
│   ├── __init__.py         # Application factory
│   ├── models.py           # Database models
│   ├── forms.py            # WTForms definitions
│   ├── routes.py           # Application routes (views/controllers)
│   ├── auth.py             # Authentication blueprints
│   ├── admin.py            # Admin blueprints
│   ├── static/             # Static files (CSS, JS, images)
│   │   └── css/
│   │       └── style.css
│   └── templates/          # Jinja2 templates
│       ├── base.html           # Base template for all pages
│       ├── index.html
│       ├── login.html
│       ├── register.html
│       ├── admin/
│       │   └── dashboard.html
│       └── user/
│           └── dashboard.html
├── instance/               # Instance folder (for SQLite DB, config files)
│   └── app.db              # SQLite database file
├── migrations/             # Flask-Migrate database migration scripts
├── venv/                   # Virtual environment
├── run.py                  # Script to run the application
├── requirements.txt        # Python dependencies
└── README.md               # Project README
```

## Frameworks and Libraries

*   **Flask:** Backend web framework.
*   **Flask-SQLAlchemy:** ORM for database interaction.
*   **Flask-Migrate:** For handling database migrations.
*   **Flask-WTF:** For working with web forms.
*   **Flask-Login:** For user session management.
*   **Bootstrap-Flask:** For integrating Bootstrap CSS framework.
*   **Jinja2:** Templating engine.
*   **SQLite:** Database.
*   **HTML/CSS/Bootstrap:** Frontend.

## Core Functionalities

### Admin
*   Login (no registration required).
*   Create, edit, and delete parking lots.
*   View status of all parking spots.
*   View parked vehicle details.
*   View all registered users.
*   View summary charts (parking lots/spots).

### User
*   Register/Login.
*   Choose an available parking lot (spot auto-assigned).
*   Mark spot as occupied.
*   Mark spot as released.
*   View parking duration and cost.
*   View summary charts (personal parking history).

## ER Diagram

(To be added once models are finalized)

## API Resource Endpoints (if any)

(To be added if APIs are implemented) 