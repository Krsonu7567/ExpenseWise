"""
test_app.py - Automated Unit & Integration Tests for ExpenseWise.

Uses Python's built-in `unittest` module. Tests run against a temporary,
isolated SQLite database file so existing user data is never touched or deleted.
"""

import os
import shutil
import tempfile
import unittest
from datetime import datetime

import database
from app import create_app


class ExpenseWiseTestCase(unittest.TestCase):
    """Full test suite covering CRUD, validations, calculations, and persistence."""

    def setUp(self):
        """Create a temporary directory and test database for every test."""
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_dir, "test_expenses.db")

        # Create app configured with test database and testing mode
        self.app = create_app({
            "TESTING": True,
            "DB_PATH": self.test_db_path,
            "SECRET_KEY": "test-secret-key-12345",
            "WTF_CSRF_ENABLED": False,  # Simplified POST testing for automated test client
        })
        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up temporary test files after each test."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ------------------------------------------------------------------------
    # 1. Dashboard Tests
    # ------------------------------------------------------------------------

    def test_dashboard_opens(self):
        """Verify dashboard route loads with HTTP 200 and required KPI elements."""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Financial Dashboard", content)
        self.assertIn("Total Income", content)
        self.assertIn("Total Expenses", content)
        self.assertIn("Remaining Balance", content)
        self.assertIn("Transactions", content)

    # ------------------------------------------------------------------------
    # 2. Add Transactions (Income & Expense)
    # ------------------------------------------------------------------------

    def test_add_income_transaction(self):
        """Verify adding an income transaction saves in integer paise and redirects."""
        response = self.client.post(
            "/transactions/new",
            data={
                "transaction_type": "income",
                "amount": "25000.50",
                "category": "Salary",
                "description": "October Monthly Stipend",
                "transaction_date": "2026-10-01",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Successfully added income of ₹25,000.50!", response.data.decode("utf-8"))

        # Verify database record
        txs = database.get_all_transactions(db_path=self.test_db_path)
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]["transaction_type"], "income")
        self.assertEqual(txs[0]["amount"], 2500050)  # 25,000.50 * 100 paise
        self.assertEqual(txs[0]["amount_rupees"], 25000.50)
        self.assertEqual(txs[0]["category"], "Salary")

    def test_add_expense_transaction(self):
        """Verify adding ₹250 chai & samosa expense saves accurately."""
        response = self.client.post(
            "/transactions/new",
            data={
                "transaction_type": "expense",
                "amount": "250",
                "category": "Food & Dining",
                "description": "Chai and samosa with study group",
                "transaction_date": "2026-10-05",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Successfully added expense of ₹250.00!", response.data.decode("utf-8"))

        txs = database.get_all_transactions(db_path=self.test_db_path)
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]["transaction_type"], "expense")
        self.assertEqual(txs[0]["amount"], 25000)  # 250 * 100 paise
        self.assertEqual(txs[0]["amount_rupees"], 250.00)

    # ------------------------------------------------------------------------
    # 3. Transaction History View
    # ------------------------------------------------------------------------

    def test_transactions_appear_in_history(self):
        """Verify added transactions are rendered in the transaction table."""
        # Add sample data
        database.add_transaction(
            "income", 500000, "Freelance", "Website design", "2026-10-10", self.test_db_path
        )
        database.add_transaction(
            "expense", 120000, "Groceries", "Supermarket run", "2026-10-11", self.test_db_path
        )

        response = self.client.get("/transactions")
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Website design", content)
        self.assertIn("Supermarket run", content)
        self.assertIn("Freelance", content)
        self.assertIn("Groceries", content)
        self.assertIn("+ ₹5,000.00", content)
        self.assertIn("- ₹1,200.00", content)

    # ------------------------------------------------------------------------
    # 4. Edit Transactions
    # ------------------------------------------------------------------------

    def test_editing_transaction(self):
        """Verify editing a transaction updates values in database."""
        tx_id = database.add_transaction(
            "expense", 15000, "Food & Dining", "Coffee", "2026-10-12", self.test_db_path
        )

        # GET edit page prefill
        get_resp = self.client.get(f"/transactions/{tx_id}/edit")
        self.assertEqual(get_resp.status_code, 200)
        self.assertIn("150.00", get_resp.data.decode("utf-8"))

        # POST update
        post_resp = self.client.post(
            f"/transactions/{tx_id}/edit",
            data={
                "transaction_type": "expense",
                "amount": "200.50",
                "category": "Food & Dining",
                "description": "Coffee and Croissant",
                "transaction_date": "2026-10-12",
            },
            follow_redirects=True,
        )
        self.assertEqual(post_resp.status_code, 200)
        self.assertIn("Transaction updated successfully!", post_resp.data.decode("utf-8"))

        updated_tx = database.get_transaction_by_id(tx_id, self.test_db_path)
        self.assertEqual(updated_tx["amount"], 20050)
        self.assertEqual(updated_tx["amount_rupees"], 200.50)
        self.assertEqual(updated_tx["description"], "Coffee and Croissant")

    # ------------------------------------------------------------------------
    # 5. Delete Transactions
    # ------------------------------------------------------------------------

    def test_deleting_transaction(self):
        """Verify deleting a transaction removes it completely."""
        tx_id = database.add_transaction(
            "expense", 9900, "Shopping", "Book", "2026-10-15", self.test_db_path
        )
        self.assertIsNotNone(database.get_transaction_by_id(tx_id, self.test_db_path))

        response = self.client.post(f"/transactions/{tx_id}/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Transaction deleted successfully.", response.data.decode("utf-8"))

        self.assertIsNone(database.get_transaction_by_id(tx_id, self.test_db_path))

    # ------------------------------------------------------------------------
    # 6. Input Validation
    # ------------------------------------------------------------------------

    def test_invalid_amounts_rejected(self):
        """Verify invalid or malformed amounts return HTTP 422 with descriptive error."""
        invalid_amounts = ["-50", "0", "abc", "", "15.999"]
        for amt in invalid_amounts:
            response = self.client.post(
                "/transactions/new",
                data={
                    "transaction_type": "expense",
                    "amount": amt,
                    "category": "Food & Dining",
                    "description": "Test invalid",
                    "transaction_date": "2026-10-15",
                },
            )
            self.assertEqual(
                response.status_code, 422, f"Amount '{amt}' should have been rejected."
            )

        # Database must still have 0 records
        txs = database.get_all_transactions(db_path=self.test_db_path)
        self.assertEqual(len(txs), 0)

    def test_missing_required_fields_rejected(self):
        """Verify missing type, date or category is rejected."""
        # Missing category
        response = self.client.post(
            "/transactions/new",
            data={
                "transaction_type": "expense",
                "amount": "100",
                "category": "",
                "transaction_date": "2026-10-15",
            },
        )
        self.assertEqual(response.status_code, 422)

        # Missing date
        response2 = self.client.post(
            "/transactions/new",
            data={
                "transaction_type": "expense",
                "amount": "100",
                "category": "Groceries",
                "transaction_date": "",
            },
        )
        self.assertEqual(response2.status_code, 422)

    # ------------------------------------------------------------------------
    # 7. Monthly Calculations
    # ------------------------------------------------------------------------

    def test_monthly_calculations(self):
        """Verify income, expenses, and balance calculations for a specific month."""
        # October transactions
        database.add_transaction("income", 4000000, "Salary", "October Pay", "2026-10-01", self.test_db_path) # ₹40,000
        database.add_transaction("expense", 1200000, "Housing & Rent", "October Rent", "2026-10-02", self.test_db_path) # ₹12,000
        database.add_transaction("expense", 300000, "Food & Dining", "Groceries", "2026-10-05", self.test_db_path) # ₹3,000

        # September transaction (should NOT affect October calculations)
        database.add_transaction("expense", 500000, "Shopping", "September Clothes", "2026-09-20", self.test_db_path)

        summary_oct = database.get_monthly_summary("2026-10", self.test_db_path)
        self.assertEqual(summary_oct["income_rupees"], 40000.0)
        self.assertEqual(summary_oct["expense_rupees"], 15000.0)
        self.assertEqual(summary_oct["balance_rupees"], 25000.0)
        self.assertEqual(summary_oct["transaction_count"], 3)

        # Check Category Breakdown
        breakdown = database.get_category_breakdown("2026-10", self.test_db_path)
        self.assertEqual(len(breakdown), 2)
        # Rent is 12,000 out of 15,000 = 80.0%
        self.assertEqual(breakdown[0]["category"], "Housing & Rent")
        self.assertEqual(breakdown[0]["percentage"], 80.0)
        # Food is 3,000 out of 15,000 = 20.0%
        self.assertEqual(breakdown[1]["category"], "Food & Dining")
        self.assertEqual(breakdown[1]["percentage"], 20.0)

    # ------------------------------------------------------------------------
    # 8. Filters
    # ------------------------------------------------------------------------

    def test_transaction_filters(self):
        """Verify category, type, and month filters work on transaction list."""
        database.add_transaction("income", 1000000, "Salary", "Job", "2026-10-01", self.test_db_path)
        database.add_transaction("expense", 50000, "Transportation", "Metro", "2026-10-02", self.test_db_path)
        database.add_transaction("expense", 30000, "Food & Dining", "Lunch", "2026-09-15", self.test_db_path)

        # Filter by type=expense
        expense_only = database.get_all_transactions(transaction_type="expense", db_path=self.test_db_path)
        self.assertEqual(len(expense_only), 2)

        # Filter by category=Transportation
        transport_only = database.get_all_transactions(category="Transportation", db_path=self.test_db_path)
        self.assertEqual(len(transport_only), 1)
        self.assertEqual(transport_only[0]["description"], "Metro")

        # Filter by month=2026-09
        september_only = database.get_all_transactions(month="2026-09", db_path=self.test_db_path)
        self.assertEqual(len(september_only), 1)
        self.assertEqual(september_only[0]["description"], "Lunch")

    # ------------------------------------------------------------------------
    # 9. Data Persistence Across Restarts
    # ------------------------------------------------------------------------

    def test_data_persists_after_restarting_application(self):
        """Verify data saved to SQLite database file survives application recreation."""
        # 1. Create first app instance and insert data
        app1 = create_app({"TESTING": True, "DB_PATH": self.test_db_path, "WTF_CSRF_ENABLED": False})
        client1 = app1.test_client()
        client1.post(
            "/transactions/new",
            data={
                "transaction_type": "expense",
                "amount": "1450.75",
                "category": "Utilities & Bills",
                "description": "Electricity Bill",
                "transaction_date": "2026-10-18",
            },
        )
        del client1
        del app1

        # 2. Spin up a brand new app instance pointing to the exact same file
        app2 = create_app({"TESTING": True, "DB_PATH": self.test_db_path, "WTF_CSRF_ENABLED": False})
        client2 = app2.test_client()
        resp = client2.get("/transactions")
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode("utf-8")
        self.assertIn("Electricity Bill", content)
        self.assertIn("₹1,450.75", content)

        # Check raw database rows
        rows = database.get_all_transactions(db_path=self.test_db_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["amount"], 145075)

    # ------------------------------------------------------------------------
    # 10. CSRF Protection
    # ------------------------------------------------------------------------

    def test_csrf_protection_rejects_missing_token(self):
        """Verify that when CSRF protection is active, POST without token returns 400."""
        # App with CSRF enabled
        secure_app = create_app({
            "TESTING": True,
            "DB_PATH": self.test_db_path,
            "WTF_CSRF_ENABLED": True,
            "SECRET_KEY": "secure-secret-key",
        })
        secure_client = secure_app.test_client()

        # POST without any CSRF token
        resp = secure_client.post(
            "/transactions/new",
            data={
                "transaction_type": "expense",
                "amount": "100",
                "category": "Food & Dining",
                "transaction_date": "2026-10-20",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("CSRF", resp.data.decode("utf-8"))

    # ------------------------------------------------------------------------
    # 11. Edge Cases & Robustness
    # ------------------------------------------------------------------------

    def test_add_transaction_with_comma_formatted_amount(self):
        """Verify amounts with commas (e.g. 1,500.50) are safely cleaned and stored."""
        response = self.client.post(
            "/transactions/new",
            data={
                "transaction_type": "expense",
                "amount": "1,500.50",
                "category": "Shopping",
                "description": "Headphones",
                "transaction_date": "2026-10-22",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        txs = database.get_all_transactions(db_path=self.test_db_path)
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]["amount"], 150050)
        self.assertEqual(txs[0]["amount_rupees"], 1500.50)

    def test_category_options_prerendered_in_html(self):
        """Verify category options are server-side pre-rendered in HTML even before JS runs."""
        response = self.client.get("/transactions/new")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        # Note: Jinja2 automatically escapes '&' to '&amp;' in HTML templates for security
        self.assertIn("Food &amp; Dining", html)
        self.assertIn("Transportation", html)

    def test_delete_transaction_redirects_to_referrer(self):
        """Verify delete action safely redirects back to referring page on the same host."""
        tx_id = database.add_transaction(
            "expense", 50000, "Education", "Course", "2026-10-24", self.test_db_path
        )
        resp = self.client.post(
            f"/transactions/{tx_id}/delete",
            headers={"Referer": "http://localhost/dashboard"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["Location"], "http://localhost/dashboard")


if __name__ == "__main__":
    unittest.main()

