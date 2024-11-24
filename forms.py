from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField, EmailField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp
from wtforms.fields import HiddenField


# User Registration Form (for Admin to register Teachers)
class UserRegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    is_admin = BooleanField('Admin', default=False)
    submit = SubmitField('Register')


class UserLoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


# Subject Creation Form
class SubjectForm(FlaskForm):
    subject_name = StringField('Subject Name', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Create Subject')


# Student Creation Form
class StudentForm(FlaskForm):
    student_name = StringField('Student Name', validators=[DataRequired(), Length(min=2, max=100)])
    enrollment_number = StringField(
        'Enrollment Number',
        validators=[
            DataRequired(),
            Length(min=12, max=12),  # Length validation for enrollment numbers
            Regexp(
                r'^\d{4}[A-Z]{2}\d{3}[A-Z0-9]\d{2}$',
                message="Enrollment number must follow the pattern: 4 digits, 2 letters, 3 digits, 1 alphanumeric, and 2 digits."
            )
        ]
    )
    batch = SelectField('Batch', coerce=int, validators=[DataRequired()])  # Batch choices to be populated dynamically
    submit = SubmitField('Create Student')



# Lecture Selection Form (Formerly SelectSubjectBatchForm)
class LectureForm(FlaskForm):
    subject = SelectField('Subject', coerce=int, validators=[DataRequired()])  # Choices to be populated dynamically
    batch = SelectField('Batch', coerce=int, validators=[DataRequired()])  # Choices to be populated dynamically
    submit = SubmitField('Proceed to Mark Attendance')


# Attendance Form
class AttendanceForm(FlaskForm):
    lecture_id = HiddenField(validators=[DataRequired()])  # Stores the selected lecture ID
    students = []  # Dynamic list to hold student fields for marking attendance

    def generate_student_fields(self, student_list):
        """ Dynamically adds a checkbox for each student in the batch. """
        for student in student_list:
            field = BooleanField(f"{student.student_name} - {student.enrollment_number}")
            field.student_id = student.id  # Attach student ID for processing
            self.students.append(field)
        return self

    submit = SubmitField('Submit Attendance')


# Attendance Report Form
class AttendanceReportForm(FlaskForm):
    subject = SelectField('Subject', coerce=int, validators=[DataRequired()])  # Populated dynamically
    batch = SelectField('Batch', coerce=int, validators=[DataRequired()])  # Populated dynamically
    submit = SubmitField('View Attendance Report')
