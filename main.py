import os
import smtplib
from functools import wraps
from dotenv import load_dotenv
from flask_bootstrap import Bootstrap5
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Batch, Student, Subject, Lecture, Attendance, AttendanceStats
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort, flash
from flask_login import login_user, LoginManager, current_user, logout_user, login_required
from forms import UserRegistrationForm, SubjectForm, StudentForm, LectureForm, AttendanceForm, AttendanceReportForm, \
    UserLoginForm, BatchForm

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")
SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")


app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
Bootstrap5(app)


login_manager = LoginManager()
login_manager.init_app(app)


app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
db.init_app(app)


with app.app_context():
    db.create_all()


def admin_only(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            return abort(403)
        return func(*args, **kwargs)
    return wrapper


def taker_only(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        lecture_id = kwargs.get('lecture_id')
        lecture = Lecture.query.get(lecture_id)
        if not lecture:
            return page_not_found(404)
        if lecture.teacher_id != current_user.id:
            return abort(403)
        return func(*args, **kwargs)
    return wrapper


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/register', methods=['GET', 'POST'])
@admin_only
def register():
    image = '../static/assets/img/register-bg.jpg'
    curr_user = current_user if current_user.is_authenticated else None
    form = UserRegistrationForm()
    if form.validate_on_submit():
        new_user = User()
        new_user.email = form.email.data
        new_user.password = generate_password_hash(form.password.data, 'pbkdf2:sha256', 8)
        new_user.name = form.name.data
        new_user.is_admin = form.is_admin.data

        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! You can now log in.")
        else:
            flash("This email is already registered.")
    return render_template("forms.html", form=form, user=curr_user, action="Register",
                           phrase="Start Contributing to the Blog!", image=image)


@app.route('/login', methods=['GET', 'POST'])
def login():
    image = '../static/assets/img/login-bg.jpg'
    form = UserLoginForm()
    user = current_user if current_user.is_authenticated else None
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for("home"))
            else:
                flash("Wrong Password Entered.")
        else:
            flash("User doesn't exist. Consider Registering!")
    return render_template("forms.html", form=form, user=user, action="Log In", phrase="Welcome Back!", image=image)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


def render_lectures_template(lectures, start=None, end=None):
    total_lectures = len(lectures)
    user = current_user if current_user.is_authenticated else None
    year = datetime.now().year

    if start is None:
        start = 0
    if end is None:
        end = total_lectures

    start = max(0, start)
    end = min(total_lectures, end)

    return render_template("index.html", year=year, lectures=lectures, start=start, end=end,
                           user=user, len=total_lectures)


@app.route('/')
@app.route('/home')
def home():
    # Find lectures where all attendance records are marked as False (absent)
    lectures_with_no_attendance = (
        Lecture.query
        .outerjoin(Attendance)
        .group_by(Lecture.id)
        .having(db.func.count(Attendance.id) == 0)  # No attendance records
        .all()
    )

    # Find lectures where all attendance records are marked 'False' (absent)
    lectures_with_all_absent = (
        Lecture.query
        .join(Attendance)
        .group_by(Lecture.id)
        .having(db.func.count(Attendance.id) == db.func.count(Attendance.id).filter(
            Attendance.status == False))  # All students absent
        .all()
    )

    # Combine both queries
    lectures_to_delete = set(lectures_with_no_attendance) | set(lectures_with_all_absent)

    # Delete attendance records for these lectures
    for lecture in lectures_to_delete:
        # Delete all attendance records related to the lecture
        Attendance.query.filter_by(lecture_id=lecture.id).delete()

    # Delete the lectures themselves
    for lecture in lectures_to_delete:
        db.session.delete(lecture)

    # Commit the changes
    db.session.commit()

    # Fetch all lectures and reverse for latest-first display
    lectures = Lecture.query.order_by(Lecture.timestamp.desc()).all()
    total_lectures = len(lectures)

    return render_lectures_template(lectures=lectures, start=0, end=min(total_lectures, 5))


@app.route('/older_lectures')
def older():
    lectures = Lecture.query.all()
    lectures = lectures[::-1]
    total_lectures = len(lectures)
    return render_lectures_template(lectures=lectures, start=min(total_lectures, 5), end=None)


@app.route("/attendance/", methods=['GET', 'POST'])
def get_attendance():
    form = AttendanceReportForm()
    image = '../static/assets/img/post-bg.jpg'
    user = current_user if current_user.is_authenticated else None

    # Populate the choices for subject and batch
    form.subject.choices = [(subject.id, subject.subject_name) for subject in Subject.query.all()]
    form.batch.choices = [(batch.id, batch.name) for batch in Batch.query.all()]

    attendance_data = None

    if form.validate_on_submit():
        subject_id = form.subject.data
        batch_id = form.batch.data

        # Calculate attendance percentages
        students = Student.query.filter_by(batch_id=batch_id).all()
        attendance_data = []

        for student in students:
            percentage = AttendanceStats.get_percentage(student.id, subject_id)
            attendance_data.append({
                'student_name': student.student_name,
                'enrollment_number': student.enrollment_number,
                'percentage': percentage
            })

        attendance_data = sorted(attendance_data, key=lambda x: x['percentage'], reverse=True)

        for idx, record in enumerate(attendance_data, start=1):
            record['rank'] = idx

    return render_template(
        "forms.html",
        form=form,
        user=user,
        action="Attendance",
        phrase="Get Attendance Report!",
        image=image,
        attendance_data=attendance_data
    )


@app.route("/lecture/<int:lecture_id>", methods=['GET', 'POST'])
def get_lecture_attendance(lecture_id):
    return redirect(
        url_for(
            'mark_attendance',
            lecture_id=lecture_id,
        )
    )


@app.route('/new-lecture', methods=['GET', 'POST'])
@login_required
def add_new_lecture():
    form = LectureForm()
    # Populate subject choices for the current teacher
    form.subject.choices = [(s.id, s.subject_name) for s in Subject.query.filter_by(teacher_id=current_user.id).all()]
    form.batch.choices = [(batch.id, batch.name) for batch in Batch.query.all()]

    if request.method == 'POST' and form.validate_on_submit():
        # Create new lecture
        new_lecture = Lecture(
            subject_id=form.subject.data,
            teacher_id=current_user.id,
            batch_id=form.batch.data,
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(new_lecture)
        db.session.commit()
        flash('Lecture created successfully!', 'success')

        # Redirect to mark attendance for this lecture and batch
        return redirect(
            url_for(
                'mark_attendance',
                lecture_id=new_lecture.id,
            )
        )

    image = '../static/assets/img/post-bg.jpg'
    return render_template(
        'forms.html',
        form=form,
        user=current_user,
        action="Add New Lecture",
        phrase="Create a new lecture and proceed to mark attendance.",
        image=image
    )


@app.route('/mark-attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    lecture_id = request.args.get('lecture_id', type=int)
    lecture = Lecture.query.get_or_404(lecture_id)
    batch_id = lecture.batch_id

    # Sort students based on enrollment number
    students = Student.query.filter_by(batch_id=batch_id).order_by(Student.enrollment_number).all()

    if not students:
        flash("No students found in the selected batch.", "danger")
        return redirect(url_for('home'))

    # Fetch existing attendance records for the lecture
    existing_attendance = {att.student_id: att.status for att in Attendance.query.filter_by(lecture_id=lecture_id).all()}

    form = AttendanceForm()
    form.lecture_id.data = lecture_id

    if request.method == 'POST' and form.validate_on_submit():
        attendance_records = []
        for student in students:
            # Check if attendance is marked as "Present" (checkbox is ticked)
            attendance_status = request.form.get(f'attendance_{student.id}') == 'on'
            existing_record = existing_attendance.get(student.id)

            if existing_record is None:
                # Create new record if no existing record is found
                attendance_records.append(Attendance(
                    lecture_id=lecture_id,
                    student_id=student.id,
                    status=attendance_status
                ))
            elif existing_record != attendance_status:
                # Update the record only if the status has changed
                attendance = Attendance.query.filter_by(lecture_id=lecture_id, student_id=student.id).first()
                attendance.status = attendance_status

        if attendance_records:
            db.session.bulk_save_objects(attendance_records)
        db.session.commit()

        flash("Attendance marked successfully!", "success")
        return redirect(url_for('home'))

    # Prepare the pre-checked status for each student based on existing attendance
    attendance_status_map = {
        student.id: existing_attendance.get(student.id, False) for student in students
    }

    image = '../static/assets/img/post-bg.jpg'
    return render_template(
        'mark_attendance.html',
        form=form,
        lecture_id=lecture_id,
        batch_id=batch_id,
        students=students,
        attendance_status_map=attendance_status_map,
        user=current_user,
        action="Mark Attendance",
        phrase=f"Mark attendance for Lecture {lecture_id} - {lecture.subject.subject_name}",
        image=image
    )


@app.route('/delete-lecture/<lecture_id>', methods=['GET', 'DELETE'])
@taker_only
def delete_lecture(lecture_id):
    lecture = db.session.query(Lecture).get(lecture_id)
    db.session.query(Attendance).filter_by(lecture_id=lecture_id).delete()
    db.session.delete(lecture)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/add-subject/', methods=['GET', 'POST'])
@login_required
def add_new_subject():
    form = SubjectForm()

    if form.validate_on_submit():
        # Create the new subject
        new_subject = Subject(
            subject_name=form.subject_name.data,
            teacher_id=current_user.id
        )
        db.session.add(new_subject)
        db.session.commit()

        flash('Subject created successfully!', 'success')
        return redirect(url_for('add_new_lecture'))

    image = '../static/assets/img/post-bg.jpg'
    return render_template(
        'forms.html',
        form=form,
        user=current_user,
        action="Add New Subject",
        phrase="Create a new subject for your courses.",
        image=image
    )


@app.route('/add-batch', methods=['GET', 'POST'])
@admin_only
def add_new_batch():
    form = BatchForm()

    if request.method == 'POST' and form.validate_on_submit():
        batch_name = form.batch_name.data

        # Check if the batch already exists
        existing_batch = Batch.query.filter_by(name=batch_name).first()
        if existing_batch:
            flash(f"A batch with the name '{batch_name}' already exists.", "danger")
            return redirect(url_for('add_new_batch'))

        # Create and add the new batch to the database
        new_batch = Batch(name=batch_name)
        db.session.add(new_batch)
        db.session.commit()

        flash(f"Batch '{batch_name}' created successfully!", "success")
        return redirect(url_for('add_new_student'))

    image = '../static/assets/img/post-bg.jpg'
    return render_template(
        'forms.html',
        form=form,
        user=current_user,
        action="Add New Batch",
        phrase="Create a new batch for your courses.",
        image=image
    )


@app.route('/add-student/', methods=['GET', 'POST'])
@admin_only
def add_new_student():
    form = StudentForm()
    form.batch.choices = [(batch.id, batch.name) for batch in Batch.query.all()]

    if request.method == 'POST' and form.validate_on_submit():
        # Get the form data and create a new Student record
        student_name = form.student_name.data
        enrollment_number = form.enrollment_number.data
        batch_id = form.batch.data  # Assuming batch is selected from the form

        # Check if the enrollment number already exists
        existing_student = Student.query.filter_by(enrollment_number=enrollment_number).first()
        if existing_student:
            flash("A student with this enrollment number already exists!", "danger")
            return redirect(url_for('add_new_student'))

        # Create and save the new student to the database
        new_student = Student(
            student_name=student_name,
            enrollment_number=enrollment_number,
            batch_id=batch_id
        )
        db.session.add(new_student)
        db.session.commit()

        flash("Student added successfully!", "success")
        return redirect(url_for('add_new_student'))

    # Set the image for the header
    image = '../static/assets/img/post-bg.jpg'
    return render_template(
        'forms.html',
        form=form,
        user=current_user,
        action="Add New Student",
        phrase="Create a new student record for your courses.",
        image=image
    )


@app.route('/about')
def about():
    year = datetime.now().year
    return render_template("about.html", year=year, user=current_user)


@app.route('/contact')
def contact():
    year = datetime.now().year
    return render_template("contact.html", year=year, user=current_user)


@app.route('/send_mail', methods=["POST"])
def send_mail():
    try:
        data = request.get_json()
        if not data:
            raise ValueError("No data received")

        if request.method == 'POST':
            with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
                connection.starttls()
                connection.login(EMAIL, PASSWORD)
                connection.sendmail(
                    EMAIL,
                    EMAIL,
                    msg=f"Subject: New Contact Form Submission\n\n"
                        f"Name: {data['name']}\n"
                        f"Email: {data['email']}\n"
                        f"Phone: {data['phone']}\n"
                        f"Message: {data['message']}"
                )

        return jsonify({"message": "Form submission successful!"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Error processing the form submission."}), 500


@app.errorhandler(404)
def page_not_found(error):
    year = datetime.now().year
    return render_template("404.html", year=year, error=error), 404


if __name__ == "__main__":
    app.run(debug=True)