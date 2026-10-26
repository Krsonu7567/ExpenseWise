"""
database.py - Database Access Layer for ExpenseWise.

This module handles all database interactions using Python's built-in `sqlite3`
library. It follows clean architecture principles by isolating SQL queries and
data conversions away from Flask route handlers.

Key Design Decisions:
1. Integer Paise Storage:
   All monetary amounts are stored in integer paise (1 Rupee = 100 paise)
   to completely eliminate floating-point arithmetic errors (e.g., 0.1 + 0.2 != 0.3).
2. Parameterized Queries:
   Every SQL statement uses '?' placeholders to guarantee full protection against
   SQL injection attacks.
3. Row Factory:
   Queries return dictionary-like `sqlite3.Row` objects for intuitive column access.
"""

import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

# Default path for the SQLite database file (uses /tmp on Vercel serverless environment)
if os.environ.get("VERCEL"):
    DEFAULT_DB_DIR = "/tmp"
    DEFAULT_DB_PATH = "/tmp/expenses.db"
else:
    DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
    DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "expenses.db")

# Predefined standard categories for clean UI selection
DEFAULT_EXPENSE_CATEGORIES = [
    "Food & Dining",
    "Groceries",
    "Transportation",
    "Utilities & Bills",
    "Housing & Rent",
    "Entertainment",
    "Shopping",
    "Healthcare",
    "Education",
    "Miscellaneous",
]

DEFAULT_INCOME_CATEGORIES = [
    "Salary",
    "Freelance",
    "Investments",
    "Gift / Allowance",
    "Business",
    "Other Income",
]


# ============================================================================
# Helper Functions: Currency & Conversion
# ============================================================================

def rupees_to_paise(rupees: float | int | str) -> int:
    """
    Convert a rupee amount to integer paise.
    Example: 250 -> 25000, "250.50" -> 25050, "1,250.50" -> 125050.
    """
    try:
        if isinstance(rupees, str):
            rupees = rupees.replace(",", "").strip()
        val = float(rupees)
        if val < 0:
            raise ValueError("Amount cannot be negative.")
        return int(round(val * 100))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid rupee amount: {rupees}") from e


def paise_to_rupees(paise: int) -> float:
    """
    Convert integer paise back to float rupees.
    Example: 25050 -> 250.50.
    """
    return round(paise / 100.0, 2)


def format_inr(paise: int) -> str:
    """
    Format integer paise as a readable Indian Rupee string.
    Example: 25050 -> "₹250.50", 1000000 -> "₹10,000.00".
    """
    rupees = paise / 100.0
    return f"₹{rupees:,.2f}"


# ============================================================================
# Connection & Initialization
# ============================================================================

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Create and return a database connection with row_factory set to sqlite3.Row.
    Enables foreign keys and returns dictionary-accessible rows.
    """
    path = db_path or DEFAULT_DB_PATH
    # Ensure directory exists before connecting
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize the SQLite database schema if it doesn't already exist.
    Will never delete existing records during normal application startup.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_type TEXT NOT NULL CHECK(transaction_type IN ('income', 'expense')),
                    amount INTEGER NOT NULL CHECK(amount > 0),
                    category TEXT NOT NULL,
                    description TEXT,
                    transaction_date TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            # Create indexes on frequently queried fields for high performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);"
            )
    finally:
        conn.close()


# ============================================================================
# Transaction CRUD Operations
# ============================================================================

def add_transaction(
    transaction_type: str,
    amount_paise: int,
    category: str,
    description: str,
    transaction_date: str,
    db_path: Optional[str] = None,
) -> int:
    """
    Insert a new transaction into the database using parameterized queries.
    Returns the newly generated transaction ID.
    """
    if transaction_type not in ("income", "expense"):
        raise ValueError("transaction_type must be either 'income' or 'expense'")
    if amount_paise <= 0:
        raise ValueError("amount_paise must be a positive integer greater than 0")
    if not category or not category.strip():
        raise ValueError("category is required")
    if not transaction_date or not transaction_date.strip():
        raise ValueError("transaction_date is required")

    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO transactions (
                    transaction_type, amount, category, description, transaction_date
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (
                    transaction_type.strip(),
                    amount_paise,
                    category.strip(),
                    (description or "").strip(),
                    transaction_date.strip(),
                ),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_transaction_by_id(
    transaction_id: int, db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch a single transaction record by ID.
    Returns a dict with rupee calculations or None if not found.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM transactions WHERE id = ?;", (transaction_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return _row_to_dict(row)
    finally:
        conn.close()


def get_all_transactions(
    month: Optional[str] = None,
    category: Optional[str] = None,
    transaction_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve transactions with optional filtering by month (YYYY-MM),
    category, and transaction_type ('income' or 'expense').
    Sorted chronologically descending (newest first).
    """
    query = "SELECT * FROM transactions WHERE 1=1"
    params: List[Any] = []

    if month and month.strip() and month.lower() != "all":
        query += " AND strftime('%Y-%m', transaction_date) = ?"
        params.append(month.strip())

    if category and category.strip() and category.lower() != "all":
        query += " AND category = ?"
        params.append(category.strip())

    if transaction_type and transaction_type.strip() and transaction_type.lower() != "all":
        query += " AND transaction_type = ?"
        params.append(transaction_type.strip())

    if search and search.strip():
        query += " AND (description LIKE ? OR category LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term])

    query += " ORDER BY transaction_date DESC, id DESC"

    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_recent_transactions(
    limit: int = 5, db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve the most recent transactions up to the specified limit.
    """
    return get_all_transactions(limit=limit, db_path=db_path)


def update_transaction(
    transaction_id: int,
    transaction_type: str,
    amount_paise: int,
    category: str,
    description: str,
    transaction_date: str,
    db_path: Optional[str] = None,
) -> bool:
    """
    Update an existing transaction record by ID using parameterized queries.
    Returns True if a row was updated, False otherwise.
    """
    if transaction_type not in ("income", "expense"):
        raise ValueError("transaction_type must be either 'income' or 'expense'")
    if amount_paise <= 0:
        raise ValueError("amount_paise must be a positive integer greater than 0")
    if not category or not category.strip():
        raise ValueError("category is required")
    if not transaction_date or not transaction_date.strip():
        raise ValueError("transaction_date is required")

    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE transactions
                SET transaction_type = ?,
                    amount = ?,
                    category = ?,
                    description = ?,
                    transaction_date = ?
                WHERE id = ?;
                """,
                (
                    transaction_type.strip(),
                    amount_paise,
                    category.strip(),
                    (description or "").strip(),
                    transaction_date.strip(),
                    transaction_id,
                ),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_transaction(transaction_id: int, db_path: Optional[str] = None) -> bool:
    """
    Delete a single transaction by ID.
    Returns True if the transaction was deleted, False if not found.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "DELETE FROM transactions WHERE id = ?;", (transaction_id,)
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


# ============================================================================
# Analytics & Reporting Operations
# ============================================================================

def get_monthly_summary(
    month_str: str, db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate total income, total expenses, balance, and transaction count
    for a given month formatted as 'YYYY-MM'.
    All figures calculated dynamically from actual SQLite records.
    """
    conn = get_db_connection(db_path)
    try:
        # Total Income
        cur = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_income
            FROM transactions
            WHERE transaction_type = 'income'
              AND strftime('%Y-%m', transaction_date) = ?;
            """,
            (month_str,),
        )
        total_income_paise = cur.fetchone()["total_income"]

        # Total Expense
        cur = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_expense
            FROM transactions
            WHERE transaction_type = 'expense'
              AND strftime('%Y-%m', transaction_date) = ?;
            """,
            (month_str,),
        )
        total_expense_paise = cur.fetchone()["total_expense"]

        # Total count
        cur = conn.execute(
            """
            SELECT COUNT(*) AS tx_count
            FROM transactions
            WHERE strftime('%Y-%m', transaction_date) = ?;
            """,
            (month_str,),
        )
        tx_count = cur.fetchone()["tx_count"]

        balance_paise = total_income_paise - total_expense_paise

        return {
            "month": month_str,
            "income_paise": total_income_paise,
            "income_rupees": paise_to_rupees(total_income_paise),
            "expense_paise": total_expense_paise,
            "expense_rupees": paise_to_rupees(total_expense_paise),
            "balance_paise": balance_paise,
            "balance_rupees": paise_to_rupees(balance_paise),
            "transaction_count": tx_count,
        }
    finally:
        conn.close()


def get_category_breakdown(
    month_str: str, db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Return category-wise expense breakdown for a specific month.
    Includes category name, total paise, total rupees, transaction count,
    and percentage of total monthly expenses.
    """
    conn = get_db_connection(db_path)
    try:
        # Get total expense for percentage calculation
        cur = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_expense
            FROM transactions
            WHERE transaction_type = 'expense'
              AND strftime('%Y-%m', transaction_date) = ?;
            """,
            (month_str,),
        )
        total_expense_paise = cur.fetchone()["total_expense"]

        # Category totals
        cur = conn.execute(
            """
            SELECT category,
                   SUM(amount) AS total_paise,
                   COUNT(*) AS count
            FROM transactions
            WHERE transaction_type = 'expense'
              AND strftime('%Y-%m', transaction_date) = ?
            GROUP BY category
            ORDER BY total_paise DESC;
            """,
            (month_str,),
        )
        rows = cur.fetchall()

        results = []
        for r in rows:
            paise = r["total_paise"]
            pct = round((paise / total_expense_paise * 100), 1) if total_expense_paise > 0 else 0.0
            results.append(
                {
                    "category": r["category"],
                    "total_paise": paise,
                    "total_rupees": paise_to_rupees(paise),
                    "count": r["count"],
                    "percentage": pct,
                }
            )
        return results
    finally:
        conn.close()


def get_monthly_trend(
    num_months: int = 6, db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Return income and expense trends over the last `num_months` months.
    Guarantees sorted chronological order for the trend chart.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.execute(
            """
            SELECT strftime('%Y-%m', transaction_date) AS month,
                   transaction_type,
                   SUM(amount) AS total_paise
            FROM transactions
            GROUP BY month, transaction_type
            ORDER BY month ASC;
            """
        )
        rows = cur.fetchall()

        # Organize by month
        data_by_month: Dict[str, Dict[str, int]] = {}
        for r in rows:
            m = r["month"]
            if m not in data_by_month:
                data_by_month[m] = {"income": 0, "expense": 0}
            data_by_month[m][r["transaction_type"]] = r["total_paise"]

        # If empty, default to current month
        if not data_by_month:
            current_m = datetime.now().strftime("%Y-%m")
            data_by_month[current_m] = {"income": 0, "expense": 0}

        sorted_months = sorted(data_by_month.keys())
        if len(sorted_months) > num_months:
            sorted_months = sorted_months[-num_months:]

        trend = []
        for m in sorted_months:
            inc_paise = data_by_month[m]["income"]
            exp_paise = data_by_month[m]["expense"]
            trend.append(
                {
                    "month": m,
                    "income_paise": inc_paise,
                    "income_rupees": paise_to_rupees(inc_paise),
                    "expense_paise": exp_paise,
                    "expense_rupees": paise_to_rupees(exp_paise),
                    "savings_rupees": paise_to_rupees(inc_paise - exp_paise),
                }
            )
        return trend
    finally:
        conn.close()


def get_available_months(db_path: Optional[str] = None) -> List[str]:
    """
    Return a list of all distinct months (YYYY-MM) present in the database,
    ordered descending. Always ensures current month is included in the list.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.execute(
            """
            SELECT DISTINCT strftime('%Y-%m', transaction_date) AS month
            FROM transactions
            WHERE transaction_date IS NOT NULL
            ORDER BY month DESC;
            """
        )
        months = [r["month"] for r in cur.fetchall() if r["month"]]
        current_m = datetime.now().strftime("%Y-%m")
        if current_m not in months:
            months.insert(0, current_m)
        return sorted(months, reverse=True)
    finally:
        conn.close()


def get_all_categories(db_path: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Return all default and dynamically added categories from database.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.execute(
            """
            SELECT DISTINCT transaction_type, category
            FROM transactions
            ORDER BY category ASC;
            """
        )
        rows = cur.fetchall()
        expense_cats = set(DEFAULT_EXPENSE_CATEGORIES)
        income_cats = set(DEFAULT_INCOME_CATEGORIES)

        for r in rows:
            if r["transaction_type"] == "income":
                income_cats.add(r["category"])
            else:
                expense_cats.add(r["category"])

        return {
            "expense": sorted(list(expense_cats)),
            "income": sorted(list(income_cats)),
        }
    finally:
        conn.close()


# ============================================================================
# Private Helpers
# ============================================================================

def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """
    Convert a sqlite3.Row into a Python dict with added helper values.
    """
    d = dict(row)
    d["amount_rupees"] = paise_to_rupees(d["amount"])
    d["amount_formatted"] = format_inr(d["amount"])
    return d
