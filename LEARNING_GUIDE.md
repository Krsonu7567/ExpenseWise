# ExpenseWise — The Beginner's Full-Stack Learning & Interview Guide

> **Author Note for Students & Interviewees:**  
> This guide is specially designed for engineering students and beginners who know basic Python and want to master full-stack web development. Every concept is explained simply, without unnecessary jargon, so you can confidently showcase and explain ExpenseWise in HR and technical job interviews.

---

## 📚 Table of Contents

1. [Understanding the Big Picture: Frontend vs. Backend](#1-understanding-the-big-picture-frontend-vs-backend)
2. [What is Flask and How Does It Work?](#2-what-is-flask-and-how-does-it-work)
3. [Understanding Routes and HTTP Methods (GET vs. POST)](#3-understanding-routes-and-http-methods-get-vs-post)
4. [How HTML Forms Send Data Over the Internet](#4-how-html-forms-send-data-over-the-internet)
5. [What is SQLite and How Does Python Connect to It?](#5-what-is-sqlite-and-how-does-python-connect-to-it)
6. [Why We Store Money in Integer Paise (Not Floats!)](#6-why-we-store-money-in-integer-paise-not-floats)
7. [What Does CRUD Mean in ExpenseWise?](#7-what-does-crud-mean-in-expensewise)
8. [End-to-End Walkthrough: The ₹250 Chai & Samosa Expense](#8-end-to-end-walkthrough-the-250-chai--samosa-expense)
9. [How Monthly Totals and Balances Are Calculated](#9-how-monthly-totals-and-balances-are-calculated)
10. [How Chart.js Renders Interactive Visualizations](#10-how-chartjs-renders-interactive-visualizations)
11. [What is CSRF Protection and Why Does It Matter?](#11-what-is-csrf-protection-and-why-does-it-matter)
12. [Top 10 Interview Questions & Model Answers](#12-top-10-interview-questions--model-answers)

---

## 1. Understanding the Big Picture: Frontend vs. Backend

Think of a web application like a restaurant:

- **The Frontend (The Dining Room):**  
  This is everything the user sees and touches in their web browser.
  - **HTML5:** The skeletal structure (headings, forms, input fields, tables).
  - **CSS3 / Bootstrap 5:** The interior decor and styling (colors, layout grid, buttons, card borders).
  - **Vanilla JavaScript & Chart.js:** The interactive waiters (rendering dynamic charts, opening modal popups, switching categories).

- **The Backend (The Kitchen & Storeroom):**  
  This runs behind the scenes on a server (your Python program).
  - **Flask:** The master chef. It receives orders from the browser, validates ingredients (inputs), asks the database for recipes/data, and prepares the final meal (HTML page or JSON data).
  - **SQLite Database:** The locked pantry. It permanently stores all transaction records so nothing disappears when the server restarts or the browser tab closes.

---

## 2. What is Flask and How Does It Work?

Flask is a **micro web framework** written in Python. 

### Why is it called "micro"?
"Micro" does not mean it lacks capability. It means Flask provides only the essential core:
1. Routing (mapping URLs to Python functions).
2. Request and response handling.
3. Template rendering (via Jinja2).

It does not force a specific database, form library, or complex configuration on you, making it ideal for learning clean software design.

### The Request-Response Cycle:
```text
[ Browser ]  ──(1. HTTP Request: GET /dashboard)──>  [ Flask (app.py) ]
                                                            │
                                                     (2. Runs Python function)
                                                            │
                                                     (3. Queries SQLite database.py)
                                                            │
[ Browser ]  <──(4. HTTP Response: Rendered HTML)──  [ Jinja2 Template Engine ]
```

---

## 3. Understanding Routes and HTTP Methods (GET vs. POST)

### What is a Route?
A **Route** is a URL path registered with Flask using the `@app.route()` decorator. When a user navigates to a URL, Flask executes the corresponding Python function.

```python
@app.route("/dashboard")
def dashboard():
    # Python code executes here
    return render_template("dashboard.html", ...)
```

### HTTP Methods:
- **`GET` (Retrieve Data):** Used when requesting or viewing a page. Parameters are visible in the URL (e.g., `/dashboard?month=2026-10`). `GET` requests should **never** alter or delete data in the database.
- **`POST` (Submit/Modify Data):** Used when sending sensitive or state-changing data (like submitting an expense form or deleting a record). The data is securely packaged in the hidden **HTTP Request Body**, not in the URL.

---

## 4. How HTML Forms Send Data Over the Internet

When you click **"Add Transaction"** in your browser, the HTML `<form>` does the following:

```html
<form method="POST" action="/transactions/new">
  <input type="hidden" name="csrf_token" value="...">
  <input type="number" name="amount" value="250">
  <select name="category"><option value="Food & Dining">Food & Dining</option></select>
  <button type="submit">Submit</button>
</form>
```

1. The browser serializes all `<input>` and `<select>` values into URL-encoded key-value pairs:
   ```text
   csrf_token=6ea97b70...&transaction_type=expense&amount=250&category=Food+%26+Dining&transaction_date=2026-10-05
   ```
2. The browser sends an HTTP `POST` packet with the header:
   ```http
   Content-Type: application/x-www-form-urlencoded
   ```
3. In Flask, `request.form` automatically parses this payload into a Python dictionary:
   ```python
   amount = request.form.get("amount") # Returns "250"
   category = request.form.get("category") # Returns "Food & Dining"
   ```

---

## 5. What is SQLite and How Does Python Connect to It?

### What is SQLite?
Unlike MySQL or PostgreSQL, which require running a separate server process and network connections, **SQLite is a serverless, file-based relational database engine**. 

The entire database is stored in a single file on your hard disk:
`instance/expenses.db`.

### How Python Connects:
Python includes the `sqlite3` module in its standard library:
```python
import sqlite3

conn = sqlite3.connect("instance/expenses.db")
conn.row_factory = sqlite3.Row # Allows accessing columns by name (row["amount"])
```

### Parameterized SQL Queries (Defense Against SQL Injection):
Never concatenate user input directly into SQL strings (`"SELECT * WHERE id = " + user_id` ❌). That allows hackers to manipulate SQL commands.

In ExpenseWise, we always use **parameterized queries with `?` placeholders**:
```python
# Safe, parameterized query
cursor = conn.execute(
    "INSERT INTO transactions (transaction_type, amount, category, description, transaction_date) VALUES (?, ?, ?, ?, ?);",
    (tx_type, amount_paise, category, description, tx_date)
)
```
The database driver handles escaping and treats inputs strictly as literal values.

---

## 6. Why We Store Money in Integer Paise (Not Floats!)

In software engineering interviews, one of the most common questions is:
> *"Why didn't you store money amounts as floating-point numbers like `float` or `REAL`?"*

### The Problem with Floats:
Computers store floating-point numbers in binary format using the **IEEE 754 standard**. Certain decimal fractions cannot be represented exactly in binary:
```python
# In standard Python:
0.1 + 0.2 == 0.3 # Returns False!
0.1 + 0.2        # Returns 0.30000000000000004
```
If you perform thousands of addition or balance calculations using floats, rounding inaccuracies accumulate and can cause financial discrepancies.

### The Solution: Integer Paise:
1 Rupee = 100 paise.
- ₹250.00 is stored as integer `25000` paise.
- ₹1,500.75 is stored as integer `150075` paise.

Integers are always **100% exact** in computer memory. When presenting numbers to the user in HTML, we simply divide by `100.0` for display.

---

## 7. What Does CRUD Mean in ExpenseWise?

**CRUD** represents the four fundamental operations of persistent data storage:

| Operation | HTTP Method | URL Route | Python Function (`database.py`) | Description |
| :--- | :--- | :--- | :--- | :--- |
| **C** - Create | `POST` | `/transactions/new` | `add_transaction(...)` | Inserts a new record into `transactions` table |
| **R** - Read | `GET` | `/transactions` & `/dashboard` | `get_all_transactions(...)` | Fetches transactions for display |
| **U** - Update | `POST` | `/transactions/<id>/edit` | `update_transaction(...)` | Modifies an existing record by `id` |
| **D** - Delete | `POST` | `/transactions/<id>/delete` | `delete_transaction(...)` | Removes the record matching `id` |

---

## 8. End-to-End Walkthrough: The ₹250 Chai & Samosa Expense

Let's trace what happens when a user records a **₹250** expense:

```text
Step 1: User fills form in browser (Amount: 250, Category: Food & Dining, Date: 2026-10-05)
         │
Step 2: User clicks "Add Transaction"
         │
Step 3: Browser sends HTTP POST to /transactions/new with CSRF token & form fields
         │
Step 4: Flask verifies CSRF token in session
         │
Step 5: Flask validates inputs:
        - Is type 'income' or 'expense'? -> 'expense' (Valid)
        - Is 250 a valid positive number? -> Yes (Valid)
        - Is category non-empty? -> Yes (Valid)
         │
Step 6: Conversion: 250 Rupees * 100 -> 25000 Integer Paise
         │
Step 7: database.add_transaction() runs parameterized INSERT:
        INSERT INTO transactions VALUES (?, ?, ?, ?, ?)
         │
Step 8: SQLite writes row to disk and commits transaction
         │
Step 9: Flask flashes success message: "Successfully added expense of ₹250.00!"
         │
Step 10: Flask issues HTTP 302 Redirect to /transactions (Post/Redirect/Get Pattern)
         │
Step 11: Browser issues HTTP GET /transactions and renders updated table
         │
Step 12: When user visits /dashboard, SQL queries SUM(amount), updating:
         - Total Expenses (+ ₹250.00)
         - Remaining Balance (- ₹250.00)
         - Category Doughnut Chart (Food & Dining slice increases)
```

---

## 9. How Monthly Totals and Balances Are Calculated

Dashboard numbers are **never hardcoded**. They are computed dynamically using SQLite aggregate functions:

### 1. Total Income:
```sql
SELECT COALESCE(SUM(amount), 0) AS total_income
FROM transactions
WHERE transaction_type = 'income'
  AND strftime('%Y-%m', transaction_date) = '2026-10';
```
*(COALESCE ensures that if no records exist, SQLite returns `0` instead of `NULL`)*.

### 2. Total Expense:
```sql
SELECT COALESCE(SUM(amount), 0) AS total_expense
FROM transactions
WHERE transaction_type = 'expense'
  AND strftime('%Y-%m', transaction_date) = '2026-10';
```

### 3. Remaining Balance:
$$\text{Remaining Balance} = \text{Total Income} - \text{Total Expenses}$$

### 4. Category Percentage:
$$\text{Percentage} = \left(\frac{\text{Category Expense}}{\text{Total Monthly Expenses}}\right) \times 100$$

---

## 10. How Chart.js Renders Interactive Visualizations

We use **Chart.js** via CDN (`chart.umd.min.js`) so the application requires zero build tools (like npm or webpack).

### How Data Moves to Chart.js:
1. In `app.py`, Flask calculates the breakdown list of categories:
   ```python
   [
     {"category": "Food & Dining", "total_rupees": 250.0, "percentage": 14.3},
     {"category": "Transportation", "total_rupees": 1500.0, "percentage": 85.7}
   ]
   ```
2. In `dashboard.html`, Jinja converts this Python list into a valid JSON string inside an HTML5 data attribute:
   ```html
   <canvas id="categoryDoughnutChart" data-chart-data='{{ category_breakdown | tojson }}'></canvas>
   ```
3. In `charts.js`, Vanilla JavaScript reads this data attribute and instantiates a Chart object:
   ```javascript
   const rawData = categoryCanvas.getAttribute('data-chart-data');
   const categories = JSON.parse(rawData);

   new Chart(categoryCanvas, {
     type: 'doughnut',
     data: {
       labels: categories.map(c => c.category),
       datasets: [{ data: categories.map(c => c.total_rupees) }]
     }
   });
   ```

---

## 11. What is CSRF Protection and Why Does It Matter?

### What is CSRF (Cross-Site Request Forgery)?
Imagine you log into your bank website, and then in another browser tab, you open a malicious website. The malicious website could secretly contain code that sends a POST request to your bank to transfer money. Because your browser still has the bank's cookie, the bank might accept it.

### How ExpenseWise Prevents CSRF:
1. When your session starts, Flask generates a 16-byte cryptographically random hex token:
   `session['_csrf_token'] = secrets.token_hex(16)`
2. Every form in our application contains a hidden field:
   ```html
   <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
   ```
3. When any `POST` request reaches Flask, `app.before_request` compares the token submitted in the form with the one in the user's session:
   ```python
   if not secrets.compare_digest(expected_token, submitted_token):
       abort(400, "Invalid or missing CSRF token.")
   ```
A third-party attacker cannot guess or read this secret token!

---

## 12. Top 10 Interview Questions & Model Answers

### Q1: Can you describe the architecture of your project?
> **Answer:** ExpenseWise follows a 3-tier architecture:
> - **Presentation Tier:** Responsive UI built with HTML5, CSS3, Bootstrap 5, and Chart.js for data visualization.
> - **Application Tier:** Python Flask handles routing, input validation, CSRF verification, and the Post/Redirect/Get lifecycle.
> - **Data Tier:** An embedded SQLite relational database accessed through a dedicated `database.py` module using parameterized SQL queries.

### Q2: Why did you choose SQLite over MySQL or MongoDB?
> **Answer:** For a single-user personal finance tracker, SQLite offers zero configuration, ACID compliance, and excellent performance. The entire database resides in a single local file (`expenses.db`), eliminating the need to run and maintain an external database server daemon.

### Q3: How do you prevent SQL injection attacks?
> **Answer:** We never use string formatting or concatenation when building SQL queries. Instead, we use parameterized queries with `?` placeholders (e.g. `WHERE id = ?`). The SQLite engine treats user inputs strictly as literal values rather than executable code.

### Q4: Why store money as integer paise instead of floating-point numbers?
> **Answer:** In Python and modern computing (IEEE 754), floating-point arithmetic can introduce fractional precision errors (such as `0.1 + 0.2 == 0.30000000000000004`). In financial software, storing amounts in the smallest currency unit—integer paise—guarantees exact mathematical precision without rounding bugs.

### Q5: What is the Post/Redirect/Get (PRG) pattern?
> **Answer:** PRG is a web development design pattern. When a user submits a form via `POST`, the server processes the data and responds with an HTTP 302 Redirect to a `GET` URL (e.g., `/transactions`) rather than directly rendering HTML. This prevents accidental duplicate form submissions if the user refreshes the page.

### Q6: How does ExpenseWise handle input validation?
> **Answer:** We enforce comprehensive server-side validation in `app.py`:
> - Verifying that the transaction type is strictly either 'income' or 'expense'.
> - Ensuring the amount is a positive number with no more than 2 decimal places.
> - Validating the date format against ISO `YYYY-MM-DD`.
> - If any validation check fails, we return HTTP 422 with a descriptive error message and re-render the form with the user's input preserved.

### Q7: How are the charts rendered without a frontend framework like React?
> **Answer:** We use Chart.js loaded via a CDN. The backend serializes Python summary dictionaries into JSON using Jinja's `| tojson` filter inside HTML5 `data-chart-data` attributes. A lightweight vanilla JavaScript file (`charts.js`) reads these attributes on `DOMContentLoaded` and initializes the canvas charts.

### Q8: How did you test your application?
> **Answer:** We created an automated test suite in `tests/test_app.py` using Python's built-in `unittest` module. It tests all core functionality: dashboard loading, adding income/expenses, updating records, deleting records, validation rejections, monthly calculations, and data persistence across application restarts. Importantly, tests run against a separate temporary database file, ensuring actual user data is never modified.

### Q9: What happens when a user selects a different month on the dashboard?
> **Answer:** When the user changes the month dropdown, an HTTP `GET /dashboard?month=YYYY-MM` request is sent. Flask passes this month string to `database.get_monthly_summary()` and `database.get_category_breakdown()`, which filter transactions using SQLite's `strftime('%Y-%m', transaction_date) = ?`. The updated calculations and chart data are rendered dynamically for that specific month.

### Q10: If you had more time, how would you scale this project?
> **Answer:** 
> 1. Add multi-user authentication using password hashing (e.g., `werkzeug.security` with bcrypt).
> 2. Add CSV/Excel data export and import for transaction records.
> 3. Implement monthly budgeting limits with warning alerts when category spending exceeds a threshold.
> 4. Migrate the database layer from SQLite to PostgreSQL for high-concurrency production deployments.
