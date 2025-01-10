from flask import Flask, render_template, redirect, url_for, request, session, flash  # type: ignore
import psycopg2
from psycopg2.pool import SimpleConnectionPool
import logging
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "a_default_secret_key_for_managing_sessions")

logging.basicConfig(level=logging.DEBUG)

def initialize_connection_pool() -> SimpleConnectionPool :
    global connection_pool
    postgres_user = os.getenv("POSTGRES_USER")
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    postgres_host = os.getenv("POSTGRES_HOST", "db")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_name = os.getenv("POSTGRES_DBNAME")

    return SimpleConnectionPool(
        1,
        10,
        user=postgres_user,
        password=postgres_password,
        host=postgres_host,
        port=postgres_port,
        database=postgres_name
    )

connection_pool = initialize_connection_pool()

@app.route('/')
def home():
    return render_template('home.html')

def create_new_user(username, password):
    conn = connection_pool.getconn()
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

        conn = connection_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username = %s", (username,))
        user_record = cur.fetchone()
        cur.close()
        conn.close()

        if user_record and user_record[0] == password:
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

        conn = connection_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE username = %s", (username,))
        user_exists = cur.fetchone()

        if user_exists:
            flash('Username already exists. Please choose a different one.', 'danger')
        else:
            create_new_user(username, password)
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
    conn = None

    try:
        # Handle form submission to add steps
        if request.method == 'POST':
            step_count = int(request.form.get('step_count', 0))
            if step_count <= 0 or step_count > 100000:  # Validate step count
                flash('Step count must be a positive number and less than 100,000.', 'danger')
            else:
                conn = connection_pool.getconn()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO steps (username, step_count, recorded_at) VALUES (%s, %s, CURRENT_TIMESTAMP)",
                    (username, step_count),
                )
                conn.commit()
                cur.close()
                flash('Step count added successfully!', 'success')

        # Fetch step data for the logged-in user
        if not conn:
            conn = connection_pool.getconn()

        cur = conn.cursor()
        cur.execute(
            "SELECT step_count, recorded_at FROM steps WHERE username = %s ORDER BY recorded_at ASC",
            (username,),
        )
        step_data = cur.fetchall()
        cur.close()

        # Prepare data for the chart
        user_steps = [row[0] for row in step_data]  # Step counts
        timestamps = [row[1].strftime('%Y-%m-%d %H:%M:%S') for row in step_data]  # Timestamps

        return render_template('dashboard.html', user_steps=user_steps, timestamps=timestamps)

    except ValueError:
        flash('Invalid input. Please enter a valid number.', 'danger')

    except Exception as e:
        app.logger.error(f"Error in dashboard: {e}")
        flash('An error occurred. Please try again later.', 'danger')

    finally:
        if conn:
            connection_pool.putconn(conn)


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

# Run the App
if __name__ == '__main__':
    app.run(debug=True)
