import os
import re
from flask import Flask, request, render_template, redirect, url_for, flash, session
from docx import Document
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename

# --- CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "frontend"))

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static")
)
app.secret_key = "supersecretkey"

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- TEMPORARY USER STORE ---
USERS = {"admin": "123"}

# --- KEYWORDS FOR RESUME RANKING ---
KEYWORDS = [
    "python", "java", "c", "c++", "sql", "mysql", "postgresql",
    "html", "css", "javascript", "react", "node",
    "flask", "django",
    "api", "rest", "json",
    "git", "github",
    "linux", "docker",
    "aws", "azure",
    "machine learning", "data analysis", "pandas", "numpy",
    "problem solving", "communication", "teamwork"
]

def extract_text(file_path):
    """
    Extract text from .txt, .pdf, .docx
    Keeps newlines for project/bullet detection
    """
    text = ""
    try:
        if file_path.lower().endswith(".txt"):
            with open(file_path, "r", errors="ignore") as f:
                text = f.read()

        elif file_path.lower().endswith(".pdf"):
            reader = PdfReader(file_path)
            pages = []
            for page in reader.pages:
                p = page.extract_text()
                if p:
                    pages.append(p)
            text = "\n".join(pages)

        elif file_path.lower().endswith(".docx"):
            doc = Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs if p.text)

    except Exception:
        pass

    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    text = "\n".join(ln for ln in lines if ln)
    return text.lower()

# --- RANKING LOGIC ---
def rank_resume(text):
    if not text:
        return 0.0, 0, 0, 0

    t = text.lower()

    # --- KEYWORD SCORE ---
    found_keywords = sum(1 for kw in KEYWORDS if kw in t)
    keyword_score = min(found_keywords * 2, 75)

    # --- EXPERIENCE DETECTION ---
    exp_years = 0.0

    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:years|yrs|yr)', t)
    if m:
        exp_years = float(m.group(1))

    if exp_years == 0.0:
        m2 = re.search(r'(\b(19|20)\d{2}\b).{0,40}?(\b(19|20)\d{2}\b)', t)
        if m2:
            y1 = int(m2.group(1))
            y2 = int(m2.group(3))
            if y2 >= y1:
                exp_years = float(y2 - y1)

    exp_score = min(int(exp_years) * 2, 15)
    returned_exp_years = exp_score // 2

    # --- PROJECT COUNT ---
    proj_words = len(re.findall(r'\bproject\b', t))
    bullets = t.count("•")
    hyphen_bullets = len(re.findall(r'(?m)^\s*-\s+\S+', t))

    proj_count = proj_words + bullets + hyphen_bullets
    proj_score = min(proj_count * 2, 10)

    # --- TOTAL SCORE ---
    total_score = round(min(keyword_score + exp_score + proj_score, 100), 2)

    return total_score, returned_exp_years, proj_count, found_keywords

# --- ROUTES ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/rank", methods=["GET", "POST"])
def rank():
    if "user" not in session:
        session["next_page"] = url_for("rank")
        flash("⚠ Please log in first to rank your resumes.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST" and "resumes" in request.files:
        files = request.files.getlist("resumes")
        results = []

        for file in files:
            filename = secure_filename(file.filename)
            path = os.path.join(UPLOAD_DIR, filename)
            file.save(path)

            text = extract_text(path)
            score, exp, proj, hits = rank_resume(text)

            results.append((filename, score, exp, proj, hits))

        results.sort(key=lambda x: x[1], reverse=True)
        return render_template("result.html", results=results)

    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username in USERS and USERS[username] == password:
            session["user"] = username
            flash("✅ Logged in successfully!", "success")
            return redirect(session.pop("next_page", url_for("home")))
        else:
            flash("Incorrect username or password", "login_error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("✅ Logged out successfully.", "success")
    return redirect(url_for("home"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        if not username or not password or not role:
            flash("⚠ Please fill all fields!", "warning")
            return redirect(url_for("signup"))

        if username in USERS:
            flash("⚠ Username already exists!", "warning")
            return redirect(url_for("signup"))

        USERS[username] = password
        flash(f"✅ Account created successfully for {username}!", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        flash(f"Thank you {name}, your message has been submitted successfully!", "success")
    return render_template("contact.html")

@app.route("/learn")
def learn():
    return render_template("learn.html")

# --- RUN APP ---
if __name__ == "__main__":
    app.run(debug=True)
