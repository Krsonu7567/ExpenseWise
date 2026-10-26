"""
app.py - Flask Application for ExpenseWise.

This file configures the Flask application, registers URL routes, implements
server-side validation, enforces CSRF security tokens on all POST requests,
and connects frontend views to the SQLite database.

Design Principles:
- Simple, readable Python that a beginner or interviewer can inspect effortlessly.
- Strict server-side validation to reject malformed inputs.
- Post/Redirect/Get (PRG) pattern on all form submissions with flash feedback.
- Clean JSON API endpoints for Chart.js visualization.
"""

import os
import re
import secrets
from datetime import datetime
from typing import Optional

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import database


def create_app(test_config: Optional[dict] = None) -> Flask:
    """
    Application factory to create and configure the Flask app.
    Supports injecting custom test configurations (e.g. isolated test databases).
    """
    app = Flask(__name__, instance_relative_config=True)

    # Secret key for secure session cookies and CSRF token signing
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "expensewise-dev-secret-key-3b89a42f"),
        DB_PATH=database.DEFAULT_DB_PATH,
    )

    if test_config:
        app.config.update(test_config)

    # Initialize the database table on startup (does not overwrite existing data)
    database.init_db(app.config["DB_PATH"])

    # ------------------------------------------------------------------------
    # CSRF Protection & Context Processors
    # ------------------------------------------------------------------------

    @app.before_request
    def check_csrf():
        """
        Verify the presence and correctness of CSRF token on all POST requests.
        Protects against Cross-Site Request Forgery without external dependencies.
        """
        if request.method == "POST":
            # Allow skipping CSRF check if explicitly configured in tests
            if app.config.get("TESTING") and app.config.get("WTF_CSRF_ENABLED") is False:
                return

            expected_token = session.get("_csrf_token")
            submitted_token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")

            if not expected_token or not submitted_token or not secrets.compare_digest(expected_token, submitted_token):
                abort(400, description="Invalid or missing CSRF security token. Please refresh and try again.")

    @app.context_processor
    def inject_global_template_vars():
        """
        Make csrf_token, current_date, and current_year available in all Jinja templates.
        """
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_hex(16)

        now = datetime.now()
        return {
            "csrf_token": session["_csrf_token"],
            "current_month_str": now.strftime("%Y-%m"),
            "current_date_str": now.strftime("%Y-%m-%d"),
            "current_year": now.year,
        }

    # ------------------------------------------------------------------------
    # Custom Jinja Template Filters
    # ------------------------------------------------------------------------

    @app.template_filter("currency_inr")
    def currency_inr_filter(paise_value):
        """Format an integer paise amount into a readable Indian Rupee string."""
        if paise_value is None:
            return "₹0.00"
        try:
            val = int(paise_value)
            return database.format_inr(val)
        except (ValueError, TypeError):
            return "₹0.00"

    @app.template_filter("format_date")
    def format_date_filter(date_str):
        """Format 'YYYY-MM-DD' into a user-friendly 'DD MMM YYYY' format."""
        if not date_str:
            return ""
        try:
            dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            return dt.strftime("%d %b %Y")
        except ValueError:
            return str(date_str)

    # ------------------------------------------------------------------------
    # Routes: Dashboard & Navigation
    # ------------------------------------------------------------------------

    @app.route("/")
    def index():
        """Root route: Redirect to dashboard."""
        return redirect(url_for("dashboard"))

    @app.route("/dashboard")
    def dashboard():
        """
        Main Dashboard:
        Displays selected month's 4 summary cards (Income, Expense, Balance, Count),
        recent transactions, and dynamic data for charts.
        """
        db_path = app.config["DB_PATH"]
        selected_month = request.args.get("month", "").strip()

        # Default to current month if not specified or invalid format
        if not selected_month or not re.match(r"^\d{4}-\d{2}$", selected_month):
            selected_month = datetime.now().strftime("%Y-%m")

        available_months = database.get_available_months(db_path)
        if selected_month not in available_months:
            available_months.insert(0, selected_month)

        summary = database.get_monthly_summary(selected_month, db_path)
        category_breakdown = database.get_category_breakdown(selected_month, db_path)
        monthly_trend = database.get_monthly_trend(num_months=6, db_path=db_path)
        recent_transactions = database.get_recent_transactions(limit=6, db_path=db_path)

        return render_template(
            "dashboard.html",
            selected_month=selected_month,
            available_months=available_months,
            summary=summary,
            category_breakdown=category_breakdown,
            monthly_trend=monthly_trend,
            recent_transactions=recent_transactions,
        )

    # ------------------------------------------------------------------------
    # Routes: Transactions (List, Add, Edit, Delete)
    # ------------------------------------------------------------------------

    @app.route("/transactions")
    def transactions_list():
        """
        Transaction History:
        Displays all transactions with optional filters for month, category,
        and transaction type (income / expense).
        """
        db_path = app.config["DB_PATH"]
        month_filter = request.args.get("month", "all").strip()
        category_filter = request.args.get("category", "all").strip()
        type_filter = request.args.get("type", "all").strip()
        search_query = request.args.get("search", "").strip()

        transactions = database.get_all_transactions(
            month=month_filter,
            category=category_filter,
            transaction_type=type_filter,
            search=search_query,
            db_path=db_path,
        )

        available_months = database.get_available_months(db_path)
        categories = database.get_all_categories(db_path)

        return render_template(
            "transactions.html",
            transactions=transactions,
            selected_month=month_filter,
            selected_category=category_filter,
            selected_type=type_filter,
            search_query=search_query,
            available_months=available_months,
            categories=categories,
        )

    @app.route("/transactions/new", methods=["GET", "POST"])
    def add_transaction_view():
        """
        Create a new transaction.
        GET: Render blank form.
        POST: Validate, convert rupees to paise, save to SQLite, redirect.
        """
        db_path = app.config["DB_PATH"]
        categories = database.get_all_categories(db_path)

        if request.method == "POST":
            # Extract form inputs
            tx_type = request.form.get("transaction_type", "").strip().lower()
            amount_str = request.form.get("amount", "").strip()
            category = request.form.get("category", "").strip()
            description = request.form.get("description", "").strip()
            tx_date = request.form.get("transaction_date", "").strip()

            # Validation logic
            amount_clean = amount_str.replace(",", "").strip()
            errors = _validate_transaction_input(tx_type, amount_clean, category, tx_date, description)

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template(
                    "transaction_form.html",
                    is_edit=False,
                    form_data=request.form,
                    categories=categories,
                ), 422

            # Convert rupee amount to paise (e.g. ₹250 -> 25000 paise)
            amount_paise = database.rupees_to_paise(amount_clean)

            # Insert into database
            database.add_transaction(
                transaction_type=tx_type,
                amount_paise=amount_paise,
                category=category,
                description=description,
                transaction_date=tx_date,
                db_path=db_path,
            )

            flash(f"Successfully added {tx_type} of ₹{float(amount_clean):,.2f}!", "success")
            return redirect(url_for("transactions_list"))

        # Default pre-filled data for new transaction
        default_data = {
            "transaction_type": "expense",
            "amount": "",
            "category": "Food & Dining",
            "description": "",
            "transaction_date": datetime.now().strftime("%Y-%m-%d"),
        }

        return render_template(
            "transaction_form.html",
            is_edit=False,
            form_data=default_data,
            categories=categories,
        )

    @app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
    def edit_transaction_view(transaction_id: int):
        """
        Edit an existing transaction.
        GET: Fetch and display current values.
        POST: Validate, update record in SQLite, redirect.
        """
        db_path = app.config["DB_PATH"]
        transaction = database.get_transaction_by_id(transaction_id, db_path)

        if not transaction:
            flash(f"Transaction #{transaction_id} not found.", "warning")
            return redirect(url_for("transactions_list"))

        categories = database.get_all_categories(db_path)

        if request.method == "POST":
            tx_type = request.form.get("transaction_type", "").strip().lower()
            amount_str = request.form.get("amount", "").strip()
            category = request.form.get("category", "").strip()
            description = request.form.get("description", "").strip()
            tx_date = request.form.get("transaction_date", "").strip()

            amount_clean = amount_str.replace(",", "").strip()
            errors = _validate_transaction_input(tx_type, amount_clean, category, tx_date, description)

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template(
                    "transaction_form.html",
                    is_edit=True,
                    transaction_id=transaction_id,
                    form_data=request.form,
                    categories=categories,
                ), 422

            amount_paise = database.rupees_to_paise(amount_clean)

            updated = database.update_transaction(
                transaction_id=transaction_id,
                transaction_type=tx_type,
                amount_paise=amount_paise,
                category=category,
                description=description,
                transaction_date=tx_date,
                db_path=db_path,
            )

            if updated:
                flash("Transaction updated successfully!", "success")
            else:
                flash("Unable to update transaction. Record may have been removed.", "danger")

            return redirect(url_for("transactions_list"))

        # Pre-fill form from database row
        form_data = {
            "transaction_type": transaction["transaction_type"],
            "amount": f"{transaction['amount_rupees']:.2f}",
            "category": transaction["category"],
            "description": transaction["description"] or "",
            "transaction_date": transaction["transaction_date"],
        }

        return render_template(
            "transaction_form.html",
            is_edit=True,
            transaction_id=transaction_id,
            form_data=form_data,
            categories=categories,
        )

    @app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
    def delete_transaction_view(transaction_id: int):
        """
        Delete a transaction with confirmation.
        State-changing endpoint protected by POST method and CSRF token.
        """
        db_path = app.config["DB_PATH"]
        deleted = database.delete_transaction(transaction_id, db_path)

        if deleted:
            flash("Transaction deleted successfully.", "success")
        else:
            flash(f"Could not delete transaction #{transaction_id}; it was not found.", "warning")

        # Safely redirect back to referring page if on the same host (e.g. dashboard vs history)
        referrer = request.referrer
        if referrer and request.host in referrer:
            return redirect(referrer)
        return redirect(url_for("transactions_list"))

    # ------------------------------------------------------------------------
    # Routes: Monthly Reports
    # ------------------------------------------------------------------------

    @app.route("/reports")
    def reports_view():
        """
        Monthly Reports Page:
        Displays in-depth financial summary, category breakdowns with percentages,
        savings rate, and spending insights for any selected month.
        """
        db_path = app.config["DB_PATH"]
        selected_month = request.args.get("month", "").strip()

        if not selected_month or not re.match(r"^\d{4}-\d{2}$", selected_month):
            selected_month = datetime.now().strftime("%Y-%m")

        available_months = database.get_available_months(db_path)
        if selected_month not in available_months:
            available_months.insert(0, selected_month)

        summary = database.get_monthly_summary(selected_month, db_path)
        category_breakdown = database.get_category_breakdown(selected_month, db_path)

        # Calculate financial health indicators
        income = summary["income_rupees"]
        expense = summary["expense_rupees"]
        balance = summary["balance_rupees"]

        savings_rate = 0.0
        if income > 0:
            savings_rate = round(max(0.0, (balance / income) * 100), 1)

        highest_expense_category = category_breakdown[0] if category_breakdown else None

        return render_template(
            "reports.html",
            selected_month=selected_month,
            available_months=available_months,
            summary=summary,
            category_breakdown=category_breakdown,
            savings_rate=savings_rate,
            highest_expense_category=highest_expense_category,
        )

    # ------------------------------------------------------------------------
    # API Endpoints (Used by Chart.js)
    # ------------------------------------------------------------------------

    @app.route("/api/chart-data")
    def api_chart_data():
        """
        JSON endpoint returning chart data for a requested month.
        Powers the frontend Chart.js doughnut and bar charts.
        """
        db_path = app.config["DB_PATH"]
        selected_month = request.args.get("month", "").strip()

        if not selected_month or not re.match(r"^\d{4}-\d{2}$", selected_month):
            selected_month = datetime.now().strftime("%Y-%m")

        breakdown = database.get_category_breakdown(selected_month, db_path)
        trend = database.get_monthly_trend(num_months=6, db_path=db_path)
        summary = database.get_monthly_summary(selected_month, db_path)

        return jsonify({
            "status": "success",
            "month": selected_month,
            "summary": summary,
            "category_breakdown": breakdown,
            "monthly_trend": trend,
        })

    # ------------------------------------------------------------------------
    # Error Handlers
    # ------------------------------------------------------------------------

    @app.errorhandler(400)
    def bad_request_error(e):
        return render_template(
            "base.html",
            page_title="Bad Request (400)",
            error_code=400,
            error_message=str(getattr(e, "description", "Bad Request")),
        ), 400

    @app.errorhandler(404)
    def not_found_error(e):
        return render_template(
            "base.html",
            page_title="Page Not Found (404)",
            error_code=404,
            error_message="The page or transaction you are looking for does not exist.",
        ), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template(
            "base.html",
            page_title="Server Error (500)",
            error_code=500,
            error_message="An unexpected error occurred. Please try again shortly.",
        ), 500

    return app


# ============================================================================
# Validation Helper
# ============================================================================

def _validate_transaction_input(
    tx_type: str,
    amount_str: str,
    category: str,
    tx_date: str,
    description: str,
) -> list[str]:
    """
    Validate all transaction form fields before interacting with the database.
    Returns a list of error strings. If valid, the returned list is empty.
    """
    errors = []

    # 1. Type validation
    if tx_type not in ("income", "expense"):
        errors.append("Transaction type must be either 'Income' or 'Expense'.")

    # 2. Amount validation
    if not amount_str:
        errors.append("Amount is required.")
    else:
        clean_amt = amount_str.replace(",", "").strip()
        try:
            val = float(clean_amt)
            if val <= 0:
                errors.append("Amount must be greater than zero.")
            elif val > 100_000_000:
                errors.append("Amount cannot exceed ₹10,00,00,000.")
            # Check maximum 2 decimal places
            parts = clean_amt.split(".")
            if len(parts) == 2 and len(parts[1]) > 2:
                errors.append("Amount cannot have more than 2 decimal places (paise).")
        except ValueError:
            errors.append("Please enter a valid numeric amount (e.g. 250 or 250.50).")

    # 3. Category validation
    if not category:
        errors.append("Please select or enter a category.")
    elif len(category) > 50:
        errors.append("Category name cannot exceed 50 characters.")

    # 4. Date validation
    if not tx_date:
        errors.append("Transaction date is required.")
    else:
        try:
            parsed_date = datetime.strptime(tx_date, "%Y-%m-%d")
            # Reasonable date range sanity check (e.g., year 2000 to 2100)
            if parsed_date.year < 2000 or parsed_date.year > 2100:
                errors.append("Transaction date year must be between 2000 and 2100.")
        except ValueError:
            errors.append("Transaction date must be in YYYY-MM-DD format.")

    # 5. Description validation
    if description and len(description) > 255:
        errors.append("Description cannot exceed 255 characters.")

    return errors


# Standard entry point when running `python app.py`
app = create_app()

if __name__ == "__main__":
    # Host on 127.0.0.1:5000 for local development
    print("Starting ExpenseWise web server on http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=True)
