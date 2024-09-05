import os
import smtplib
import datetime
from typing import List
from hashlib import md5
from datetime import date
from functools import wraps
from dotenv import load_dotenv
from flask_ckeditor import CKEditor
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Text, ForeignKey
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort, flash
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required


load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")


app = Flask(__name__)
ckeditor = CKEditor(app)
app.config['SECRET_KEY'] = 'SOME_KEY'
Bootstrap5(app)


login_manager = LoginManager()
login_manager.init_app(app)


class Base(DeclarativeBase):
    pass


def gravatar_url(email, size=100, rating='g', default='retro', force_default=False):
    hash_value = md5(email.lower().encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash_value}?s={size}&d={default}&r={rating}&f={force_default}"


@app.context_processor
def inject_gravatar_url():
    return dict(gravatar_url=gravatar_url)


app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))
    blogs: Mapped[List["BlogPost"]] = relationship("BlogPost", back_populates="parent")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="parent")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parent: Mapped["User"] = relationship("User", back_populates="blogs")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="parent_post",
                                                     cascade="all, delete-orphan")


class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(250), nullable=False)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parent: Mapped["User"] = relationship("User", back_populates="comments")
    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"))
    parent_post: Mapped["BlogPost"] = relationship("BlogPost", back_populates="comments")


with app.app_context():
    db.create_all()


def admin_only(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        post_id = kwargs.get('post_id')
        post = BlogPost.query.get(post_id)
        if not post:
            return page_not_found(404)
        if post.parent_id != current_user.id:
            return abort(403)
        return func(*args, **kwargs)
    return wrapper


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User()
        new_user.email = form.email.data
        new_user.password = generate_password_hash(form.password.data, 'pbkdf2:sha256', 8)
        new_user.name = form.name.data
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login', registered="True"))
        return redirect(url_for('login', registered="Already"))
    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    registered = request.args.get('registered')
    if registered == "True":
        flash('User registered successfully!')
    if registered == "Already":
        flash('User already registered. Try logging in instead.')
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
    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


def render_posts_template(posts, start=None, end=None):
    total_posts = len(posts)
    user_id = current_user.id if current_user.is_authenticated else None
    year = datetime.datetime.now().year

    if start is None:
        start = 0
    if end is None:
        end = total_posts

    start = max(0, start)
    end = min(total_posts, end)

    return render_template("index.html", year=year, posts=posts, start=start, end=end,
                           logged_in=current_user.is_authenticated, user_id=user_id, len=total_posts)


@app.route('/')
@app.route('/home')
def home():
    post_by_user_id = request.args.get('posts_by', type=int)
    posts = BlogPost.query.all()
    if post_by_user_id:
        posts = [post for post in posts if post.parent_id == post_by_user_id]
    posts = posts[::-1]
    total_posts = len(posts)
    return render_posts_template(posts=posts, start=0, end=min(total_posts, 5))


@app.route('/older_posts')
def older():
    post_by_user_id = request.args.get('posts_by', type=int)
    posts = BlogPost.query.all()
    if post_by_user_id:
        posts = [post for post in posts if post.parent_id == post_by_user_id]
    posts = posts[::-1]
    total_posts = len(posts)
    return render_posts_template(posts=posts, start=min(total_posts, 5), end=None)


@app.route("/blog/<int:post_id>", methods=['GET', 'POST'])
def blog(post_id):
    post = BlogPost.query.get(post_id)
    if not post:
        return page_not_found(404)
    result = db.session.execute(db.select(Comment).where(Comment.post_id == post_id))
    comments = result.scalars().all()
    form = CommentForm()
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        user_id = None
    if form.validate_on_submit():
        new_comment = Comment(
            date=date.today().strftime("%B %d, %Y"),
            comment=form.comment.data,
            author=current_user.name,
            parent_id=current_user.id,
            post_id=post_id
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('blog', post_id=post_id))
    return render_template("post.html", year=datetime.datetime.now().year, post=post,
                           logged_in=current_user.is_authenticated, user_id=user_id, form=form, comments=comments)


@app.route('/new-post', methods=['GET', 'POST'])
@login_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user.name,
            date=date.today().strftime("%B %d, %Y"),
            parent_id=current_user.id
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("make-post.html", form=form, action="Add new Post", logged_in=current_user.is_authenticated)


@app.route('/edit-post/<post_id>', methods=['GET', 'POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    if not post:
        return page_not_found(404)
    form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if form.validate_on_submit():
        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.body = form.body.data
        post.img_url = form.img_url.data
        post.author = current_user.name
        post.date = date.today().strftime("%B %d, %Y")
        post.parent_id = current_user.id
        db.session.commit()
        return redirect(url_for("blog", post_id=post_id))
    return render_template("make-post.html", form=form, action="Edit Post", logged_in=current_user.is_authenticated)


@app.route('/delete-post/<post_id>', methods=['GET', 'DELETE'])
@admin_only
def delete_post(post_id):
    post = BlogPost.query.get(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/delete_comment/<int:post_id>/<int:comment_id>")
def delete_comment(post_id, comment_id):
    post = db.get_or_404(BlogPost, post_id)
    comment = db.get_or_404(Comment, comment_id)
    if current_user.id == post.parent_id or current_user.id == comment.parent_id:
        db.session.delete(comment)
        db.session.commit()
    else:
        return abort(403)
    return redirect(url_for('blog', post_id=post_id))


@app.route('/about')
def about():
    year = datetime.datetime.now().year
    return render_template("about.html", year=year, logged_in=current_user.is_authenticated)


@app.route('/contact')
def contact():
    year = datetime.datetime.now().year
    return render_template("contact.html", year=year, logged_in=current_user.is_authenticated)


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
    year = datetime.datetime.now().year
    return render_template("404.html", year=year, error=error), 404


if __name__ == "__main__":
    app.run(debug=True)
