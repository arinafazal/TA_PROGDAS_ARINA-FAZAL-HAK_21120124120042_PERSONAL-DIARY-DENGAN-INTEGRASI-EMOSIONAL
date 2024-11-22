import os
import re
from os.path import join, dirname
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

class DiaryApp:
    def __init__(self):
        dotenv_path = join(dirname(__file__), '.env')
        load_dotenv(dotenv_path)

        self.app = Flask(__name__)
        self.app.secret_key = os.urandom(24)

        self.client = MongoClient(os.environ.get("MONGODB_URI"))
        self.db = self.client[os.environ.get("DB_NAME")]

        self.MINIMAL_PW = 8
        self.EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

        self.register_routes()

    def is_valid_email(self, email):
        """
        Validates email with a regex.
        """
        return re.match(self.EMAIL_REGEX, email) is not None

    def validate_registration_form(self, username, email, password):
        """
        Validates the registration form.
        """
        validation_rules = [
            (not username.strip()),
            (not self.is_valid_email(email)),
            (len(password) < self.MINIMAL_PW),
        ]

        return None

    def register_routes(self):
        app = self.app

        @app.route('/')
        def index():
            """
            Main diary index page.
            """
            if "user_id" not in session:
                return redirect(url_for("login"))

            entries_cursor = self.db.diary_users.find({"user_id": session["user_id"]})
            entries_stack = [entry for entry in entries_cursor]

            return render_template(
                'index.html',
                entries=reversed(entries_stack),
                username=session.get("username"),
                show_welcome=session.pop("show_welcome", False)
            )

        @app.route('/new', methods=['GET', 'POST'])
        def new_entry():
            """
            Create a new diary entry.
            """
            if "user_id" not in session:
                return redirect(url_for("login"))

            if request.method == 'POST':
                mood = request.form.get('mood', '').strip()
                content = request.form.get('content', '').strip()

                if not mood or not content:
                    return redirect(url_for('new_entry'))

                entry = {
                    "user_id": session["user_id"],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "mood": mood,
                    "content": content,
                }
                self.db.diary_users.insert_one(entry)
                flash('Yeay! Kamu berhasil curhat!', 'success')
                return redirect(url_for('index'))

            return render_template('new_entry.html')

        @app.route('/login', methods=['GET', 'POST'])
        def login():
            """
            User login route.
            """
            if "user_id" in session:
                return redirect(url_for('index'))

            if request.method == 'POST':
                email = request.form.get('email').strip()
                password = request.form.get('password').strip()
                user = self.db.users.find_one({"email": email})

                if user and check_password_hash(user["password"], password):
                    session["user_id"] = str(user["_id"])
                    session["username"] = user["username"]
                    session["show_welcome"] = True
                    flash(f'Selamat datang kembali, {user["username"]}!', 'success')
                    return redirect(url_for('index'))

                flash('Login gagal. Hayo apa yang salah.', 'danger')

            return render_template('login.html')

        @app.route('/register', methods=['GET', 'POST'])
        def register():
            """
            User registration route.
            """
            if "user_id" in session:
                return redirect(url_for('index'))

            if request.method == 'POST':
                username = request.form.get('username').strip()
                email = request.form.get('email').strip()
                password = request.form.get('password').strip()

                error = self.validate_registration_form(username, email, password)
                if error:
                    flash(error, 'danger')
                    return redirect(url_for('register'))

                user = self.db.users.find_one({"email": email})
                if user:
                    flash('Email ini sudah digunakan. Silakan gunakan email lain.', 'danger')
                else:
                    hashed_password = generate_password_hash(password)
                    self.db.users.insert_one({
                        "username": username,
                        "email": email,
                        "password": hashed_password,
                    })
                    flash('Akun berhasil dibuat! Silakan login.', 'success')
                    return redirect(url_for('login'))

            return render_template('register.html')

        @app.route('/logout')
        def logout():
            """
            User logout route.
            """
            session.clear()
            flash('Anda berhasil logout.', 'info')
            return redirect(url_for('login'))

    def run(self, debug=True):
        """
        Run the application.
        """
        self.app.run(debug=debug)

if __name__ == '__main__':
    diary_app = DiaryApp()
    diary_app.run()