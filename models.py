from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum

db = SQLAlchemy()

class BaseModel(db.Model):
    __abstract__ = True
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(),
                          onupdate=db.func.current_timestamp())


# User model (for Admin and Teacher users)
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    # Relationship: a user can create many subjects
    subjects = db.relationship('Subject', backref='teacher', lazy=True)

    # Relationship: a user can create many lectures
    lectures = db.relationship('Lecture', backref='teacher', lazy=True)

    def __repr__(self):
        return f"<User {self.name}>"


class Batch(db.Model):
    __tablename__ = 'batches'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    # Relationship: a batch can have many students
    students = db.relationship('Student', backref='batch', lazy=True)

    def __repr__(self):
        return f"<Batch {self.name}>"


# Student model
class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    enrollment_number = db.Column(db.String(20), unique=True, nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=False)

    # Relationship: a student can have multiple attendance records
    attendance = db.relationship('Attendance', backref='student', lazy=True)

    def __repr__(self):
        return f"<Student {self.student_name} ({self.enrollment_number})>"


# Subject model
class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    lectures = db.relationship('Lecture', back_populates='subject')

    def __repr__(self):
        return f"<Subject {self.subject_name}>"


# Lecture model
class Lecture(db.Model):
    __tablename__ = 'lectures'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=False)

    # Relationships
    subject = db.relationship('Subject', back_populates='lectures')  # Fix: Use back_populates
    batch = db.relationship('Batch', backref='lectures')  # This backref is unique
    attendance = db.relationship('Attendance', backref='lecture', lazy=True)

    def __repr__(self):
        return f"<Lecture {self.id} for Subject {self.subject_id} on {self.timestamp}>"


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Boolean, nullable=False)

    # Foreign keys for relationships
    lecture_id = db.Column(db.Integer, db.ForeignKey('lectures.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)

    def __repr__(self):
        return f"<Attendance Lecture {self.lecture_id} - {'Present' if self.status else 'Absent'} for {self.student_id}>"


class AttendanceStats:
    @staticmethod
    def get_percentage(student_id, subject_id):
        # Use a single query to calculate total and attended lectures
        result = db.session.query(
            db.func.count(Lecture.id).label('total_lectures'),
            db.func.sum(
                db.case((Attendance.status == 'TRUE', 1), else_=0)
            ).label('attended_lectures')
        ).outerjoin(
            Attendance, Attendance.lecture_id == Lecture.id
        ).filter(
            Lecture.subject_id == subject_id
        ).filter(
            Attendance.student_id == student_id
        ).first()

        total_lectures = result.total_lectures or 0
        attended_lectures = result.attended_lectures or 0

        if total_lectures == 0:
            return 0  # Avoid division by zero

        percentage = (attended_lectures / total_lectures) * 100
        return round(percentage, 2)  # Return rounded percentage
