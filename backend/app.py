import os
import re

import psycopg2
from psycopg2.extras import RealDictCursor

from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    jsonify
)

from dotenv import load_dotenv
# Load .env before importing other application modules
BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

load_dotenv(
    os.path.join(BASE_DIR, ".env")
)
from docx import Document
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from flask_mail import Mail, Message

from itsdangerous import (
    URLSafeTimedSerializer,
    BadSignature,
    SignatureExpired
)

from .aichatbox import chat_with_ai


# =========================================================
# CONFIGURATION
# =========================================================

FRONTEND_DIR = os.path.normpath(
    os.path.join(
        BASE_DIR,
        "..",
        "frontend"
    )
)

app = Flask(
    __name__,
    template_folder=os.path.join(
        FRONTEND_DIR,
        "templates"
    ),
    static_folder=os.path.join(
        FRONTEND_DIR,
        "static"
    )
)


# =========================================================
# FLASK SECRET KEY
# =========================================================

app.secret_key = os.environ.get(
    "SECRET_KEY"
)

if not app.secret_key:
    raise RuntimeError(
        "SECRET_KEY is missing. Add it to backend/.env"
    )


# =========================================================
# UPLOAD CONFIGURATION
# =========================================================

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# =========================================================
# SUPABASE POSTGRESQL CONFIGURATION
# =========================================================

DATABASE_URL = os.environ.get(
    "DATABASE_URL"
)

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Add your Supabase connection string to .env"
    )


def get_db_connection():
    """
    Connect to Supabase PostgreSQL database.
    """

    connection = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )

    return connection


# =========================================================
# MAILJET CONFIGURATION
# =========================================================

app.config["MAIL_SERVER"] = os.environ.get(
    "MAIL_SERVER",
    "in-v3.mailjet.com"
)

app.config["MAIL_PORT"] = int(
    os.environ.get(
        "MAIL_PORT",
        587
    )
)

app.config["MAIL_USE_TLS"] = (
    os.environ.get(
        "MAIL_USE_TLS",
        "True"
    ).lower() == "true"
)

app.config["MAIL_USE_SSL"] = (
    os.environ.get(
        "MAIL_USE_SSL",
        "False"
    ).lower() == "true"
)

app.config["MAIL_USERNAME"] = os.environ.get(
    "MAIL_USERNAME"
)

app.config["MAIL_PASSWORD"] = os.environ.get(
    "MAIL_PASSWORD"
)

app.config["MAIL_DEFAULT_SENDER"] = os.environ.get(
    "MAIL_DEFAULT_SENDER"
)

if not app.config["MAIL_USERNAME"]:
    raise RuntimeError(
        "MAIL_USERNAME is missing in backend/.env"
    )

if not app.config["MAIL_PASSWORD"]:
    raise RuntimeError(
        "MAIL_PASSWORD is missing in backend/.env"
    )

if not app.config["MAIL_DEFAULT_SENDER"]:
    raise RuntimeError(
        "MAIL_DEFAULT_SENDER is missing in backend/.env"
    )


mail = Mail(app)

serializer = URLSafeTimedSerializer(
    app.secret_key
)


# =========================================================
# DATABASE TEST
# =========================================================

def test_database_connection():
    """
    Test Supabase connection.
    """

    connection = None

    try:
        connection = get_db_connection()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT NOW() AS current_time"
        )

        result = cursor.fetchone()

        print(
            "Supabase connected successfully:",
            result["current_time"]
        )

    except Exception as error:
        print(
            "Supabase connection error:",
            type(error).__name__,
            str(error)
        )

    finally:
        if connection:
            connection.close()


# =========================================================
# RESUME KEYWORDS
# =========================================================

KEYWORDS = [
    "python",
    "java",
    "c",
    "c++",
    "sql",
    "mysql",
    "postgresql",
    "html",
    "css",
    "javascript",
    "react",
    "node",
    "flask",
    "django",
    "api",
    "rest",
    "json",
    "git",
    "github",
    "linux",
    "docker",
    "aws",
    "azure",
    "machine learning",
    "data analysis",
    "pandas",
    "numpy",
    "problem solving",
    "communication",
    "teamwork"
]


# =========================================================
# TEXT EXTRACTION
# =========================================================

def extract_text(file_path):
    """
    Extract text from TXT, PDF and DOCX files.
    """

    text = ""

    try:

        if file_path.lower().endswith(".txt"):

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                text = file.read()

        elif file_path.lower().endswith(".pdf"):

            reader = PdfReader(
                file_path
            )

            pages = []

            for page in reader.pages:

                page_text = page.extract_text()

                if page_text:
                    pages.append(page_text)

            text = "\n".join(
                pages
            )

        elif file_path.lower().endswith(".docx"):

            document = Document(
                file_path
            )

            text = "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text
            )

    except Exception as error:

        print(
            "Text extraction error:",
            type(error).__name__,
            str(error)
        )

    lines = [
        re.sub(
            r"[ \t]+",
            " ",
            line
        ).strip()
        for line in text.splitlines()
    ]

    text = "\n".join(
        line
        for line in lines
        if line
    )

    return text.lower()


# =========================================================
# RESUME RANKING LOGIC
# =========================================================

def rank_resume(text):

    if not text:
        return 0.0, 0, 0, 0

    text = text.lower()

    # -----------------------------------------------------
    # Keyword score
    # -----------------------------------------------------

    found_keywords = sum(
        1
        for keyword in KEYWORDS
        if keyword in text
    )

    keyword_score = min(
        found_keywords * 2,
        75
    )

    # -----------------------------------------------------
    # Experience detection
    # -----------------------------------------------------

    experience_years = 0.0

    experience_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:years|yrs|yr)",
        text
    )

    if experience_match:

        experience_years = float(
            experience_match.group(1)
        )

    if experience_years == 0.0:

        year_match = re.search(
            r"\b(19|20)\d{2}\b.{0,40}?\b(19|20)\d{2}\b",
            text
        )

        if year_match:

            years = re.findall(
                r"\b(?:19|20)\d{2}\b",
                year_match.group(0)
            )

            if len(years) >= 2:

                first_year = int(
                    years[0]
                )

                second_year = int(
                    years[1]
                )

                if second_year >= first_year:

                    experience_years = float(
                        second_year - first_year
                    )

    experience_score = min(
        int(experience_years) * 2,
        15
    )

    returned_experience_years = (
        experience_score // 2
    )

    # -----------------------------------------------------
    # Project count
    # -----------------------------------------------------

    project_words = len(
        re.findall(
            r"\bproject\b",
            text
        )
    )

    bullets = text.count("•")

    hyphen_bullets = len(
        re.findall(
            r"(?m)^\s*-\s+\S+",
            text
        )
    )

    project_count = (
        project_words
        + bullets
        + hyphen_bullets
    )

    project_score = min(
        project_count * 2,
        10
    )

    # -----------------------------------------------------
    # Total score
    # -----------------------------------------------------

    total_score = round(
        min(
            keyword_score
            + experience_score
            + project_score,
            100
        ),
        2
    )

    return (
        total_score,
        returned_experience_years,
        project_count,
        found_keywords
    )


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_logged_in_user():
    """
    Get current logged-in user from Supabase.
    """

    username = session.get(
        "user"
    )

    if not username:
        return None

    connection = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, username, email, role
            FROM users
            WHERE username = %s
            LIMIT 1
            """,
            (
                username,
            )
        )

        user = cursor.fetchone()

        return user

    except Exception as error:

        print(
            "User lookup error:",
            type(error).__name__,
            str(error)
        )

        return None

    finally:

        if connection:
            connection.close()


def get_user_id():
    """
    Return logged-in user's database ID.
    """

    user = get_logged_in_user()

    if user:
        return user["id"]

    return None


# =========================================================
# HOME ROUTE
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# RESUME RANKING ROUTE
# =========================================================

@app.route(
    "/rank",
    methods=["GET", "POST"]
)
def rank():

    if "user" not in session:

        session["next_page"] = url_for(
            "rank"
        )

        flash(
            "Please log in first to rank your resumes.",
            "warning"
        )

        return redirect(
            url_for("login")
        )

    if (
        request.method == "POST"
        and "resumes" in request.files
    ):

        uploaded_files = request.files.getlist(
            "resumes"
        )

        results = []

        user_id = get_user_id()

        if not user_id:

            flash(
                "Unable to identify your account. Please login again.",
                "danger"
            )

            return redirect(
                url_for("login")
            )

        for file in uploaded_files:

            if not file or not file.filename:
                continue

            filename = secure_filename(
                file.filename
            )

            if not filename:
                continue

            file_path = os.path.join(
                UPLOAD_DIR,
                filename
            )

            file.save(
                file_path
            )

            extracted_text = extract_text(
                file_path
            )

            score, experience, projects, hits = (
                rank_resume(
                    extracted_text
                )
            )

            connection = None

            try:

                connection = get_db_connection()

                cursor = connection.cursor()

                # -------------------------------------------------
                # Save uploaded resume
                # -------------------------------------------------

                cursor.execute(
                    """
                    INSERT INTO resumes
                    (
                        user_id,
                        filename,
                        file_path,
                        extracted_text
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        filename,
                        file_path,
                        extracted_text
                    )
                )

                resume_record = cursor.fetchone()

                resume_id = resume_record["id"]

                # -------------------------------------------------
                # Save ranking result
                # -------------------------------------------------

                cursor.execute(
                    """
                    INSERT INTO ranking_results
                    (
                        user_id,
                        resume_id,
                        score,
                        experience,
                        projects,
                        keyword_hits
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        resume_id,
                        score,
                        experience,
                        projects,
                        hits
                    )
                )

                connection.commit()

                results.append(
                    (
                        filename,
                        score,
                        experience,
                        projects,
                        hits
                    )
                )

            except Exception as error:

                if connection:
                    connection.rollback()

                print(
                    "Resume database error:",
                    type(error).__name__,
                    str(error)
                )

                flash(
                    "Could not save resume details to database.",
                    "danger"
                )

            finally:

                if connection:
                    connection.close()

        results.sort(
            key=lambda item: item[1],
            reverse=True
        )

        return render_template(
            "result.html",
            results=results
        )

    return render_template(
        "index.html"
    )


# =========================================================
# LOGIN ROUTE
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        connection = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT id, username, email, password, role
                FROM users
                WHERE username = %s
                LIMIT 1
                """,
                (
                    username,
                )
            )

            user = cursor.fetchone()

        except Exception as error:

            print(
                "Login database error:",
                type(error).__name__,
                str(error)
            )

            user = None

            flash(
                "Database connection error. Please try again.",
                "danger"
            )

        finally:

            if connection:
                connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user"] = user["username"]

            session["user_id"] = user["id"]

            session["role"] = user["role"]

            flash(
                "Logged in successfully!",
                "success"
            )

            next_page = session.pop(
                "next_page",
                url_for("home")
            )

            return redirect(
                next_page
            )

        flash(
            "Incorrect username or password.",
            "login_error"
        )

    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT ROUTE
# =========================================================

@app.route(
    "/logout"
)
def logout():

    session.pop(
        "user",
        None
    )

    session.pop(
        "user_id",
        None
    )

    session.pop(
        "role",
        None
    )

    flash(
        "Logged out successfully.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# SIGNUP ROUTE
# =========================================================

@app.route(
    "/signup",
    methods=["GET", "POST"]
)
def signup():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        # Users cannot create admin accounts
        role = "user"

        # -----------------------------------------------------
        # Required field validation
        # -----------------------------------------------------

        if not username or not email or not password:

            flash(
                "Please fill all required fields.",
                "warning"
            )

            return redirect(
                url_for("signup")
            )

        # -----------------------------------------------------
        # Email validation
        # -----------------------------------------------------

        email_pattern = (
            r"^[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\."
            r"[A-Za-z]{2,}$"
        )

        if not re.match(
            email_pattern,
            email
        ):

            flash(
                "Please enter a valid email address.",
                "warning"
            )

            return redirect(
                url_for("signup")
            )

        # -----------------------------------------------------
        # Strong password validation
        # -----------------------------------------------------

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "warning"
            )

            return redirect(
                url_for("signup")
            )

        if not re.search(
            r"[A-Z]",
            password
        ):

            flash(
                "Password must contain at least one uppercase letter.",
                "warning"
            )

            return redirect(
                url_for("signup")
            )

        if not re.search(
            r"[a-z]",
            password
        ):

            flash(
                "Password must contain at least one lowercase letter.",
                "warning"
            )

            return redirect(
                url_for("signup")
            )

        if not re.search(
            r"\d",
            password
        ):

            flash(
                "Password must contain at least one number.",
                "warning"
            )

            return redirect(
                url_for("signup")
            )

        if not re.search(
            r"""[!@#$%^&*(),.?":{}|<>_\-+=/\\[\]]""",
            password
        ):

            flash(
                "Password must contain at least one special character.",
                "warning"
            )

            return redirect(
                url_for("signup")
            )

        connection = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor()

            # -------------------------------------------------
            # Check duplicate username or email
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE username = %s
                   OR email = %s
                LIMIT 1
                """,
                (
                    username,
                    email
                )
            )

            existing_user = cursor.fetchone()

            if existing_user:

                flash(
                    "Username or email already exists.",
                    "warning"
                )

                return redirect(
                    url_for("signup")
                )

            hashed_password = generate_password_hash(
                password
            )

            # -------------------------------------------------
            # Insert user into Supabase
            # -------------------------------------------------

            cursor.execute(
                """
                INSERT INTO users
                (
                    username,
                    email,
                    password,
                    role
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    username,
                    email,
                    hashed_password,
                    role
                )
            )

            connection.commit()

            flash(
                "Account created successfully. Please login.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except psycopg2.errors.UniqueViolation:

            if connection:
                connection.rollback()

            flash(
                "Username or email already exists.",
                "warning"
            )

            return redirect(
                url_for("signup")
            )

        except Exception as error:

            if connection:
                connection.rollback()

            print(
                "Signup database error:",
                type(error).__name__,
                str(error)
            )

            flash(
                "Unable to create account. Please try again.",
                "danger"
            )

            return redirect(
                url_for("signup")
            )

        finally:

            if connection:
                connection.close()

    return render_template(
        "signup.html"
    )


# =========================================================
# FORGOT PASSWORD ROUTE
# =========================================================

@app.route(
    "/forgot-password",
    methods=["POST"]
)
def forgot_password():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        email = data.get(
            "email",
            ""
        ).strip().lower()

        if not email:

            return jsonify({
                "error": "Please enter your email address."
            }), 400

        connection = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT username, email
                FROM users
                WHERE email = %s
                LIMIT 1
                """,
                (
                    email,
                )
            )

            user = cursor.fetchone()

        finally:

            if connection:
                connection.close()

        success_message = (
            "If this email is registered, "
            "a password reset link has been sent."
        )

        # Generic response for security
        if not user:

            print(
                "Email not registered:",
                email
            )

            return jsonify({
                "message": success_message
            }), 200

        # -----------------------------------------------------
        # Generate reset token
        # -----------------------------------------------------

        token = serializer.dumps(
            email,
            salt="password-reset"
        )

        reset_link = url_for(
            "reset_password",
            token=token,
            _external=True
        )

        # -----------------------------------------------------
        # Create email
        # -----------------------------------------------------

        message = Message(
            subject="ResumeRanker - Password Reset",
            recipients=[
                email
            ],
            sender=app.config[
                "MAIL_DEFAULT_SENDER"
            ]
        )

        message.body = f"""
Hello {user["username"]},

You requested to reset your ResumeRanker password.

Click the link below to set a new password:

{reset_link}

This link will expire in 30 minutes.

If you did not request this password reset,
you can safely ignore this email.

Regards,
ResumeRanker Team
"""

        mail.send(
            message
        )

        print(
            "Password reset email sent successfully!"
        )

        print(
            "Recipient:",
            email
        )

        return jsonify({
            "message": success_message
        }), 200

    except Exception as error:

        print(
            "Forgot password email error:",
            type(error).__name__,
            str(error)
        )

        return jsonify({
            "error": (
                "Unable to send reset email. "
                "Please check your Mailjet settings."
            )
        }), 500


# =========================================================
# RESET PASSWORD ROUTE
# =========================================================

@app.route(
    "/reset-password/<token>",
    methods=["GET", "POST"]
)
def reset_password(token):

    try:

        email = serializer.loads(
            token,
            salt="password-reset",
            max_age=1800
        )

    except SignatureExpired:

        flash(
            "This password reset link has expired.",
            "danger"
        )

        return redirect(
            url_for("login")
        )

    except BadSignature:

        flash(
            "Invalid password reset link.",
            "danger"
        )

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        new_password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # Use same strong password rules
        if len(new_password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "warning"
            )

            return redirect(
                url_for(
                    "reset_password",
                    token=token
                )
            )

        if not re.search(
            r"[A-Z]",
            new_password
        ):

            flash(
                "Password must contain at least one uppercase letter.",
                "warning"
            )

            return redirect(
                url_for(
                    "reset_password",
                    token=token
                )
            )

        if not re.search(
            r"[a-z]",
            new_password
        ):

            flash(
                "Password must contain at least one lowercase letter.",
                "warning"
            )

            return redirect(
                url_for(
                    "reset_password",
                    token=token
                )
            )

        if not re.search(
            r"\d",
            new_password
        ):

            flash(
                "Password must contain at least one number.",
                "warning"
            )

            return redirect(
                url_for(
                    "reset_password",
                    token=token
                )
            )

        if not re.search(
            r"""[!@#$%^&*(),.?":{}|<>_\-+=/\\[\]]""",
            new_password
        ):

            flash(
                "Password must contain at least one special character.",
                "warning"
            )

            return redirect(
                url_for(
                    "reset_password",
                    token=token
                )
            )

        if new_password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(
                url_for(
                    "reset_password",
                    token=token
                )
            )

        hashed_password = generate_password_hash(
            new_password
        )

        connection = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor()

            cursor.execute(
                """
                UPDATE users
                SET password = %s
                WHERE email = %s
                """,
                (
                    hashed_password,
                    email
                )
            )

            connection.commit()

            flash(
                "Password reset successful. Please login.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except Exception as error:

            if connection:
                connection.rollback()

            print(
                "Password reset database error:",
                type(error).__name__,
                str(error)
            )

            flash(
                "Unable to reset password. Please try again.",
                "danger"
            )

        finally:

            if connection:
                connection.close()

    return render_template(
        "reset_password.html",
        token=token
    )


# =========================================================
# ABOUT PAGE
# =========================================================

@app.route(
    "/about"
)
def about():

    return render_template(
        "about.html"
    )


# =========================================================
# CONTACT PAGE
# =========================================================

@app.route(
    "/contact",
    methods=["GET", "POST"]
)
def contact():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        flash(
            f"Thank you {name}, your message has been submitted successfully!",
            "success"
        )

    return render_template(
        "contact.html"
    )


# =========================================================
# LEARN PAGE
# =========================================================

@app.route(
    "/learn"
)
def learn():

    return render_template(
        "learn.html"
    )


# =========================================================
# AI CHAT PAGE
# =========================================================

@app.route(
    "/aichat"
)
def aichat():

    return render_template(
        "aichat.html"
    )


# =========================================================
# AI CHAT API
# =========================================================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        user_message = data.get(
            "message",
            ""
        ).strip()

        if not user_message:

            return jsonify({
                "error": "Please enter a message."
            }), 400

        ai_response = chat_with_ai(
            user_message
        )

        # -------------------------------------------------
        # Save chat history to Supabase
        # -------------------------------------------------

        user_id = get_user_id()

        if user_id:

            connection = None

            try:

                connection = get_db_connection()

                cursor = connection.cursor()

                cursor.execute(
                    """
                    INSERT INTO chat_messages
                    (
                        user_id,
                        message,
                        response
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        user_id,
                        user_message,
                        ai_response
                    )
                )

                connection.commit()

            except Exception as database_error:

                if connection:
                    connection.rollback()

                print(
                    "Chat history save error:",
                    type(database_error).__name__,
                    str(database_error)
                )

            finally:

                if connection:
                    connection.close()

        return jsonify({
            "response": ai_response
        })

    except Exception as error:

        print(
            "Chat error:",
            type(error).__name__,
            str(error)
        )

        return jsonify({
            "error": (
                "AI service is temporarily unavailable."
            )
        }), 500


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    test_database_connection()

    app.run(
        debug=True
    )