from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from datetime import datetime

from bson import ObjectId

app = Flask(__name__)
app.secret_key = "your_secret_key"

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["supplier_db"]
suppliers_collection = db["suppliers"]
transactions_collection = db["transactions"]

# Homepage: List of all suppliers
@app.route("/", methods=["GET"])
def home():
    search = request.args.get("search", "")
    filter_balance = request.args.get("filter_balance", "all")

    query = {}
    if search:
        query["supplier_name"] = {"$regex": search, "$options": "i"}

    # Fetch all suppliers matching the query
    suppliers = list(suppliers_collection.find(query))

    # Calculate remaining balance for each supplier
    for supplier in suppliers:
        supplier_id = str(supplier["_id"])
        transactions = list(transactions_collection.find({"customer_id": supplier_id}))

        total_credit = sum(t.get("credit", 0) for t in transactions)
        total_debit = sum(t.get("debit", 0) for t in transactions)
        remaining_balance = total_credit - total_debit

        supplier["balance"] = remaining_balance  # Add balance to each supplier dynamically

    # Filter by balance if requested
    if filter_balance == "pending":
        suppliers = [s for s in suppliers if s["balance"] > 0]
    elif filter_balance == "settled":
        suppliers = [s for s in suppliers if s["balance"] == 0]

    return render_template("home.html", suppliers=suppliers, search=search, filter_balance=filter_balance)


# Add a new supplier
@app.route("/customer/add", methods=["GET", "POST"])
def add_customer():
    if request.method == "POST":
        supplier_name = request.form["supplier_name"]
        contact = request.form["contact"]
        email = request.form["email"]
        address = request.form["address"]

        # Add customer to the database
        new_supplier = {
            "supplier_name": supplier_name,
            "contact": contact,
            "email": email,
            "address": address,
            "balance": 0  # Initial balance is 0
        }
        suppliers_collection.insert_one(new_supplier)
        flash("New customer added successfully!", "success")
        return redirect(url_for("home"))  # Redirect to home page or suppliers list

    return render_template("customer_add.html")


@app.route("/customer/edit/<customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):
    customer = suppliers_collection.find_one({"_id": ObjectId(customer_id)})
    
    if request.method == "POST":
        # Get updated data from the form
        supplier_name = request.form["supplier_name"]
        contact = request.form["contact"]
        email = request.form["email"]
        address = request.form["address"]
        
        # Update customer details in the database
        suppliers_collection.update_one(
            {"_id": ObjectId(customer_id)},
            {
                "$set": {
                    "supplier_name": supplier_name,
                    "contact": contact,
                    "email": email,
                    "address": address
                }
            }
        )
        flash("Customer details updated successfully!", "success")
        return redirect(url_for("home"))  # Redirect to home page or customers list
    
    return render_template("customer_edit.html", customer=customer)

# Supplier details: Transactions
from datetime import datetime
from flask import render_template, request
from bson.objectid import ObjectId

@app.route("/customer/<customer_id>", methods=["GET", "POST"])
def supplier_details(customer_id):
    supplier = suppliers_collection.find_one({"_id": ObjectId(customer_id)})
    
    search = request.args.get("search", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    transaction_type = request.args.get("transaction_type", "all")

    query = {"customer_id": customer_id}

    # Filter by description
    if search:
        query["description"] = {"$regex": search, "$options": "i"}

    # Filter by date range (string comparison)
    if start_date and end_date:
        try:
            # Ensure dates are in the correct format (YYYY-MM-DD)
            datetime.strptime(start_date, "%Y-%m-%d")  # Validate format
            datetime.strptime(end_date, "%Y-%m-%d")    # Validate format
            
            query["date"] = {"$gte": start_date, "$lte": end_date}
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "error")

    # Filter by transaction type
    if transaction_type == "credit":
        query["credit"] = {"$gt": 0}
    elif transaction_type == "debit":
        query["debit"] = {"$gt": 0}

    transactions = list(transactions_collection.find(query))

    total_credit = sum(t.get("credit", 0) for t in transactions)
    total_debit = sum(t.get("debit", 0) for t in transactions)
    remaining_balance = total_credit - total_debit

    today_date = datetime.today()

    return render_template(
        "supplier.html",
        supplier=supplier,
        transactions=transactions,
        search=search,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
        total_credit=total_credit,
        total_debit=total_debit,
        remaining_balance=remaining_balance,
        today_date=today_date,
    )





from datetime import datetime
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from bson.objectid import ObjectId

@app.route("/customer/<customer_id>/add_transaction", methods=["POST", "GET"])
def add_transaction(customer_id):
    # Get today's date as a datetime object
    today_date = datetime.today()

    if request.method == "POST":
        description = request.form.get("description")
        credit = float(request.form.get("credit", 0))
        debit = float(request.form.get("debit", 0))
        
        # Use provided date or default to today's date
        date = request.form.get("date") or today_date

        transaction = {
            "customer_id": customer_id,
            "description": description,
            "credit": credit,
            "debit": debit,
            "date": date
        }

        # Insert the transaction into the database
        transactions_collection.insert_one(transaction)

        # Update the supplier's balance
        suppliers_collection.update_one(
            {"_id": ObjectId(customer_id)},
            {"$inc": {"balance": credit - debit}}  # Increment balance by credit and subtract debit
        )

        flash("Transaction added successfully!", "success")
        return redirect(url_for("supplier_details", customer_id=customer_id))
    
    # Ensure to pass 'today_date' to the template
    return render_template("supplier_details.html", today_date=today_date, customer_id=customer_id)




@app.route("/transaction/edit/<transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id):
    # Fetch the transaction from the database
    transaction = transactions_collection.find_one({"_id": ObjectId(transaction_id)})

    if not transaction:
        flash("Transaction not found!", "error")
        return redirect(url_for("some_route"))  # Replace with your default route

    if request.method == "POST":
        # Get the updated values from the form
        updated_date = request.form.get("date")
        updated_description = request.form.get("description")
        updated_credit = request.form.get("credit", 0)
        updated_debit = request.form.get("debit", 0)

        # Validate and update fields
        try:
            # Validate date
            datetime.strptime(updated_date, "%Y-%m-%d")  # Ensure date format is correct

            # Update the transaction in the database
            transactions_collection.update_one(
                {"_id": ObjectId(transaction_id)},
                {
                    "$set": {
                        "date": updated_date,
                        "description": updated_description,
                        "credit": float(updated_credit),
                        "debit": float(updated_debit),
                    }
                }
            )

            flash("Transaction updated successfully!", "success")
            return redirect(url_for("supplier_details", customer_id=transaction["customer_id"]))
        except ValueError:
            flash("Invalid input! Ensure all fields are filled correctly.", "error")

    # Render the edit form with the existing transaction details
    return render_template("edit_transaction.html", transaction=transaction)


@app.route("/transaction/delete/<transaction_id>", methods=["GET"])
def delete_transaction(transaction_id):
    transaction = transactions_collection.find_one({"_id": ObjectId(transaction_id)})
    supplier_id = transaction["customer_id"]

    # Update the supplier balance
    suppliers_collection.update_one(
        {"_id": ObjectId(supplier_id)},
        {"$inc": {"balance": -(transaction["credit"] - transaction["debit"])}}
    )

    # Delete the transaction
    transactions_collection.delete_one({"_id": ObjectId(transaction_id)})

    flash("Transaction deleted successfully!", "success")
    return redirect(url_for("supplier_details", customer_id=supplier_id))



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
