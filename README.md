# Lecture Management System

## Overview

This is a web-based application designed to manage lectures, attendance, and student records for educational institutions. The system allows users (teachers, administrators) to add subjects, batches, students, and lectures, mark attendance for each lecture, and generate attendance reports. The application uses Flask, SQLAlchemy, and Flask-Login for user management and session handling.

## Demo Login

To access the website as an admin, use the following login credentials:

- **Email**: vivek@gmail.com
- **Password**: vivek1

This account has admin access to manage users, batches, lectures, and attendance.

## Features

- **User Registration & Login**: Admins can register new users and manage user logins.
- **Lecture Management**: Create and manage lectures, assign them to subjects and batches, and mark attendance for each lecture.
- **Attendance Tracking**: Track attendance for students, view attendance reports, and calculate attendance percentages.
- **Batch & Student Management**: Admins can create batches and add students to these batches.
- **Email Notifications**: Send emails for contact form submissions.
- **Admin & Teacher Roles**: Different roles for users with permissions based on their roles.

## Technologies

- **Flask**: The web framework used to build the application.
- **SQLAlchemy**: ORM for interacting with the database.
- **Flask-Login**: Used to manage user authentication and sessions.
- **Flask-Bootstrap**: For integrating Bootstrap 5 into the Flask application.
- **Werkzeug**: For password hashing.
- **SMTP (Gmail)**: For sending email notifications.

## Setup

### Prerequisites

- Python 3.x
- pip (Python package manager)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/lecture-management-system.git
   cd lecture-management-system
   ```

2. Create a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # For MacOS/Linux
   venv\Scripts\activate  # For Windows
   ```

3. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory of the project with the following content:

   ```bash
   EMAIL=your-email@gmail.com
   PASSWORD=your-email-password
   SECRET_KEY=your-secret-key
   SQLALCHEMY_DATABASE_URI=sqlite:///site.db
   ```

   Replace `your-email@gmail.com`, `your-email-password`, and `your-secret-key` with your actual email, email password (for SMTP), and a secret key for Flask sessions. You can use `sqlite:///site.db` for local testing, or replace it with a proper database URI (e.g., PostgreSQL, MySQL).

5. Run the application:

   ```bash
   python app.py
   ```

   The app will be accessible at `http://127.0.0.1:5000/` by default.

## Usage

### User Roles

- **Admin**: Can manage users, add batches, students, subjects, and lectures.
- **Teacher**: Can manage lectures and mark attendance.

### Routes

- `/register`: Admins can register new users.
- `/login`: Users can log in to the application.
- `/home`: Displays all lectures and allows teachers to manage them.
- `/mark-attendance`: Teachers can mark attendance for lectures.
- `/attendance`: View attendance reports.
- `/about`: Information about the application.
- `/contact`: A contact form to submit queries.

### Attendance Management

- Teachers can mark attendance for lectures through the `/mark-attendance` route.
- Students' attendance status is tracked, and reports can be generated based on attendance percentages.

## Error Handling

- **404 Page Not Found**: Custom error page for when a route is not found.

### Acknowledgments

- Flask for the web framework.
- SQLAlchemy for ORM-based database management.
- Flask-Login for user session management.
- Bootstrap 5 for the front-end styling.
