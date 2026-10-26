# ExpenseWise — Personal Expense Tracker

A full-stack, beginner-friendly personal finance tracking web application built with **Python 3**, **Flask**, **SQLite**, and **Bootstrap 5**.

ExpenseWise helps users track daily income and expenses in Indian Rupees (₹), visualize spending habits through interactive **Chart.js** charts, analyze monthly savings rates, and filter transaction records.

---

## 🌟 Key Features

- **Executive Financial Dashboard:**
  - 4 Real-time KPI summary cards: **Total Income**, **Total Expenses**, **Remaining Balance**, and **Transaction Count**.
  - Interactive **Expense Breakdown by Category** (Doughnut Chart).
  - 6-Month **Cash Flow Trend** (Income vs. Expense Grouped Bar Chart).
  - Recent transactions overview table with direct edit and delete actions.
  - Dynamic Month Selector that updates all KPI calculations and charts on demand.
- **Transaction CRUD Operations:**
  - **Create:** Add income or expenses with type, amount (₹), category, date, and description.
  - **Read:** Comprehensive transaction history table with badges and formatted rupee amounts.
  - **Update:** Pre-filled edit form with instant validation.
  - **Delete:** Safe deletion workflow with Bootstrap confirmation modal.
- **Financial Analytics & Monthly Reports:**
  - Savings rate percentage indicator (`(Income - Expenses) / Income * 100`).
  - Category-wise spending table with visual percentage progress bars.
  - Top expense category detection.
- **Filter & Search Engine:**
  - Filter transactions by **Month** (`YYYY-MM`), **Type** (Income / Expense), or **Category**.
  - Instant text search across descriptions and notes.
- **Production-Grade Engineering Practices:**
  - **Integer Paise Storage:** All currency values are stored as integers (1 Rupee = 100 paise) in SQLite to eliminate IEEE 754 floating-point rounding errors.
  - **SQL Injection Prevention:** 100% of queries use parameterized SQL (`?` placeholders).
  - **CSRF Protection:** State-changing `POST` requests are verified against cryptographic session tokens.
  - **Post/Redirect/Get (PRG) Pattern:** Prevents accidental duplicate submissions upon page refresh.
  - **Graceful Error Handling:** Custom 400, 404, and 500 status pages with user-friendly alerts.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+ & Flask 3.x | Lightweight WSGI web framework, routes, request validation |
| **Database** | SQLite 3 (`sqlite3`) | Embedded, zero-configuration relational database |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript | Clean semantic structure and UI interactions |
| **Styling** | Bootstrap 5.3 & Bootstrap Icons | Responsive grid system, modal dialogs, and components |
| **Typography**| Google Fonts (*Plus Jakarta Sans*) | Modern, legible financial dashboard aesthetics |
| **Visuals** | Chart.js 4.4 (via CDN) | Dynamic responsive charts for categories and trends |
| **Testing** | Python `unittest` | Automated test suite running on isolated in-memory/temp DBs |

---

## 📂 Project Directory Structure

```text
d:/EXPENSEWISE/
│
├── app.py                  # Flask application factory, routes, CSRF, input validation
├── database.py             # SQLite data access layer, parameterized CRUD, analytics
├── requirements.txt        # Minimal Python dependencies (only Flask)
├── README.md               # Project documentation and quickstart guide
├── LEARNING_GUIDE.md       # Comprehensive beginner guide & interview preparation
├── .gitignore              # Ignored files (virtual environment, database instances)
│
├── instance/
│   └── expenses.db         # SQLite database file (auto-generated on first run)
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Master layout (navbar, footer, flash alerts, modal)
│   ├── dashboard.html      # KPI summary cards, Chart.js canvases, recent entries
│   ├── transactions.html   # Filterable transaction history table
│   ├── transaction_form.html# Add & Edit transaction form with dynamic categories
│   └── reports.html        # Monthly financial health, savings rate, and breakdown
│
├── static/
│   ├── css/
│   │   └── style.css       # Custom design system, badges, card animations
│   └── js/
│       └── charts.js       # Chart.js initialization for Doughnut and Bar charts
│
└── tests/
    └── test_app.py         # 12 automated unit and integration tests
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
Ensure Python 3.10 or newer is installed on your computer:
```powershell
python --version
```

### 2. Clone or Navigate to the Project Folder
```powershell
cd d:\EXPENSEWISE
```

### 3. Set Up Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate on Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# (Or on macOS / Linux / Git Bash):
# source .venv/bin/activate
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Run the Application
```powershell
python app.py
```

The web server will start locally:
👉 Open your browser at: **`http://127.0.0.1:5000`**

---

## 🧪 Running Automated Tests

ExpenseWise includes an automated test suite covering routes, form validation, database operations, calculations, persistence, and CSRF protection.

Run the test suite using Python's standard test runner:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

**Expected output:**
```text
test_add_expense_transaction (test_app.ExpenseWiseTestCase) ... ok
test_add_income_transaction (test_app.ExpenseWiseTestCase) ... ok
test_csrf_protection_rejects_missing_token (test_app.ExpenseWiseTestCase) ... ok
test_dashboard_opens (test_app.ExpenseWiseTestCase) ... ok
test_data_persists_after_restarting_application (test_app.ExpenseWiseTestCase) ... ok
test_deleting_transaction (test_app.ExpenseWiseTestCase) ... ok
test_editing_transaction (test_app.ExpenseWiseTestCase) ... ok
test_invalid_amounts_rejected (test_app.ExpenseWiseTestCase) ... ok
test_missing_required_fields_rejected (test_app.ExpenseWiseTestCase) ... ok
test_monthly_calculations (test_app.ExpenseWiseTestCase) ... ok
test_transaction_filters (test_app.ExpenseWiseTestCase) ... ok
test_transactions_appear_in_history (test_app.ExpenseWiseTestCase) ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.75s

OK
```

> **Note:** Tests automatically create a temporary, isolated SQLite database file. Running the test suite will **never** alter or delete your actual recorded transactions.

---

## 📖 Beginner Learning Guide & Interview Prep

Are you an engineering student or beginner preparing to explain this project during technical or HR interviews?
Check out **[`LEARNING_GUIDE.md`](file:///d:/EXPENSEWISE/LEARNING_GUIDE.md)** for:
- Explanation of Frontend vs. Backend concepts in simple terms.
- How Flask handles routes and the HTTP Request-Response cycle.
- Detailed step-by-step walkthrough of the **₹250 Chai & Samosa** expense data flow.
- Why integer paise storage prevents financial rounding bugs.
- Top 10 frequently asked interview questions on this project.
