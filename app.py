# app.py

# Import statements
from flask import Flask, render_template, redirect, url_for, request, session, flash  # type: ignore
import psycopg2
import logging

# For Cloud.OpenObserve
import requests  
import os        
import json


# Read OpenObserve credentials from Docker environment variables (or use defaults) //TODOO
OPENOBSERVE_USERNAME = os.environ.get("OPENOBSERVE_USERNAME", "my_username_here")  
OPENOBSERVE_PASSWORD = os.environ.get("OPENOBSERVE_PASSWORD", "my_password_here")
OPENOBSERVE_URL = os.environ.get(
    "OPENOBSERVE_URL",
    "https://api.openobserve.ai/api/<YOUR_ORG>/<YOUR_PROJECT>/default/_json" 
)

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
            requests.post(
                OPENOBSERVE_URL,
                json=payload,
                auth=(OPENOBSERVE_USERNAME, OPENOBSERVE_PASSWORD),  # Basic auth
                timeout=5
            )
        except requests.exceptions.RequestException:
            # Don't interrupt the main flow if logging fails
            pass

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Attach logging handler
openobserve_handler = OpenObserveHandler() 
openobserve_handler.setLevel(logging.DEBUG) # OpenObserve

# Format for the logs sent to OpenObserve
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')  # OpenObserve
openobserve_handler.setFormatter(formatter)  # OpenObserve

logging.getLogger().addHandler(openobserve_handler)  # OpenObserve
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
            app.logger.info(f"User '{username}' logged in successfully.")  # OpenObserve
            return redirect(url_for('dashboard'))
        else:
            app.logger.warning(f"Failed login attempt for username '{username}'.")  # OpenObserve
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
            app.logger.info(f"New user registered: {username}")  # OpenObserve
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

    # Handle form submission to add steps
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
                app.logger.info(f"User '{username}' added {step_count} steps.")  # OpenObserve
        except ValueError:
            flash('Invalid input. Please enter a valid number.', 'danger')

    # Fetch step data for the logged-in user
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT step_count, recorded_at FROM steps WHERE username = %s ORDER BY recorded_at ASC",
        (username,),
    )
    step_data = cur.fetchall()
    cur.close()
    conn.close()

    # Prepare data for the chart
    user_steps = [row[0] for row in step_data]  # Step counts
    timestamps = [row[1].strftime('%Y-%m-%d %H:%M:%S') for row in step_data]  # Timestamps

    return render_template('dashboard.html', user_steps=user_steps, timestamps=timestamps)

@app.route('/logout')
def logout():
    user = session.get('username', 'Unknown')  # OpenObserve
    session.pop('username', None)
    flash('Logged out successfully.', 'info')
    app.logger.info(f"User '{user}' has logged out.")  # OpenObserve
    return redirect(url_for('home'))

# Run the App
if __name__ == '__main__':
    app.run(debug=True)
