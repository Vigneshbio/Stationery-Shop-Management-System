from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
import os
from werkzeug.utils import secure_filename
import os
from flask import send_file

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "your_secret_key"  

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="vignesh",
    database="smart_shop"
)
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def home():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template('index.html', products=products)


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    cursor = db.cursor()
    cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user:
        if user[1] == password:
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return "Invalid credentials", 401
    else:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        db.commit()
        session['user_id'] = cursor.lastrowid
        session['username'] = username
        return redirect(url_for('home'))
    
@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    password = request.form['password']

    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username=%s OR email=%s", (username, email))
    existing_user = cursor.fetchone()
    if existing_user:
        return "Username or email already exists!"

    cursor.execute(
        "INSERT INTO users (username, email, phone, address, password) VALUES (%s, %s, %s, %s, %s)",
        (username, email, phone, address, password)
    )
    db.commit()

    session['user_id'] = cursor.lastrowid
    session['username'] = username

    return redirect(url_for('home'))

   
@app.route('/signup.html')
def signup_page():
    return render_template('signin.html')

@app.route('/admin/add-product', methods=['GET', 'POST'])
def add_product():
    if session.get('username') != 'admin':
        return redirect('/login.html')

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form.get('description', '')
        quantity = request.form.get('quantity', 0)

        if 'image' not in request.files or request.files['image'].filename == '':
            return "No image uploaded", 400

        file = request.files['image']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        image_path = f"images/{filename}"

        cursor = db.cursor()
        cursor.execute(""" 
            INSERT INTO products (name, price, description, images, quantity)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, price, description, image_path, quantity))
        db.commit()

        return redirect('/admin/add-product')  

    return render_template('add_product.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    data = request.json
    if not data or not data.get('items'):
        return {'status': 'error', 'message': 'Cart is empty'}, 400

    cursor = db.cursor()
    try:
        for i in data['items']:
            title = i.get('title', 'Unknown Product')
            price = i.get('price', 0)
            quantity = i.get('quantity', 1)
            
            image = i.get('image', '')
            if image.startswith('/static/'):
                image = image[len('/static/'):]

            cursor.execute("""
                INSERT INTO cart_items (user_id, product_name, price, quantity, image_url)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                session['user_id'], 
                title,       
                price, 
                quantity, 
                image     
            ))
        db.commit()
    except Exception as e:
        print("Error:", e)
        return {'status': 'error', 'message': str(e)}, 500
    finally:
        cursor.close()

    return {'status': 'success'}

@app.route("/payment-success", methods=["POST"])
def payment_success():
    if "user_id" not in session:
        return redirect("/login.html")

    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    payment_method = request.form['payment_method']

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cart_items WHERE user_id=%s", (session["user_id"],))
    cart_items = cursor.fetchall()

    if not cart_items:
        return "<h2>No items in cart!</h2>"

    bill_no = "BILL" + str(session["user_id"]) + str(os.urandom(3).hex())
    os.makedirs("invoices", exist_ok=True)
    filename = f"invoices/{bill_no}.pdf"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filename, pagesize=A4)
    story = []

    story.append(Paragraph(f"Invoice - {bill_no}", styles["Title"]))
    story.append(Spacer(1, 20))

   
    data = [["Product", "Quantity", "Unit Price", "Total"]]
    total_amount = 0

  
    for item in cart_items:
        total = item['price'] * item['quantity']
        data.append([item['product_name'], item['quantity'], f"₹{item['price']:.2f}", f"₹{total:.2f}"])
        total_amount += total

   
    data.append(["", "", "Total Amount:", f"₹{total_amount:.2f}"])

   
    table = Table(data, colWidths=[200, 60, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f2f2f2")),  
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,-1), (-2,-1), 'Helvetica-Bold'),  
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#f9f9f9"))
    ]))

    story.append(table)
    story.append(Spacer(1, 20))

    story.append(Paragraph(f"Payment Method: {payment_method}", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Customer Details:", styles["Heading3"]))
    story.append(Paragraph(f"Name: {name}", styles["Normal"]))
    story.append(Paragraph(f"Email: {email}", styles["Normal"]))
    story.append(Paragraph(f"Phone: {phone}", styles["Normal"]))
    story.append(Paragraph(f"Address: {address}", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Thank you for shopping with us!", styles["Normal"]))

    doc.build(story)
    cursor.execute("DELETE FROM cart_items WHERE user_id=%s", (session["user_id"],))
    db.commit()
    cursor.close()

    return f"""
    <h2>Payment Successful!</h2>
    <p>Your invoice is ready: <a href='/download-invoice/{bill_no}'>Download PDF</a></p>
    """


@app.route('/admin/seed-products')
def seed_products():
    if session.get('username') != 'admin':
        return "Unauthorized", 403

    cursor = db.cursor()
    cursor.executemany("""
        INSERT INTO products (name, price, description, images)
        VALUES (%s, %s, %s, %s)
    """, [
        ('Premium Pencil', 45.99, 'High-quality wooden pencil.', 'images/back-school-witch-school-supplies.jpg'),
        ('Sketch Pen', 25.50, 'Colorful sketch pen set.', 'images/back-school-witch-school-supplies.jpg'),
        ('Apsara Pencil', 10.99, 'Smooth writing Apsara pencils.', 'images/apsara.jpg')
    ])
    db.commit()
    return "Seeded products!"
@app.route("/admin/manage-products")
def manage_products():
    if session.get("username") != "admin":
        return redirect("/login.html")
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template("manage.html", products=products)


@app.route("/admin/delete-product/<int:id>")
def delete_product(id):
    if session.get("username") != "admin":
        return redirect("/login.html")
    cursor = db.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (id,))
    db.commit()
    return redirect("/admin/manage-products")


@app.route("/admin/edit-product/<int:id>", methods=["GET", "POST"])
def edit_product(id):
    if session.get("username") != "admin":
        return redirect("/login.html")
    
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id = %s", (id,))
    product = cursor.fetchone()

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        description = request.form["description"]
        quantity = request.form["quantity"]

        if "image" in request.files and request.files["image"].filename != "":
            file = request.files["image"]
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            image_path = f"images/{filename}"

            cursor.execute(
                "UPDATE products SET name=%s, price=%s, description=%s, images=%s, quantity=%s WHERE id=%s",
                (name, price, description, image_path, quantity, id),
            )
        else:
            cursor.execute(
                "UPDATE products SET name=%s, price=%s, description=%s, quantity=%s WHERE id=%s",
                (name, price, description, quantity, id),
            )
        db.commit()
        return redirect("/admin/manage-products")

    return render_template("edit_product.html", product=product)

from flask import send_file

@app.route("/download-invoice/<bill_no>")
def download_invoice(bill_no):
    filename = f"invoices/{bill_no}.pdf"
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    else:
        return "Invoice not found!", 404


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user_id" not in session:
        return redirect("/login.html")

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cart_items WHERE user_id=%s", (session["user_id"],))
    cart_items = cursor.fetchall()

    total = sum(item['price'] * item['quantity'] for item in cart_items)  

    if request.method == "POST":
        return redirect(url_for("payment_success"))

    return render_template("checkout.html", cart_items=cart_items, total=total)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)

@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response
