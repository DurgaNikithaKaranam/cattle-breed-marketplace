from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import joblib
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secrte123"

# ---------------- DATABASE ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Niki@2006",
    database="cattle_db"
)
cursor = db.cursor(dictionary=True)


# ---------------- ML MODEL ----------------
model = joblib.load("ml/breed_model.pkl")
le_purpose = joblib.load("ml/purpose_encoder.pkl")
le_milk = joblib.load("ml/milk_encoder.pkl")
le_breed = joblib.load("ml/breed_encoder.pkl")

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("landing.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
            )
            db.commit()
            return redirect(url_for("login"))
        except mysql.connector.Error:
            return "Username already exists"

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()

        if user:
            session["username"] = username
            return redirect(url_for("dashboard"))

        flash("Invalid credentials")
        return redirect(url_for("login"))

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

# ---------------- BREEDS ----------------
@app.route("/breeds")
def breeds():
    cursor.execute("SELECT * FROM breeds")
    return render_template("breeds.html", breeds=cursor.fetchall())

# ---------------- RECOMMEND ----------------
@app.route("/recommend", methods=["GET", "POST"])
def recommend():
    purpose = request.form.get("purpose")
    result = None

    if request.method == "POST" and purpose:
        if purpose in ["Milk", "Commercial"]:
            milk = request.form.get("milk")
            climate = request.form.get("climate")

            if milk == "High" and climate == "Hot":
                result = "Gir or Sahiwal"
            elif milk == "Medium":
                result = "Red Sindhi"
            else:
                result = "Tharparkar"

        elif purpose == "Breeding":
            disease = request.form.get("disease")
            temperament = request.form.get("temperament")

            if disease == "High" and temperament == "Calm":
                result = "Ongole"
            else:
                result = "Kankrej"

    return render_template("recommend.html", purpose=purpose, result=result)

@app.route("/add_cattle", methods=["GET", "POST"])
def add_cattle():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        owner = session["username"]

        breed = request.form["breed"]
        price = int(request.form["price"])
        quantity = int(request.form["quantity"])
        age = int(request.form["age"])
        gender = request.form["gender"]
        is_pregnant = request.form["is_pregnant"]
        weight = int(request.form["weight"])

        pregnancy_months = request.form.get("pregnancy_months")
        pregnancy_months = int(pregnancy_months) if pregnancy_months else 0

        image = request.files["image"]
        filename = secure_filename(image.filename)

        image_path = f"uploads/{filename}"
        image.save(os.path.join("static", image_path))

        cursor.execute("""
            INSERT INTO cattle
            (owner, breed, price, quantity, age, gender,
             is_pregnant, pregnancy_months, weight, image)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            owner, breed, price, quantity, age,
            gender, is_pregnant, pregnancy_months,
            weight, image_path
        ))

        db.commit()
        return redirect(url_for("marketplace"))

    return render_template("add_cattle.html")


# ---------------- MARKETPLACE ----------------
@app.route("/marketplace")
def marketplace():
    cursor.execute("""
        SELECT id, breed, price, quantity, age, gender,
               is_pregnant, pregnancy_months, weight, image, owner
        FROM cattle
        WHERE quantity > 0
    """)
    cattle = cursor.fetchall()
    return render_template("marketplace.html", cattle=cattle)

# ---------------- BUY ----------------
@app.route("/buy/<int:cattle_id>", methods=["GET", "POST"])
def buy(cattle_id):

    if "username" not in session:
        return redirect(url_for("login"))

    cursor = db.cursor()

    # ---------- GET : SHOW QUANTITY PAGE ----------
    if request.method == "GET":
        cursor.execute("SELECT * FROM cattle WHERE id=%s", (cattle_id,))
        cattle = cursor.fetchone()
        return render_template("buy_quantity.html", cattle=cattle)


    # ---------- POST REQUEST ----------
    form = request.form

    # ---------- STEP 1 : QUANTITY SUBMITTED ----------
    if "quantity" in form and "fullname" not in form:

        quantity = int(form["quantity"])

        cursor.execute("SELECT * FROM cattle WHERE id=%s", (cattle_id,))
        cattle = cursor.fetchone()

        available = cattle[4]   # quantity column index

        # ❌ NOT ENOUGH STOCK
        if quantity > available:
            return render_template(
                "buy_quantity.html",
                cattle=cattle,
                error=f"Only {available} available!"
            )

        # ✔ VALID QUANTITY → SHOW ADDRESS FORM
        return render_template(
            "buy_address.html",
            cattle=cattle,
            quantity=quantity
        )


    # ---------- STEP 2 : ADDRESS SUBMITTED ----------
    buyer = session["username"]

    quantity = int(form["quantity"])
    pincode = form["pincode"]
    city = form["city"]
    state = form["state"]
    house = form["house"]
    area = form["area"]
    fullname = form["fullname"]
    email = form["email"]
    address_type = form["address_type"]

    address = f"""
    {fullname}
    {house}, {area}
    {city}, {state} - {pincode}
    Email: {email}
    Address Type: {address_type}
    """

    # CHECK STOCK AGAIN (important)
    cursor.execute("SELECT quantity FROM cattle WHERE id=%s", (cattle_id,))
    available = cursor.fetchone()[0]

    if quantity > available:
        return "Stock changed. Try again."

    new_qty = available - quantity

    cursor.execute(
        "UPDATE cattle SET quantity=%s WHERE id=%s",
        (new_qty, cattle_id)
    )

    cursor.execute("""
        INSERT INTO orders (cattle_id, buyer, quantity, address)
        VALUES (%s, %s, %s, %s)
    """, (cattle_id, buyer, quantity, address))

    db.commit()

    return redirect(url_for("profile"))


# ---------------- PROFILE ----------------
@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.breed, o.quantity, o.address
        FROM orders o
        JOIN cattle c ON o.cattle_id = c.id
        WHERE o.buyer = %s
        ORDER BY o.id DESC
    """, (session["username"],))

    orders = cursor.fetchall()
    return render_template("profile.html", orders=orders)

@app.route('/vets')
def vets():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM vets")
    vets = cursor.fetchall()
    cursor.close()

    return render_template("vets.html", vets=vets)


# @app.route("/buy/<int:id>")
# def buy(id):
#     return render_template("buy_quantity.html", id=id)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)