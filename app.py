# app.py

# Import statements
from flask import Flask, render_template, redirect, url_for, request, session, flash
import psycopg2
import logging
import requests
import os
import json

# For self-hosted OpenObserve
OPENOBSERVE_USERNAME = os.environ.get("OPENOBSERVE_USERNAME")
OPENOBSERVE_PASSWORD = os.environ.get("OPENOBSERVE_PASSWORD")
OPENOBSERVE_URL = os.environ.get("OPENOBSERVE_URL")

# Custom logging handler to send logs to OpenObserve
class OpenObserveHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        payload = [{
            "level": record.levelname.lower(),
            "message": log_entry,
            "loggerName": record.name,
            "timestamp": record.created,
            "filename": record.filename,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }]
        try:
            response = requests.post(
                OPENOBSERVE_URL,
                json=payload,
                auth=(OPENOBSERVE_USERNAME, OPENOBSERVE_PASSWORD),
                timeout=5
            )
            print("OpenObserve ingest response:", response.status_code, response.text)
        except requests.exceptions.RequestException as e:
            print("OpenObserve ingest failed:", e)
            pass

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Attach logging handler
openobserve_handler = OpenObserveHandler()
openobserve_handler.setLevel(logging.DEBUG)

# Format for logs
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
openobserve_handler.setFormatter(formatter)

logging.getLogger().addHandler(openobserve_handler)
logging.basicConfig(level=logging.DEBUG)

def get_db_connection():
    return psycopg2.connect("postgresql://user:password@db:5432/activity_tracker_db")

@app.route('/')
def home():
    return render_template('home.html')

def create_new_user(username, password):
    conn = get_db_connection()
    app.logger.debug("Create new user: Connected to Database")
    cur = conn.cursor()
    cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
    conn.commit()
    app.logger.debug("Created new user: %s", username)
    cur.close()
    conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username = %s", (username,))
        user_record = cur.fetchone()
        cur.close()
        conn.close()

        if user_record and user_record[0] == password:
            session['username'] = username
            flash('Login successful!', 'success')
            app.logger.info(f"User '{username}' logged in successfully.")
            return redirect(url_for('dashboard'))
        else:
            app.logger.warning(f"Failed login attempt for username '{username}'.")
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE username = %s", (username,))
        user_exists = cur.fetchone()

        if user_exists:
            flash('Username already exists. Please choose a different one.', 'danger')
        else:
            create_new_user(username, password)
            app.logger.info(f"New user registered: {username}")
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

        cur.close()
        conn.close()
    return render_template('register.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']

    if request.method == 'POST':
        try:
            step_count = int(request.form['step_count'])
            if step_count <= 0 or step_count > 100000:
                flash('Step count must be a positive number and less than 100,000.', 'danger')
            else:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO steps (username, step_count, recorded_at) VALUES (%s, %s, CURRENT_TIMESTAMP)",
                    (username, step_count),
                )
                conn.commit()
                cur.close()
                conn.close()
                flash('Step count added successfully!', 'success')
                app.logger.info(f"User '{username}' added {step_count} steps.")
        except ValueError:
            flash('Invalid input. Please enter a valid number.', 'danger')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT step_count, recorded_at FROM steps WHERE username = %s ORDER BY recorded_at ASC",
        (username,),
    )
    step_data = cur.fetchall()
    cur.close()
    conn.close()

    user_steps = [row[0] for row in step_data]
    timestamps = [row[1].strftime('%Y-%m-%d %H:%M:%S') for row in step_data]

    return render_template('dashboard.html', user_steps=user_steps, timestamps=timestamps)

@app.route('/logout')
def logout():
    user = session.get('username', 'Unknown')
    session.pop('username', None)
    flash('Logged out successfully.', 'info')
    app.logger.info(f"User '{user}' has logged out.")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)