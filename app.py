from flask import Flask, render_template, request, jsonify, session, redirect, Response
import pymysql
from contextlib import contextmanager
from functools import wraps
import logging

app = Flask(__name__)
app.secret_key = "your_secret_key"

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 数据库连接上下文管理器
@contextmanager
def get_db_connection():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="root",
        database="educationalsystem",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        yield conn
    finally:
        conn.close()


@app.route("/")
def index():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user_type = data["userType"]
    id = data["id"]
    password = data["password"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_type == "student":
            query = "SELECT * FROM student WHERE student_id = %s AND password = %s"
        elif user_type == "instructor":
            query = (
                "SELECT * FROM instructor WHERE instructor_id = %s AND password = %s"
            )
        elif user_type == "admin":
            query = "SELECT * FROM admin WHERE admin_id = %s AND password = %s"
        else:
            return jsonify({"success": False, "message": "Invalid user type"})

        try:
            cursor.execute(query, (id, password))
            user = cursor.fetchone()
            if user:
                session["user_type"] = user_type
                session["id"] = id
                return jsonify({"success": True})
            return jsonify(
                {"success": False, "message": "User not found or password incorrect"}
            )
        except Exception as e:
            logger.error(f"Database error: {e}")
            return jsonify({"success": False, "error": str(e)})


@app.route("/student-dashboard")
def student_dashboard():
    if session.get("user_type") != "student":
        return redirect("/")
    return render_template("student_dashboard.html")


@app.route("/student/data")
def student_data():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM student WHERE student_id = %s", (session["id"],))
        data = cursor.fetchone()
        return jsonify(data)


@app.route("/student/courses")
def student_courses():
    year = request.args.get("year")
    semester = request.args.get("semester")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT c.course_id, c.course_name, c.credit, c.year, c.semester, c.time_slots, c.weeks, c.location, 
                   i.name as instructor_name 
            FROM course c 
            LEFT JOIN instructor i ON c.instructor_id = i.instructor_id
            WHERE c.course_id NOT IN (
                SELECT course_id FROM enrollment WHERE student_id = %s
            ) 
            AND (c.description = (SELECT major FROM student WHERE student_id = %s)
                 OR c.description = 'public')
        """
        params = [session["id"], session["id"]]
        if year and semester:
            query += " AND c.year = %s AND c.semester = %s"
            params.extend([year, semester])
        cursor.execute(query, params)
        available_courses = cursor.fetchall()

        cursor.execute(
            """
            SELECT c.course_id, c.course_name, c.time_slots, c.weeks, c.year, c.semester
            FROM enrollment e 
            JOIN course c ON e.course_id = c.course_id 
            WHERE e.student_id = %s
        """,
            (session["id"],),
        )
        enrolled_courses = cursor.fetchall()

        for course in available_courses:
            course["can_enroll"] = True
            if enrolled_courses:
                for enrolled_course in enrolled_courses:
                    if (
                        course["year"] == enrolled_course["year"]
                        and course["semester"] == enrolled_course["semester"]
                    ):
                        available_slots = course["time_slots"].split(",")
                        available_weeks = course["weeks"].split(",")
                        enrolled_slots = enrolled_course["time_slots"].split(",")
                        enrolled_weeks = enrolled_course["weeks"].split(",")

                        for i, available_slot in enumerate(available_slots):
                            available_day, available_range = available_slot.split(":")
                            available_start, available_end = map(
                                int, available_range.split("-")
                            )
                            available_week_start, available_week_end = map(
                                int, available_weeks[i].split("-")
                            )

                            for j, enrolled_slot in enumerate(enrolled_slots):
                                enrolled_day, enrolled_range = enrolled_slot.split(":")
                                enrolled_start, enrolled_end = map(
                                    int, enrolled_range.split("-")
                                )
                                enrolled_week_start, enrolled_week_end = map(
                                    int, enrolled_weeks[j].split("-")
                                )

                                if (
                                    available_day == enrolled_day
                                    and max(available_start, enrolled_start)
                                    <= min(available_end, enrolled_end)
                                    and max(available_week_start, enrolled_week_start)
                                    <= min(available_week_end, enrolled_week_end)
                                ):
                                    course["can_enroll"] = False
                                    break
                            if not course["can_enroll"]:
                                break
                    if not course["can_enroll"]:
                        break
        return jsonify(available_courses)


@app.route("/student/grades")
def student_grades():
    year = request.args.get("year")
    semester = request.args.get("semester")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT e.*, c.course_name, c.credit 
            FROM enrollment e 
            JOIN course c ON e.course_id = c.course_id 
            WHERE e.student_id = %s
        """
        params = [session["id"]]
        if year and semester:
            query += " AND c.year = %s AND c.semester = %s"
            params.extend([year, semester])
        cursor.execute(query, params)
        grades = cursor.fetchall()
        return jsonify(grades)


@app.route("/student/timetable")
def student_timetable():
    year = request.args.get("year")
    semester = request.args.get("semester")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT c.course_name, c.location, c.year, c.semester, c.time_slots, c.weeks, i.name as instructor_name
            FROM enrollment e
            JOIN course c ON e.course_id = c.course_id
            JOIN instructor i ON c.instructor_id = i.instructor_id
            WHERE e.student_id = %s
        """
        params = [session["id"]]
        if year and semester:
            query += " AND c.year = %s AND c.semester = %s"
            params.extend([year, semester])
        cursor.execute(query, params)
        timetable = cursor.fetchall()
        return jsonify(timetable)


@app.route("/student/enroll", methods=["POST"])
def enroll():
    data = request.json

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO enrollment (student_id, course_id) VALUES (%s, %s)",
                (session["id"], data["course_id"]),
            )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Enroll error: {e}")
            return jsonify({"success": False, "error": str(e)})


@app.route("/student/update", methods=["POST"])
def update_student_profile():
    if session.get("user_type") != "student":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.json

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT student_id FROM student WHERE email = %s AND student_id != %s",
                (data["email"], session["id"]),
            )
            if cursor.fetchone():
                return jsonify(
                    {
                        "success": False,
                        "error": "Email already in use by another student",
                    }
                )

            query = """
                UPDATE student 
                SET name = %s, gender = %s, birth_date = %s, major = %s, phone = %s, email = %s
            """
            params = [
                data["name"],
                data["gender"],
                data["birth_date"],
                data["major"],
                data["phone"],
                data["email"],
            ]

            if data["password"]:
                query += ", password = %s"
                params.append(data["password"])

            query += " WHERE student_id = %s"
            params.append(session["id"])

            cursor.execute(query, params)
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Update error: {e}")
            return jsonify({"success": False, "error": str(e)})


@app.route("/student/drop", methods=["POST"])
def drop_course():
    if session.get("user_type") != "student":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.json
    course_id = data["course_id"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT grade FROM enrollment 
                WHERE student_id = %s AND course_id = %s
            """,
                (session["id"], course_id),
            )
            enrollment = cursor.fetchone()

            if not enrollment:
                return jsonify({"success": False, "error": "Course not found"})
            if enrollment["grade"] is not None:
                return jsonify(
                    {"success": False, "error": "Cannot drop a course with a grade"}
                )

            cursor.execute(
                """
                DELETE FROM enrollment 
                WHERE student_id = %s AND course_id = %s
            """,
                (session["id"], course_id),
            )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Drop error: {e}")
            return jsonify({"success": False, "error": str(e)})


@app.route("/student/semesters")
def student_semesters():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT year, semester
            FROM course
            WHERE course_id IN (
                SELECT course_id FROM course
                WHERE description = (SELECT major FROM student WHERE student_id = %s)
                OR description = 'public'
            )
            ORDER BY year DESC, semester DESC
        """,
            (session["id"],),
        )
        semesters = cursor.fetchall()
        return jsonify(semesters)


@app.route("/instructor-dashboard")
def instructor_dashboard():
    if session.get("user_type") != "instructor":
        return redirect("/")
    return render_template("instructor_dashboard.html")


@app.route("/instructor/data")
def instructor_data():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM instructor WHERE instructor_id = %s", (session["id"],)
        )
        data = cursor.fetchone()
        return jsonify(data)


# 我的课程
@app.route("/instructor/courses")
def instructor_courses():
    year = request.args.get("year")
    semester = request.args.get("semester")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT course_id, course_name, credit, year, semester, time_slots, weeks, location 
            FROM course 
            WHERE instructor_id = %s
        """
        params = [session["id"]]
        if year and semester:
            query += " AND year = %s AND semester = %s"
            params.extend([year, semester])
        cursor.execute(query, params)
        courses = cursor.fetchall()

        for course in courses:
            schedules = course["time_slots"].split(",")
            weeks = course["weeks"].split(",")
            schedule_str = []
            for i, schedule in enumerate(schedules):
                day_str, slot_range = schedule.split(":")
                days = [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ]
                day = days[int(day_str) - 1]
                week_range = weeks[i].split("-")
                schedule_str.append(
                    f"{day} Periods {slot_range} (Weeks {week_range[0]}-{week_range[1]})"
                )
            course["schedule"] = f"{course['year']} {course['semester']} " + ", ".join(
                schedule_str
            )
        return jsonify(courses)


@app.route("/instructor/enrollments")
def instructor_enrollments():
    course_id = request.args.get("course_id")
    year = request.args.get("year")
    semester = request.args.get("semester")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT e.student_id, s.name as student_name, e.course_id, c.course_name, e.grade
            FROM enrollment e
            JOIN student s ON e.student_id = s.student_id
            JOIN course c ON e.course_id = c.course_id
            WHERE c.instructor_id = %s
        """
        params = [session["id"]]
        if course_id:
            query += " AND e.course_id = %s"
            params.append(course_id)
        if year and semester:
            query += " AND c.year = %s AND c.semester = %s"
            params.extend([year, semester])
        cursor.execute(query, params)
        enrollments = cursor.fetchall()
        return jsonify(enrollments)


@app.route("/instructor/update", methods=["POST"])
def update_instructor_profile():
    if session.get("user_type") != "instructor":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.json

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT instructor_id FROM instructor WHERE email = %s AND instructor_id != %s",
                (data["email"], session["id"]),
            )
            if cursor.fetchone():
                return jsonify(
                    {
                        "success": False,
                        "error": "Email already in use by another instructor",
                    }
                )

            query = """
                UPDATE instructor 
                SET name = %s, gender = %s, department = %s, title = %s, phone = %s, email = %s
            """
            params = [
                data["name"],
                data["gender"],
                data["department"],
                data["title"],
                data["phone"],
                data["email"],
            ]

            if data["password"]:
                query += ", password = %s"
                params.append(data["password"])

            query += " WHERE instructor_id = %s"
            params.append(session["id"])

            cursor.execute(query, params)
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Update error: {e}")
            return jsonify({"success": False, "error": str(e)})


@app.route("/instructor/assign_grade", methods=["POST"])
def assign_grade():
    if session.get("user_type") != "instructor":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.json
    student_id = data["student_id"]
    course_id = data["course_id"]
    grade = float(data["grade"])

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT instructor_id FROM course WHERE course_id = %s", (course_id,)
            )
            course = cursor.fetchone()
            if not course or course["instructor_id"] != session["id"]:
                return jsonify(
                    {
                        "success": False,
                        "error": "You are not authorized to grade this course",
                    }
                )

            cursor.execute(
                """
                UPDATE enrollment 
                SET grade = %s 
                WHERE student_id = %s AND course_id = %s
            """,
                (grade, student_id, course_id),
            )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Assign grade error: {e}")
            return jsonify({"success": False, "error": str(e)})


@app.route("/instructor/timetable")
def instructor_timetable():
    year = request.args.get("year")
    semester = request.args.get("semester")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT course_name, location, year, semester, time_slots, weeks
            FROM course
            WHERE instructor_id = %s
        """
        params = [session["id"]]
        if year and semester:
            query += " AND year = %s AND semester = %s"
            params.extend([year, semester])
        cursor.execute(query, params)
        timetable = cursor.fetchall()
        return jsonify(timetable)


@app.route("/instructor/semesters")
def instructor_semesters():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT year, semester
            FROM course
            WHERE instructor_id = %s
            ORDER BY year DESC, semester DESC
        """,
            (session["id"],),
        )
        semesters = cursor.fetchall()
        return jsonify(semesters)


# 通用验证函数
def validate_phone(phone):
    return phone.isdigit() and len(phone) == 11


# 检查唯一性
def check_unique(cursor, table, field, value, exclude_id=None):
    # 白名单限制 table 和 field
    allowed_tables = ["student", "instructor", "course"]
    allowed_fields = ["student_id", "instructor_id", "course_id", "email"]
    if table not in allowed_tables or field not in allowed_fields:
        raise ValueError("Invalid table or field")

    query = f"SELECT 1 FROM {table} WHERE {field} = %s"
    params = [value]
    if exclude_id:
        query += f" AND {field} != %s"
        params.append(exclude_id)
    cursor.execute(query, params)
    return not cursor.fetchone()


# 管理员权限装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_type") != "admin":
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        return f(*args, **kwargs)

    return decorated_function


# 管理员仪表板
@app.route("/admin-dashboard")
def admin_dashboard():
    if session.get("user_type") != "admin":
        return redirect("/")
    return render_template("admin_dashboard.html")


@app.route("/admin/data")
@admin_required
def admin_data():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM admin WHERE admin_id = %s", (session["id"],))
        admin = cursor.fetchone()
        if admin:
            return jsonify({"success": True, "admin_name": admin["name"]})
        return jsonify({"success": False, "error": "Admin not found"}), 404


@app.route("/admin/stats")
@admin_required
def admin_stats():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM student")
        student_count = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count FROM instructor")
        instructor_count = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count FROM course")
        course_count = cursor.fetchone()["count"]
        return jsonify(
            {
                "student_count": student_count,
                "instructor_count": instructor_count,
                "course_count": course_count,
            }
        )


@app.route("/admin/students")
@admin_required
def admin_students():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.*, COUNT(e.course_id) as course_count
            FROM student s
            LEFT JOIN enrollment e ON s.student_id = e.student_id
            GROUP BY s.student_id
            """
        )
        students = cursor.fetchall()
        return jsonify(students)


@app.route("/admin/instructors")
@admin_required
def admin_instructors():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT instructor_id, name, gender, phone, email, department, title FROM instructor"
        )
        instructors = cursor.fetchall()
        return jsonify(instructors)


@app.route("/admin/courses")
@admin_required
def admin_courses():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.*, i.name as instructor_name 
            FROM course c 
            LEFT JOIN instructor i ON c.instructor_id = i.instructor_id
            """
        )
        courses = cursor.fetchall()
        return jsonify(courses)


@app.route("/admin/unique_values")
@admin_required
def unique_values():
    table = request.args.get("table")
    if table != "course":
        return jsonify({"error": "Invalid table"}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()
        columns = [
            "course_id",
            "course_name",
            "credit",
            "instructor_name",
            "description",
            "location",
            "year",
            "semester",
            "time_slots",
            "weeks",
        ]
        unique_values = {}

        for column in columns:
            if column == "instructor_name":
                query = """
                    SELECT DISTINCT i.name as instructor_name
                    FROM course c
                    LEFT JOIN instructor i ON c.instructor_id = i.instructor_id
                    ORDER BY instructor_name
                """
                cursor.execute(query)
            else:
                query = f"SELECT DISTINCT {column} FROM course ORDER BY {column}"
                cursor.execute(query)
            values = cursor.fetchall()
            unique_values[column] = [
                row[column] for row in values if row[column] is not None
            ]

        return jsonify(unique_values)


@app.route("/admin/add_student", methods=["POST"])
@admin_required
def add_student():
    data = request.json
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if not check_unique(cursor, "student", "student_id", data["student_id"]):
                return (
                    jsonify({"success": False, "error": "Student ID already exists"}),
                    400,
                )
            if not check_unique(cursor, "student", "email", data["email"]):
                return jsonify({"success": False, "error": "Email already in use"}), 400
            if not validate_phone(data["phone"]):
                return (
                    jsonify(
                        {"success": False, "error": "Phone number must be 11 digits"}
                    ),
                    400,
                )
            cursor.execute(
                "INSERT INTO student (student_id, name, gender, birth_date, major, phone, email, password) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    data["student_id"],
                    data["name"],
                    data["gender"],
                    data["birth_date"],
                    data["major"],
                    data["phone"],
                    data["email"],
                    data["password"],
                ),
            )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Add student error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/update_student", methods=["POST"])
@admin_required
def update_student():
    data = request.json
    old_student_id = data["student_id"]
    new_student_id = data.get("new_student_id", old_student_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if new_student_id != old_student_id and not check_unique(
                cursor, "student", "student_id", new_student_id
            ):
                return (
                    jsonify(
                        {"success": False, "error": "New Student ID already exists"}
                    ),
                    400,
                )
            if not check_unique(
                cursor, "student", "email", data["email"], old_student_id
            ):
                return jsonify({"success": False, "error": "Email already in use"}), 400
            if not validate_phone(data["phone"]):
                return (
                    jsonify(
                        {"success": False, "error": "Phone number must be 11 digits"}
                    ),
                    400,
                )
            query = "UPDATE student SET student_id = %s, name = %s, gender = %s, birth_date = %s, major = %s, phone = %s, email = %s"
            params = [
                new_student_id,
                data["name"],
                data["gender"],
                data["birth_date"],
                data["major"],
                data["phone"],
                data["email"],
            ]
            if data["password"]:
                query += ", password = %s"
                params.append(data["password"])
            query += " WHERE student_id = %s"
            params.append(old_student_id)
            cursor.execute(query, params)
            if new_student_id != old_student_id:
                cursor.execute(
                    "UPDATE enrollment SET student_id = %s WHERE student_id = %s",
                    (new_student_id, old_student_id),
                )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Update student error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/add_instructor", methods=["POST"])
@admin_required
def add_instructor():
    data = request.json
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if not check_unique(
                cursor, "instructor", "instructor_id", data["instructor_id"]
            ):
                return (
                    jsonify(
                        {"success": False, "error": "Instructor ID already exists"}
                    ),
                    400,
                )
            if not check_unique(cursor, "instructor", "email", data["email"]):
                return jsonify({"success": False, "error": "Email already in use"}), 400
            if not validate_phone(data["phone"]):
                return (
                    jsonify(
                        {"success": False, "error": "Phone number must be 11 digits"}
                    ),
                    400,
                )
            cursor.execute(
                "INSERT INTO instructor (instructor_id, name, gender, department, title, phone, email, password) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    data["instructor_id"],
                    data["name"],
                    data["gender"],
                    data["department"],
                    data["title"],
                    data["phone"],
                    data["email"],
                    data["password"],
                ),
            )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Add instructor error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/update_instructor", methods=["POST"])
@admin_required
def update_instructor():
    data = request.json
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if not check_unique(
                cursor, "instructor", "email", data["email"], data["instructor_id"]
            ):
                return jsonify({"success": False, "error": "Email already in use"}), 400
            if not validate_phone(data["phone"]):
                return (
                    jsonify(
                        {"success": False, "error": "Phone number must be 11 digits"}
                    ),
                    400,
                )
            query = "UPDATE instructor SET name = %s, gender = %s, department = %s, title = %s, phone = %s, email = %s"
            params = [
                data["name"],
                data["gender"],
                data["department"],
                data["title"],
                data["phone"],
                data["email"],
            ]
            if data["password"]:
                query += ", password = %s"
                params.append(data["password"])
            query += " WHERE instructor_id = %s"
            params.append(data["instructor_id"])
            cursor.execute(query, params)
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Update instructor error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/add_course", methods=["POST"])
@admin_required
def add_course():
    data = request.json
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if not check_unique(cursor, "course", "course_id", data["course_id"]):
                return (
                    jsonify({"success": False, "error": "Course ID already exists"}),
                    400,
                )
            if data["instructor_id"] and not cursor.execute(
                "SELECT 1 FROM instructor WHERE instructor_id = %s",
                (data["instructor_id"],),
            ):
                return (
                    jsonify(
                        {"success": False, "error": "Instructor ID does not exist"}
                    ),
                    400,
                )
            if data["credit"] and (
                not str(data["credit"]).replace(".", "").isdigit()
                or float(data["credit"]) <= 0
            ):
                return (
                    jsonify(
                        {"success": False, "error": "Credit must be a positive number"}
                    ),
                    400,
                )
            if data["semester"] not in ["Spring", "Fall"]:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Semester must be 'Spring' or 'Fall'",
                        }
                    ),
                    400,
                )
            cursor.execute(
                """
                INSERT INTO course (course_id, course_name, credit, instructor_id, description, 
                                    location, year, semester, time_slots, weeks)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    data["course_id"],
                    data["course_name"],
                    data["credit"],
                    data["instructor_id"],
                    data["description"],
                    data["location"],
                    data["year"],
                    data["semester"],
                    data["time_slots"],
                    data["weeks"],
                ),
            )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Add course error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/update_course", methods=["POST"])
@admin_required
def update_course():
    data = request.json
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if data["instructor_id"] and not cursor.execute(
                "SELECT 1 FROM instructor WHERE instructor_id = %s",
                (data["instructor_id"],),
            ):
                return (
                    jsonify(
                        {"success": False, "error": "Instructor ID does not exist"}
                    ),
                    400,
                )
            if data["credit"] and (
                not str(data["credit"]).replace(".", "").isdigit()
                or float(data["credit"]) <= 0
            ):
                return (
                    jsonify(
                        {"success": False, "error": "Credit must be a positive number"}
                    ),
                    400,
                )
            if data["semester"] not in ["Spring", "Fall"]:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Semester must be 'Spring' or 'Fall'",
                        }
                    ),
                    400,
                )
            cursor.execute(
                """
                UPDATE course 
                SET course_name = %s, credit = %s, instructor_id = %s, description = %s, 
                    location = %s, year = %s, semester = %s, time_slots = %s, weeks = %s
                WHERE course_id = %s
                """,
                (
                    data["course_name"],
                    data["credit"],
                    data["instructor_id"],
                    data["description"],
                    data["location"],
                    data["year"],
                    data["semester"],
                    data["time_slots"],
                    data["weeks"],
                    data["course_id"],
                ),
            )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Update course error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/delete", methods=["POST"])
@admin_required
def delete_record():
    data = request.json
    table = data["table"]
    ids = data.get("ids", []) if "ids" in data else [data["id"]]
    id_field = {
        "student": "student_id",
        "instructor": "instructor_id",
        "course": "course_id",
    }[table]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            for id in ids:
                if table == "student":
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM enrollment WHERE student_id = %s",
                        (id,),
                    )
                    if cursor.fetchone()["count"] > 0:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": f"Cannot delete student {id} with enrollment records",
                                }
                            ),
                            400,
                        )
                elif table == "instructor":
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM course WHERE instructor_id = %s",
                        (id,),
                    )
                    if cursor.fetchone()["count"] > 0:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": f"Cannot delete instructor {id} with assigned courses",
                                }
                            ),
                            400,
                        )
                elif table == "course":
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM enrollment WHERE course_id = %s",
                        (id,),
                    )
                    if cursor.fetchone()["count"] > 0:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": f"Cannot delete course {id} with enrollment records",
                                }
                            ),
                            400,
                        )
                cursor.execute(f"DELETE FROM {table} WHERE {id_field} = %s", (id,))
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/export/<table>")
@admin_required
def export_table(table):
    def generate_csv():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = {
                "students": "SELECT * FROM student",
                "instructors": "SELECT * FROM instructor",
                "courses": "SELECT * FROM course",
            }.get(table)
            if not query:
                yield "Invalid table\n"
                return
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            yield ",".join(columns) + "\n"
            for row in cursor:
                yield ",".join(
                    str(row[col]) if row[col] is not None else "" for col in columns
                ) + "\n"

    return Response(
        generate_csv(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table}.csv"},
    )


# app.py 中添加新的路由
@app.route("/admin/course_distribution")
@admin_required
def course_distribution():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(e.course_id) as course_count, COUNT(*) as student_count
            FROM student s
            LEFT JOIN enrollment e ON s.student_id = e.student_id
            GROUP BY s.student_id
            """
        )
        data = cursor.fetchall()
        distribution = {"0": 0, "1-3": 0, "4+": 0}
        for row in data:
            count = row["course_count"] or 0
            if count == 0:
                distribution["0"] += 1
            elif 1 <= count <= 3:
                distribution["1-3"] += 1
            else:
                distribution["4+"] += 1
        return jsonify(distribution)


@app.route("/admin/credit_stats")
@admin_required
def credit_stats():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT credit, COUNT(*) as count FROM course GROUP BY credit")
        stats = cursor.fetchall()
        return jsonify(
            {str(row["credit"]): row["count"] for row in stats if row["credit"]}
        )


if __name__ == "__main__":
    app.run(debug=True)  # host='10.67.64.206',
