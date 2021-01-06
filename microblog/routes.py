from flask import render_template, request, flash, redirect, url_for
from microblog import app, db, bcrypt
from microblog.forms import RegistrationForm, LoginForm, UpdateAccountForm
from microblog.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os

from pymongo import MongoClient
import datetime

client = MongoClient("mongodb+srv://xxxxxxxxxxxxxxxxxxxx@microblog.a8b2r.mongodb.net/test")
app.db = client.microblog


@app.route("/")
def landing():
    return redirect(url_for('home')) if current_user.is_authenticated else render_template('landing.html')


@app.route("/home/", methods=["GET", "POST"])
def home():
    if not current_user.is_authenticated:
        flash("Please login to access this page", "flash_success")
        return redirect(url_for('login'))

    if request.method == "POST":
        entry_content = request.form.get("content")
        date = datetime.datetime.today().strftime("%Y-%m-%d")

        # Saving form data into MongoDB
        app.db.entries.insert({"content": entry_content, "date": date})

    # Retrieving data from MongoDB
    # We receive a list of dicts (actually a cursor object)

    entries = []
    for entry in app.db.entries.find({}):
        data = (
            entry["content"],
            entry["date"],
            datetime.datetime.strptime(entry['date'], "%Y-%m-%d").strftime("%b %d")
        )

        entries.append(data)

    return render_template('home.html', entries=entries)


@app.route("/register/", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Your account has been created! You can now login', 'flash_success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route("/login/", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')

            if next_page:
                return redirect(next_page)

            return redirect(url_for('home'))
        else:
            flash(f'Login unsuccessful! Incorrect email or password', 'flash_fail')
    return render_template('login.html', form=form)


@app.route("/logout/")
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/account/")
@login_required
def account():
    return render_template('account.html')


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    form_picture.save(picture_path)
    return picture_fn

@app.route("/update/", methods=["GET", "POST"])
@login_required
def update():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture:
            picture_fn = save_picture(form.picture.data)
            current_user.profile_pic = picture_fn
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Account Updated', 'flash_success')
        return redirect(url_for('account'))

    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email

    return render_template('update.html', form=form)

