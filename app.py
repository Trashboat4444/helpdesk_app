from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from functools import wraps

app = Flask(__name__)
app.config.from_object(Config)

def get_db_connection():
    return pymysql.connect(
        host=app.config["DB_HOST"],
        user=app.config["DB_USER"],
        password=app.config["DB_PASSWORD"],
        database=app.config["DB_NAME"],
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route("/")
def index():
    # If user is logged in, redirect to dashboard
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

if __name__ == "__main__":
    app.run(debug=True)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password): 10
            # Store user info in session
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = user["role"]
        flash("Welcome, {}!".format(user["name"]), "success")
        return redirect(url_for("dashboard"))
    else:
            flash("Invalid email or password.", "danger")
    
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/tickets")
@login_required
def tickets_list():
    user_id = session["user_id"]
    user_role = session["user_role"]
    conn = get_db_connection()
    with conn.cursor() as cursor:
        if user_role == "ADMIN":
            cursor.execute("""
                SELECT t.*, u.name AS created_by_name, a.name AS assigned_to_name
                FROM tickets t
                JOIN users u ON t.created_by = u.id
                LEFT JOIN users a ON t.assigned_to = a.id
                ORDER BY t.created_at DESC
            """)
        elif user_role == "AGENT":
            cursor.execute("""
                SELECT t.*, u.name AS created_by_name, a.name AS assigned_to_name
                FROM tickets t
                JOIN users u ON t.created_by = u.id
                LEFT JOIN users a ON t.assigned_to = a.id
                WHERE t.assigned_to = %s OR t.assigned_to IS NULL
                ORDER BY t.created_at DESC
            """, (user_id,))
        else: # USER
            cursor.execute("""
                SELECT t.*, u.name AS created_by_name, a.name AS assigned_to_name
                FROM tickets t
                JOIN users u ON t.created_by = u.id
                LEFT JOIN users a ON t.assigned_to = a.id
                WHERE t.created_by = %s
                ORDER BY t.created_at DESC
            """, (user_id,))

        tickets = cursor.fetchall()
    conn.close()

    return render_template("tickets_list.html", tickets=tickets)

@app.route("/tickets/new", methods=["GET", "POST"])
@login_required
def ticket_new():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        priority = request.form.get("priority")
        created_by = session["user_id"]

        if not title or not description:
            flash("Title and description are required.", "warning")
            return redirect(url_for("ticket_new"))
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO tickets (title, description, priority, created_by)
                VALUES (%s, %s, %s, %s)
            """, (title, description, priority, created_by))
        conn.commit()
        conn.close()

        flash("Ticket created successfully.", "success")
        return redirect(url_for("tickets_list"))

    return render_template("ticket_new.html")