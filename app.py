from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from datetime import datetime

from bson import ObjectId

app = Flask(__name__)
app.secret_key = "your_secret_key"

# MongoDB Connection

client = MongoClient('mongodb+srv://ChiragRohada:s54icYoW4045LhAW@atlascluster.t7vxr4g.mongodb.net/test')
db = client["supplier_db"]
suppliers_collection = db["suppliers"]
transactions_collection = db["transactions"]

# Homepage: List of all suppliers
@app.route("/", methods=["GET"])
def home():
    search = request.args.get("search", "")
    filter_balance = request.args.get("filter_balance", "all")
    today_date = datetime.today().strftime("%Y-%m-%d")  # Get today's date in string format

    query = {}
    if search:
        query["supplier_name"] = {"$regex": search, "$options": "i"}

    # Fetch all suppliers matching the query
    suppliers = list(suppliers_collection.find(query))
    total_balance = 0

    # Calculate remaining balance for each supplier
    for supplier in suppliers:
        supplier_id = str(supplier["_id"])
        transactions = list(transactions_collection.find({"customer_id": supplier_id}))

        total_credit = sum(t.get("credit", 0) for t in transactions)
        total_debit = sum(t.get("debit", 0) for t in transactions)
        remaining_balance = total_credit - total_debit

        supplier["balance"] = remaining_balance
        total_balance += remaining_balance  # Sum up balance

    # Filter by balance if requested
    if filter_balance == "pending":
        suppliers = [s for s in suppliers if s["balance"] > 0]
    elif filter_balance == "settled":
        suppliers = [s for s in suppliers if s["balance"] == 0]

    # Fetch today's credit and debit transactions
    
    today = datetime.today().strftime("%Y-%m-%d")
# Fetch today's credit and debit transactions
    from bson import ObjectId

    # Fetch today's credit transactions
    todays_credit = list(transactions_collection.aggregate([
        {"$match": {"date": today, "credit": {"$gt": 0}}},
        {"$addFields": {"customer_id": {"$toObjectId": "$customer_id"}}},  # Convert customer_id to ObjectId
        {"$lookup": {
            "from": "suppliers",
            "localField": "customer_id",
            "foreignField": "_id",
            "as": "supplier_info"
        }},
        {"$unwind": "$supplier_info"}  # Flatten the supplier info
    ]))

    # Fetch today's debit transactions
    todays_debit = list(transactions_collection.aggregate([
        {"$match": {"date": today, "debit": {"$gt": 0}}},
        {"$addFields": {"customer_id": {"$toObjectId": "$customer_id"}}},  # Convert customer_id to ObjectId
        {"$lookup": {
            "from": "suppliers",
            "localField": "customer_id",
            "foreignField": "_id",
            "as": "supplier_info"
        }},
        {"$unwind": "$supplier_info"}  # Flatten the supplier info
    ]))

    # Debug print to ensure the data is loaded properly
  
    total_today_credit = sum(t.get("credit", 0) for t in todays_credit)
    total_today_debit = sum(t.get("debit", 0) for t in todays_debit)

    # Calculate overall credit and debit
    overall_credit = sum(t.get("credit", 0) for t in transactions_collection.find({}))
    overall_debit = sum(t.get("debit", 0) for t in transactions_collection.find({}))


    return render_template(
        "home.html",
        suppliers=suppliers,
        search=search,
        filter_balance=filter_balance,
        total_balance=total_balance,
        today_date=datetime.today(),
        todays_credit=todays_credit, 
        todays_debit=todays_debit,
        total_today_credit=total_today_credit,
        total_today_debit=total_today_debit,
        overall_credit=overall_credit,
        overall_debit=overall_debit
    )


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

    transactions = list(transactions_collection.find(query).sort("date", -1))

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



@app.route("/add_transaction", methods=["GET", "POST"])
def add_transaction():
    if request.method == "GET":
        transaction_type = request.args.get("type", "credit")
        search = request.args.get("search", "")
        query = {}
        if search:
            query["supplier_name"] = {"$regex": search, "$options": "i"}
        suppliers = list(suppliers_collection.find(query))
        if transaction_type=="credit":
            return render_template("add_transaction.html", suppliers=suppliers, search=search)
        else:
            return render_template("add_transaction2.html", suppliers=suppliers, search=search)

    if request.method == "POST":
        supplier_id = request.form.get("supplier_id")
        selected_supplier = suppliers_collection.find_one({"_id": ObjectId(supplier_id)})
        transaction_type = request.args.get("type", "credit")

        if transaction_type=="credit":
            return render_template("add_transaction.html", suppliers=[], selected_supplier=selected_supplier)
        else:
            return render_template("add_transaction2.html", suppliers=[], selected_supplier=selected_supplier)

from datetime import datetime

@app.route("/submit_transaction", methods=["POST"])
def submit_transaction():
    supplier_id = request.form.get("supplier_id")
    transaction_type = request.form.get("transaction_type")  # 'credit' or 'debit'
    amount = float(request.form.get("amount"))
    description = request.form.get("description")
    date = request.form.get("date")

    # If no date is provided, use today's date
    if not date:
        date = datetime.today().strftime("%Y-%m-%d")

    # Create the transaction object
    transaction = {
        "customer_id": supplier_id,
        "date": date,
        "credit": amount if transaction_type == "credit" else 0,
        "debit": amount if transaction_type == "debit" else 0,
        "description": description,
    }

    # Insert the transaction into the database
    transactions_collection.insert_one(transaction)

    # Redirect back to home or supplier page
    return redirect(url_for("home"))  # Change this as needed
    
    

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from io import BytesIO
from flask import send_file, url_for

@app.route('/generate_supplier_pdf/<supplier_id>', methods=['GET'])
def generate_supplier_pdf(supplier_id):
    try:
        # Use supplier_id directly as a string
        supplier = db.suppliers.find_one({"_id": ObjectId(supplier_id)})
        if not supplier:
            return "Supplier not found", 404

        supplier_name = supplier.get('supplier_name', 'Unknown Supplier')

        # Get the start of the current month
        current_date = datetime.now()
        start_of_month = datetime(current_date.year, current_date.month, 1).strftime('%Y-%m-%d')
        month_name = current_date.strftime('%B %Y')  # e.g., February 2025

        # Fetch transactions for the ongoing month
        transactions = db.transactions.find({
            "customer_id": supplier_id,  # Match customer_id to supplier _id as a string
            "date": {"$gte": start_of_month}  # Compare string dates
        })

        # Initialize data for PDF
        data = [["Date", "Description", "Debit (₹)", "Credit (₹)", "Running Total (₹)"]]
        running_total = 0
        total_debit = 0
        total_credit = 0
        transaction_found = False

        for transaction in transactions:
            transaction_found = True
            date = transaction.get('date', 'Unknown Date')
            description = transaction.get('description', '-')
            debit = transaction.get('debit', 0.0)
            credit = transaction.get('credit', 0.0)

            # Create a link for the transaction details
            transaction_id = transaction.get('_id')
            transaction_link = url_for('view_transaction_details', transaction_id=str(transaction_id), _external=True)

            # Show only the transaction number in the PDF and make it a clickable link
            transaction_number = f"{transaction_id}"
            description_link = f'<a href="{transaction_link}">{transaction_number}</a>'

            # Update running totals
            running_total += debit - credit
            total_debit += debit
            total_credit += credit

            # Use Paragraph to render HTML for the description with the link
            description_paragraph = Paragraph(description_link, getSampleStyleSheet()['Normal'])

            # Append transaction row with Paragraph for description
            data.append([
                date,
                description_paragraph,  # Paragraph with link
                f"{debit:.2f}",
                f"{credit:.2f}",
                f"{running_total:.2f}"
            ])

        # If no transactions found, add a default message
        if not transaction_found:
            data.append(["No transactions found for this month.", "", "", "", ""])

        # Add totals row
        if transaction_found:
            data.append([
                "",
                "Total",
                f"{total_debit:.2f}",
                f"{total_credit:.2f}",
                ""
            ])

        # Debug: Print the data being passed to the PDF
        print("Data to be included in PDF:", data)

        # Create the PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        # Create a custom stylesheet
        styles = getSampleStyleSheet()
        heading_style = styles['Heading1']
        heading_style.fontName = 'Helvetica-Bold'
        heading_style.fontSize = 16
        heading_style.alignment = 1  # Center alignment

        subheading_style = styles['Heading2']
        subheading_style.fontName = 'Helvetica-Bold'
        subheading_style.fontSize = 14
        subheading_style.alignment = 1  # Center alignment

        # Title Header
        title_header = Paragraph(f"<strong>{supplier_name}</strong> - <em>{month_name}</em>", heading_style)
        subtitle_header = Paragraph("Transaction Report", subheading_style)
        
        # Table Data
        table = Table(data)
        table.setStyle(TableStyle([  
            ('BACKGROUND', (0, 0), (-1, 0), colors.lavender),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),  # Color for the table text
            ('ALIGN', (2, 1), (3, -1), 'RIGHT'),  # Align the Debit and Credit columns to the right
        ]))

        # Elements to add
        elements = [title_header, subtitle_header, table]

        doc.build(elements)

        # Send PDF as response
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{supplier_name}_transactions_{current_date.strftime('%Y_%m')}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/transaction_details/<transaction_id>', methods=['GET'])
def view_transaction_details(transaction_id):
    # Fetch the transaction from the database using the ID
    transaction = db.transactions.find_one({"_id": ObjectId(transaction_id)})
    if not transaction:
        return "Transaction not found", 404

    # Create a detailed view of the transaction (you can customize this)
    transaction_details = f"""
        <h2>Transaction Details</h2>
        <p><strong>Date:</strong> {transaction.get('date', 'Unknown Date')}</p>
        <p><strong>Description:</strong> {transaction.get('description', '-')}</p>
        <p><strong>Debit:</strong> {transaction.get('debit', 0.0)}</p>
        <p><strong>Credit:</strong> {transaction.get('credit', 0.0)}</p>
        <p><strong>Running Total:</strong> {transaction.get('running_total', 0.0)}</p>
    """
    return transaction_details



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
