# Educational System

Welcome to the **Educational System**, a web-based application designed to manage students, instructors, and courses within an educational institution. Built with Flask (Python) for the backend and HTML/CSS/JavaScript for the frontend, this project provides a comprehensive platform for academic administration, course enrollment, grade management, and timetable scheduling.

## Table of Contents
- [Features](#features)
- [Technologies](#technologies)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Contributing](#contributing)
- [License](#license)

## Features
- **User Authentication**: Secure login for students, instructors, and administrators with role-based access.
- **Student Dashboard**:
  - View and edit personal profile.
  - Enroll in or drop courses based on availability and schedule conflicts.
  - Check grades and view course timetables.
- **Instructor Dashboard**:
  - Manage personal profile.
  - View assigned courses and student enrollments.
  - Assign grades to students.
  - Access teaching timetables.
- **Admin Dashboard**:
  - Manage students, instructors, and courses (add, update, delete).
  - Export data as CSV files.
  - View system statistics (e.g., total students, instructors, courses).
  - Filter and search records for efficient management.
- **Course Management**:
  - Schedule courses with time slots and weeks.
  - Prevent scheduling conflicts for students during enrollment.
- **Responsive Design**: User-friendly interface with tabbed navigation and modal forms.

## Technologies
- **Backend**: Python 3.x, Flask, PyMySQL
- **Frontend**: HTML5, CSS3, JavaScript, Chart.js (for potential future enhancements)
- **Database**: MySQL
- **Other**: Logging for error tracking, session management for authentication

## Installation

### Prerequisites
- Python 3.x
- MySQL Server
- Git

### Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/StarryCode-Lang/educational-system.git
   cd educational-system
   ```

2. **Set Up a Virtual Environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note*: If `requirements.txt` is not included, install the required packages manually:
   ```bash
   pip install flask pymysql
   ```

4. **Configure the Database**:
   - Create a MySQL database named `educationalsystem`.
   - Update the database connection details in `app.py` if necessary (default: `host="localhost"`, `user="root"`, `password="root"`).
   - Run the following SQL to set up the schema (see [Database Schema](#database-schema) below).

5. **Run the Application**:
   ```bash
   python app.py
   ```
   The app will be available at `http://localhost:5000`.

## Usage
1. **Access the Login Page**:
   - Open your browser and navigate to `http://localhost:5000`.
   - Choose your user type (Student, Instructor, Admin) and log in with your credentials.

2. **Default Credentials** (for testing):
   - Add users via the admin dashboard or manually insert them into the database.

3. **Dashboards**:
   - **Students**: Manage profile, enroll in courses, view grades, and check timetables.
   - **Instructors**: Update profile, view courses, assign grades, and check timetables.
   - **Admins**: Add/edit/delete records, export data, and monitor system stats.

## Project Structure
```
educational-system/
├── app.py                # Main Flask application
├── templates/
│   ├── login.html        # Login page
│   ├── student_dashboard.html  # Student dashboard
│   ├── instructor_dashboard.html  # Instructor dashboard
│   ├── admin_dashboard.html  # Admin dashboard
├── static/               # (Optional) Add static files like CSS or JS if separated
├── README.md             # This file
└── requirements.txt      # Python dependencies (create this if needed)
```

## Database Schema
The application relies on a MySQL database with the following tables:

```sql
CREATE DATABASE educationalsystem;
USE educationalsystem;

CREATE TABLE student (
    student_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(50),
    gender ENUM('male', 'female'),
    birth_date DATE,
    major VARCHAR(50),
    phone VARCHAR(11),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255)
);

CREATE TABLE instructor (
    instructor_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(50),
    gender ENUM('male', 'female'),
    department VARCHAR(50),
    title VARCHAR(50),
    phone VARCHAR(11),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255)
);

CREATE TABLE admin (
    admin_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(50),
    password VARCHAR(255)
);

CREATE TABLE course (
    course_id VARCHAR(10) PRIMARY KEY,
    course_name VARCHAR(100),
    credit DECIMAL(3,1),
    instructor_id VARCHAR(10),
    description VARCHAR(100),
    location VARCHAR(50),
    year INT,
    semester ENUM('Spring', 'Fall'),
    time_slots VARCHAR(255),
    weeks VARCHAR(255),
    FOREIGN KEY (instructor_id) REFERENCES instructor(instructor_id)
);

CREATE TABLE enrollment (
    student_id VARCHAR(10),
    course_id VARCHAR(10),
    grade DECIMAL(4,1),
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (course_id) REFERENCES course(course_id)
);
```

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Make your changes and commit (`git commit -m "Add your feature"`).
4. Push to your branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

Please ensure your code follows PEP 8 guidelines and includes appropriate comments.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
