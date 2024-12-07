# app.py
from flask import Flask, render_template, redirect, url_for, request, session, flash # type: ignore
import psycopg2
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Temporary in-memory storage
users = {}  # Stores users as {username: password_hash}
steps = {}  # Stores steps as {username: [list_of_step_entries]}
logging.basicConfig(level=logging.DEBUG)

# Routes
@app.route('/')
def home():
    #if 'username' in session:
    #    return redirect(url_for('dashboard'))
    connectDatabase()
    return render_template('home.html')

def connectDatabase():
    conn = psycopg2.connect("postgresql://user:password@db:5432/activity_tracker_db")
    app.logger.debug("Connected to Database")

    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    records = cur.fetchall()

    app.logger.debug("Got records: " + str(records))

    cur.close()
    conn.close()
    for record in records:
        users[record.index] = record.count
        steps[record.index] = []
    return

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash('Username already exists. Please choose a different one.', 'danger')
        else:
            users[username] = password
            steps[username] = []
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    if request.method == 'POST':
        step_count = request.form['step_count']
        steps[username].append(step_count)
        flash('Step count added successfully!', 'success')

    user_steps = steps[username]
    return render_template('dashboard.html', user_steps=user_steps)

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

# Run the App
if __name__ == '__main__':
    app.run(debug=True)

