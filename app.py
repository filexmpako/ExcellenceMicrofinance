from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime
import hashlib
import os

app = Flask(__name__)
app.secret_key = 'x7k9p3m2q8w4z6'  # Keep secret in env variable for production

# Absolute path to database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "microfinance.db")

# Ensure database folder exists
os.makedirs(os.path.join(BASE_DIR, "database"), exist_ok=True)

# Helper: get DB connection
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize / migrate DB
def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT UNIQUE,
            collateral TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            amount REAL,
            date TEXT,
            duration INTEGER,
            status TEXT,
            loan_type TEXT,
            interest_rate REAL,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )''')
        # Default admin
        c.execute("INSERT OR IGNORE INTO employees (username, password) VALUES (?, ?)",
                  ('admin', hashlib.sha256('admin123'.encode()).hexdigest()))
        conn.commit()

# Login required decorator
def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.template_filter('format_currency')
def format_currency(value):
    return f"TZS {value:,.2f}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM employees WHERE username = ? AND password = ?', 
                      (username, password))
            user = c.fetchone()
            if user:
                session['user_id'] = user['id']
                flash('Login successful', 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM customers')
        total_customers = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM loans WHERE status = "unpaid"')
        active_loans = c.fetchone()[0]
        c.execute('SELECT SUM(amount * (1 + COALESCE(interest_rate, 0) / 100)) FROM loans WHERE status = "unpaid"')
        total_outstanding = c.fetchone()[0] or 0
    return render_template('dashboard.html',
                           total_customers=total_customers,
                           active_loans=active_loans,
                           total_outstanding=total_outstanding)

@app.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        collateral = request.form['collateral']
        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute('INSERT INTO customers (name, phone, collateral) VALUES (?, ?, ?)',
                          (name, phone, collateral))
                conn.commit()
                flash('Customer added successfully', 'success')
        except sqlite3.IntegrityError:
            flash('Phone number already exists', 'error')
        return redirect(url_for('customers'))
    
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name, phone, COALESCE(collateral, "N/A") FROM customers')
        customers = c.fetchall()
    return render_template('customers.html', customers=customers)

@app.route('/loans', methods=['GET', 'POST'])
@login_required
def loans():
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        amount = float(request.form['amount'])
        duration = int(request.form['duration'])
        loan_type = request.form['loan_type']
        interest_rate = float(request.form['interest_rate'])
        date = datetime.now().strftime('%Y-%m-%d')

        if amount <= 0 or duration <= 0 or interest_rate < 0:
            flash('Amount and duration must be positive, and interest rate cannot be negative.', 'error')
            return redirect(url_for('loans'))

        with get_connection() as conn:
            c = conn.cursor()
            c.execute('INSERT INTO loans (customer_id, amount, date, duration, status, loan_type, interest_rate) VALUES (?, ?, ?, ?, ?, ?, ?)',
                      (customer_id, amount, date, duration, 'unpaid', loan_type, interest_rate))
            conn.commit()

        flash('Loan recorded successfully', 'success')
        return redirect(url_for('loans'))

    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT l.id, c.name, l.amount, l.date, l.duration, l.status, COALESCE(l.loan_type, "N/A"), COALESCE(l.interest_rate, 0), COALESCE(c.collateral, "N/A") FROM loans l JOIN customers c ON l.customer_id = c.id')
        loans = c.fetchall()
        c.execute('SELECT id, name FROM customers')
        customers = c.fetchall()
    return render_template('loans.html', loans=loans, customers=customers)

@app.route('/loans/repay/<int:loan_id>')
@login_required
def repay_loan(loan_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('UPDATE loans SET status = "paid" WHERE id = ?', (loan_id,))
        conn.commit()
    flash('Loan marked as paid', 'success')
    return redirect(url_for('loans'))

@app.route('/reports')
@login_required
def reports():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT c.name, l.amount, l.date, l.duration, l.status, COALESCE(l.loan_type, "N/A"), COALESCE(l.interest_rate, 0), COALESCE(c.collateral, "N/A") FROM loans l JOIN customers c ON l.customer_id = c.id WHERE l.status = "paid"')
        paid_loans = c.fetchall()
        c.execute('SELECT c.name, l.amount, l.date, l.duration, l.status, COALESCE(l.loan_type, "N/A"), COALESCE(l.interest_rate, 0), COALESCE(c.collateral, "N/A") FROM loans l JOIN customers c ON l.customer_id = c.id WHERE l.status = "unpaid"')
        unpaid_loans = c.fetchall()
    return render_template('reports.html', paid_loans=paid_loans, unpaid_loans=unpaid_loans)

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# Run DB init at startup (works with Gunicorn)
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
