from datetime import datetime
from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, g
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from help import login_required

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///luxent.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.before_request
def load_user():
    """ Load user-specific info"""
    g.is_admin = False
    g.is_customer = False

    #Check if user is admin or customer
    if session.get("user_id"):
        user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        if not user:
            session.clear()
            return redirect("/login")

        admin = db.execute("SELECT * FROM admins WHERE user_id = ?", session["user_id"])
        if admin:
            g.is_admin = True

        customer = db.execute("SELECT * FROM customers WHERE user_id = ?", session["user_id"])
        if customer:
            g.is_customer = True


#Routes for customer

@app.route("/")
def index():
    #Check if the user is logged
    user_id = session.get("user_id")

    #If it's logged in, it's going to have a custom navbar depending on it's role
    if user_id:
        rows = db.execute("SELECT * FROM users WHERE id = ?", user_id)
        is_admin = rows[0]["id"]
        return render_template("index.html", is_admin=is_admin)
    #If it's noy it'd going to render as guest
    else:
        return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    #Clear the session
    session.clear()

    if request.method == "POST":
        #Get the data from the user
        username = request.form.get("username")
        password = request.form.get("password")

        # Query user data
        user = db.execute("SELECT * FROM users WHERE username = ?", username)

        #Check if username and passwords match
        if len(user) != 1 or not check_password_hash(user[0]["password"], password):
            return render_template("sorry.html", message="Inavlid username or password")

        # Set session for the logged-in user
        session["user_id"] = user[0]["id"]

        # Check if user is admin
        admin = db.execute("SELECT * FROM admins WHERE user_id = ?", user[0]["id"])
        if len(admin) > 0:
            return redirect("/all_reservations")

        # Check if user is a customer
        customer = db.execute("SELECT * FROM customers WHERE user_id = ?", user[0]["id"])
        if len(customer) > 0:
            return redirect("/")

    else:
        #If it's not logged in render the form
        return render_template("login.html")

@app.route("/logout")
def logout():
    #Log out the user
    session.clear()
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        #Check if the user provided a first name
        first_name = request.form.get("first_name")
        if not first_name:
            return render_template("sorry.html", message="Provide a first name")

        #Check if the user provided a last name
        last_name =  request.form.get("last_name")
        if not last_name:
            return render_template("sorry.html", message="Provide a last name")

        #Check if the user provided an email
        email = request.form.get("email")
        if not email:
            return render_template("sorry.html", message="Provide an email")

        #Check if the user provided a username
        username = request.form.get("username")
        if not username:
            return render_template("sorry.html", message="Provide a username")

        #Check if the username is taken
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) > 0:
            return render_template("sorry.html", message="Username already taken")

        #Check if the passwords was provided and are the same
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if not password or not confirm_password or password != confirm_password:
            return render_template("sorry.html", message="Passwords don't match")

        #Hashing the password and insert the data in the database
        hashed_password = generate_password_hash(password)

        #Insert the new user in the users table and customers table
        user = db.execute("INSERT INTO users(username, password) VALUES(?, ?)", username, hashed_password)
        db.execute("INSERT INTO customers(user_id, first_name, last_name, email) VALUES(?, ?, ?, ?)", user, first_name, last_name, email)

        #Log in the user after the insertion
        session["user_id"] = user
        return redirect("/")

    else:
        #Render the form if it's the GET method
        return render_template("register.html")

@app.route("/reservations", methods=["GET", "POST"])
@login_required
def reservations():
    # Fetch options for filtering
    engine_types = db.execute("SELECT engine_type FROM engine")
    colors = db.execute("SELECT color_name FROM color")
    car_types = db.execute("SELECT car_type FROM car_type")

    # Base query
    base_query = """
        SELECT
            v.id,
            v.make,
            v.model,
            e.engine_type AS engine_type,
            c.color_name AS color,
            ct.car_type AS car_type,
            v.year,
            v.price_per_day
        FROM vehicles v
        JOIN engine e ON e.id = v.engine_type_id
        JOIN color c ON c.id = v.color_id
        JOIN car_type ct ON ct.id = v.car_type_id
    """

    where_conditions = []
    parameters = []

    if request.method == "POST":
        # Retrieve selected filters
        selected_engine_types = request.form.getlist("engine_type[]")
        selected_colors = request.form.getlist("color[]")
        selected_car_types = request.form.getlist("car_type[]")

        # Add conditions for selected engine types
        if selected_engine_types:
            where_conditions.append(f"e.engine_type IN ({', '.join(['?'] * len(selected_engine_types))})")
            parameters.extend(selected_engine_types)

        # Add conditions for selected colors
        if selected_colors:
            where_conditions.append(f"c.color_name IN ({', '.join(['?'] * len(selected_colors))})")
            parameters.extend(selected_colors)

        # Add conditions for selected car types
        if selected_car_types:
            where_conditions.append(f"ct.car_type IN ({', '.join(['?'] * len(selected_car_types))})")
            parameters.extend(selected_car_types)

    # Construct the final query
    if where_conditions:
        base_query += " WHERE " + " AND ".join(where_conditions)

    # Execute the query
    try:
        cars = db.execute(base_query, parameters) if parameters else db.execute(base_query)
    except Exception as e:
        print("Error executing query:", e)
        cars = []

    return render_template("reservations.html", cars=cars, engine_types=engine_types, colors=colors, car_types=car_types)

@app.route("/my_reservations")
@login_required
def my_reservations():
    #Select all the reservations made by the customer
    rows = db.execute("SELECT r.id, r.first_name, r.last_name, r.phone_number, r.vehicle_id, r.start_date, r.end_date, r.reservation_made_date, v.price_per_day FROM reservations r JOIN vehicles v ON r.vehicle_id = v.id WHERE r.user_id = ?", session["user_id"])

    #Creating an empty list
    reservations = []

    #Creating a loop to modify every reservation made by the user
    for row in rows:
        #Check the start and end date
        start_date = datetime.strptime(row["start_date"], "%Y-%m-%d")
        end_date = datetime.strptime(row["end_date"], "%Y-%m-%d")

        #Check how many days is the car rented and the total price
        days = (end_date - start_date).days
        total_price = days * row["price_per_day"]

        #Append all the informations made and querried from the database
        reservations.append({
            "id": row["id"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "phone_number": row["phone_number"],
            "vehicle_id": row["vehicle_id"],
            "reservation_made_date": row["reservation_made_date"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "days": days,
            "total_price": total_price
        })

    #Render the template with all the data
    return render_template("my_reservations.html", reservations=reservations)

@app.route("/make_reservation", methods=["GET", "POST"])
@login_required
def make_reservation():
    if request.method == "POST":
        #Get all the information from the form
        first_name = request.form.get("first_name")
        if not first_name:
            return render_template("sorry.html", message="Enter a first name")

        last_name = request.form.get("last_name")
        if not last_name:
            return render_template("sorry.html", message="Enter a last name")

        phone_number = request.form.get("phone_number")
        if not phone_number:
            return render_template("sorry.html", message="Enter a phone number")

        #Check if the user gave a positive integer
        vehicle_id = request.form.get("vehicle_id")
        if not vehicle_id or int(vehicle_id) <= 0:
            return render_template("sorry.html", message="Enter a positive vehicle ID")

        start_date = request.form.get("start_date")
        if not start_date:
            return render_template("sorry.html", message="Enter a start date")

        end_date = request.form.get("end_date")
        if not end_date:
            return render_template("sorry.html", message="Enter a end date")

        #Check if the vehicle exists in the database
        check_vehicles_id = db.execute("SELECT id FROM vehicles")
        vehicle_ids = [row["id"] for row in check_vehicles_id]
        if int(vehicle_id) not in vehicle_ids:
            return render_template("sorry.html", message="Invalid vehicle id")

        #Check the start date and end date
        check_start_date = datetime.strptime(start_date, "%Y-%m-%d")
        check_end_date = datetime.strptime(end_date, "%Y-%m-%d")
        current_time = datetime.now()

        if check_start_date < current_time:
            return render_template("sorry.html", message="The start date can't be in the past")

        if check_end_date <= check_start_date:
            return render_template("sorry.html", message="The end date can't be in the past or the same as the start")

        #Insert the new reservation in the reservations table
        db.execute("INSERT INTO reservations (user_id, first_name, last_name, phone_number, vehicle_id, start_date, end_date, reservation_made_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", session["user_id"], first_name, last_name, phone_number, vehicle_id, start_date, end_date, current_time)

        return redirect("/")
    else:
        return render_template("make_reservation.html")

#Routes for admin

@app.route("/add_admin", methods=["GET", "POST"])
@login_required
def add_admin():
    if request.method == "POST":
        # Extract form data
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validate input
        if not username or not password or not confirm_password:
            return render_template("sorry.html", message="All fields are required.")

        if password != confirm_password:
            return render_template("sorry.html", message="Passwords do not match.")

        # Check if username exists
        existing_user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if existing_user:
            return render_template("sorry.html", message="Username already exists.")

        # Insert new user
        hashed_password = generate_password_hash(password)
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", username, hashed_password)

        # Retrieve new user's ID directly after the insert
        new_user_id = db.execute("SELECT id FROM users WHERE username = ?", username)
        if not new_user_id:
            return render_template("sorry.html", message="Error creating admin user.")

        user_id = new_user_id[0]["id"]  # Access the ID

        # Insert into admins table
        db.execute("INSERT INTO admins (user_id) VALUES (?)", user_id)

        return redirect("/all_reservations")

    return render_template("add_admin.html")


@app.route("/all_reservations", methods=["GET", "POST"])
@login_required
def all_reservations():
    #Select all of the reservations
    rows = db.execute("SELECT r.id, r.user_id, r.first_name, r.last_name, r.phone_number, r.vehicle_id, r.start_date, r.end_date, r.reservation_made_date, v.price_per_day FROM reservations r JOIN vehicles v ON r.vehicle_id = v.id")

    #Creating an empty list
    reservations = []

    #Looping through every reservation
    for row in rows:

        #Check the date
        start_date = datetime.strptime(row["start_date"], "%Y-%m-%d")
        end_date = datetime.strptime(row["end_date"], "%Y-%m-%d")

        #Check how many days the car is rented and the total price
        days = (end_date - start_date).days
        total_price = days * row["price_per_day"]

        #Append the new data to the list
        reservations.append({
            "id": row["id"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "phone_number": row["phone_number"],
            "vehicle_id": row["vehicle_id"],
            "reservation_made_date": row["reservation_made_date"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "days": days,
            "total_price": total_price
        })

    return render_template("all_reservations.html", reservations=reservations)

@app.route("/remove", methods=["GET", "POST"])
@login_required
def remove():
    if request.method == "POST":
        #Get the ID that needs to be removed
        remove_reservation = request.form.get("remove_reservation")
        remove_car = request.form.get("remove_car")
        remove_contract = request.form.get("remove_contract")

        #Check if the user put at least one input
        if not remove_car and not remove_contract and not remove_reservation:
            return render_template("sorry.html", message="Enter a valid data.")

        #Removing the reservation
        if not remove_car and not remove_contract:
            #Check if the user gave a valid input
            if not int(remove_reservation):
                return render_template("sorry.html", message="Enter a positive number")

            #Check if the ID exist
            check_reservation_id = db.execute("SELECT id FROM reservations")
            reservation_ids = [row["id"] for row in check_reservation_id]
            if int(remove_reservation) not in reservation_ids:
                return render_template("sorry.html", message="Invalid reservation ID")

            db.execute("DELETE FROM reservations WHERE id = ?", remove_reservation)
            return redirect("/all_reservations")

        #Removing a vehicle
        if not remove_reservation and not remove_contract:
            #Check if the user gave a valid input
            if not int(remove_car):
                return render_template("sorry.html", message="Enter a positive number")

            #Check if the ID exist
            check_vehicles_id = db.execute("SELECT id FROM vehicles")
            vehicle_ids = [row["id"] for row in check_vehicles_id]
            if int(remove_car) not in vehicle_ids:
                return render_template("sorry.html", message="Invalid vehicle ID")

            db.execute("DELETE FROM vehicles WHERE id = ?", remove_car)
            return redirect("/cars")

        #Removing a contract
        if not remove_reservation and not remove_car:
            #Check if the user gave a valid input
            if not int(remove_contract):
                return render_template("sorry.html", message="Enter a positive number")

            #Check if the ID exist
            check_contract_id = db.execute("SELECT id FROM contracts")
            contract_ids = [row["id"] for row in check_contract_id]
            if int(remove_contract) not in contract_ids:
                return render_template("sorry.html", message="Invalid contract ID")

            db.execute("DELETE FROM contracts WHERE id = ?", remove_contract)
            return redirect("/contracts")
    else:
        return render_template("remove.html")

@app.route("/adding_car", methods=["GET", "POST"])
@login_required
def adding_car():
    if request.method == "POST":
        #Check the user input, if the numbers are positive and it's valadity
        make = request.form.get("make")
        if not make:
            return render_template("sorry.html", message="Enter a make.")

        model = request.form.get("model")
        if not model:
            return render_template("sorry.html", message="Enter a model.")

        #Check the engine ID
        engine_type_id = request.form.get("engine_type_id")
        if not engine_type_id or int(engine_type_id) <= 0:
            return render_template("sorry.html", message="Enter a positive engine ID.")

        check_engine_type_id = db.execute("SELECT id FROM engine")
        engine_ids = [row["id"] for row in check_engine_type_id]
        if int(engine_type_id) not in engine_ids:
            return render_template("sorry.html", message="Invalid engine ID")

        #Check the color ID
        color_id = request.form.get("color_id")
        if not color_id or int(color_id) <= 0:
            return render_template("sorry.html", message="Enter a positive color ID.")

        check_color_id = db.execute("SELECT id FROM color")
        color_ids = [row["id"] for row in check_color_id]
        if int(color_id) not in color_ids:
            return render_template("sorry.html", message="Invalid color ID")

        #Check the car type ID
        car_type_id = request.form.get("car_type_id")
        if not car_type_id or int(car_type_id) <= 0:
            return render_template("sorry.html", message="Enter a positive car type ID.")

        check_car_type_id = db.execute("SELECT id FROM car_type")
        car_type_ids = [row["id"] for row in check_car_type_id]
        if int(car_type_id) not in car_type_ids:
            return render_template("sorry.html", message="Invalid car type ID")

        #Check the year
        year = request.form.get("year")
        if not year or int(year) <= 1950:
            return render_template("sorry.html", message="Enter a positive year.")

        insurance_expiration_date = request.form.get("insurance_expiration_date")
        if not insurance_expiration_date:
            return render_template("sorry.html", message="Enter a insurance expiration date.")

        maintenance_need_date = request.form.get("maintenance_need_date")
        if not maintenance_need_date:
            return render_template("sorry.html", message="Enter a maintenance need date.")

        price_per_day = request.form.get("price_per_day")
        if not price_per_day:
            return render_template("sorry.html", message="Enter a price per day.")

        accidents = request.form.get("accidents")
        if not accidents:
            return render_template("sorry.html", message="Enter if it has an accident or not.")

        #Check if the dates are valid
        check_insurance_date = datetime.strptime(insurance_expiration_date, "%Y-%m-%d")
        check_maintenance_date = datetime.strptime(maintenance_need_date, "%Y-%m-%d")
        current_time = datetime.now()

        if check_insurance_date < current_time:
            return render_template("sorry.html", message="The insurance date can't be in the past")

        if check_maintenance_date <= current_time:
            return render_template("sorry.html", message="The maintenance date can't be the in the past")

        #Insert into vehicles
        db.execute("INSERT INTO vehicles (make, model, engine_type_id, color_id, car_type_id, year, insurance_expiration_date, maintenance_need_date, price_per_day, accidents) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", make, model, engine_type_id, color_id, car_type_id, year, insurance_expiration_date, maintenance_need_date, price_per_day, accidents)

        return redirect("/cars")
    else:
        return render_template("adding_car.html")

@app.route("/change_details", methods=["GET", "POST"])
@login_required
def change_details():
    if request.method == "POST":
        #Get the user input
        car_id = request.form.get("car_id")
        insurance_expiration_date = request.form.get("insurance_expiration_date")
        maintenance_need_date = request.form.get("maintenance_need_date")
        price_per_day = request.form.get("price_per_day")
        accidents = request.form.get("accidents")
        current_time = datetime.now()

        #Check if the user provided anything
        if not insurance_expiration_date and not price_per_day and not maintenance_need_date and not accidents:
            return render_template("sorry.html", message="Enter valid data.")

        #Check if the car is positive integer
        if not car_id or int(car_id) <= 0:
            return render_template("sorry.html", message="Enter a positive car ID.")

        #Check if the vehicle exists
        check_vehicles_id = db.execute("SELECT id FROM vehicles")
        vehicle_ids = [row["id"] for row in check_vehicles_id]
        if int(car_id) not in vehicle_ids:
            return render_template("sorry.html", message="Invalid vehicle id")

        #Update the insurance date
        if not maintenance_need_date and not price_per_day and not accidents:
            #Check if the insurance is valid
            check_insurance_date = datetime.strptime(insurance_expiration_date, "%Y-%m-%d")
            if check_insurance_date <= current_time:
                return render_template("sorry.html", message="The insurance date can't be in the past")

            db.execute("UPDATE vehicles SET insurance_expiration_date = ? WHERE id = ?", insurance_expiration_date, car_id)
            return redirect("/cars")

        #Update the maintenance date
        if not insurance_expiration_date and not price_per_day and not accidents:
            #Check if the maintenance is valid
            check_maintenance_date = datetime.strptime(maintenance_need_date, "%Y-%m-%d")
            if check_maintenance_date <= current_time:
                return render_template("sorry.html", message="The maintenance date can't be the in the past")

            db.execute("UPDATE vehicles SET maintenance_need_date = ? WHERE id = ?", maintenance_need_date, car_id)
            return redirect("/cars")

        #Update the price per day
        if not insurance_expiration_date and not maintenance_need_date and not accidents:
            #Check if the price is valid
            if int(price_per_day) <= 0:
                return render_template("sorry.html", message="The price can't be negative")

            db.execute("UPDATE vehicles SET price_per_day = ? WHERE id = ?", price_per_day, car_id)
            return redirect("/cars")

        if not insurance_expiration_date and not price_per_day and not maintenance_need_date:
            db.execute("UPDATE vehicles SET accidents = ? WHERE id = ?", accidents, car_id)
            return redirect("/cars")

    else:
        return render_template("change_details.html")

@app.route("/cars", methods=["GET", "POST"])
@login_required
def cars():
    #See all the vehicles
    cars = db.execute("SELECT * FROM vehicles")
    return render_template("cars.html", cars=cars)

@app.route("/contracts")
@login_required
def contracts():
    #Select all the contracts
    rows = db.execute("SELECT * FROM contracts")

    #Created an empty list
    contracts = []

    #Looping all the contracts
    for row in rows:

        #Check the date
        start_date = datetime.strptime(row["start_date"], "%Y-%m-%d")
        end_date = datetime.strptime(row["end_date"], "%Y-%m-%d")

        #See how many days the car is rented and the total price of it
        days = (end_date - start_date).days
        total_price = days * row["price_per_day"]

        #Append in the list the data
        contracts.append({
            "id": row["id"],
            "contract_number": row["contract_number"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "phone_number": row["phone_number"],
            "vehicle_id": row["vehicle_id"],
            "contract_made_date": row["contract_made_date"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "price_per_day": row["price_per_day"],
            "days": days,
            "total_price": total_price
        })
    return render_template("contracts.html", contracts=contracts)

@app.route("/adding_contract", methods=["GET", "POST"])
@login_required
def adding_contract():
    if request.method == "POST":
        #Gather and check the data if it's valid and all numbers are positive
        contract_number = request.form.get("contract_number")
        if not contract_number or int(contract_number) <= 0:
            return render_template("sorry.html", message="Enter a positive contract number")

        first_name = request.form.get("first_name")
        if not first_name:
            return render_template("sorry.html", message="Enter a first name")

        last_name = request.form.get("last_name")
        if not last_name:
            return render_template("sorry.html", message="Enter a last name")

        phone_number = request.form.get("phone_number")
        if not phone_number:
            return render_template("sorry.html", message="Enter a phone number")

        vehicle_id = request.form.get("car_id")
        if not vehicle_id or int(vehicle_id) <= 0:
            return render_template("sorry.html", message="Enter a positive vehicle ID")

        start_date = request.form.get("start_date")
        if not start_date:
            return render_template("sorry.html", message="Enter a start date")

        end_date = request.form.get("end_date")
        if not end_date:
            return render_template("sorry.html", message="Enter a end date")

        price_per_day = request.form.get("price_per_day")
        if not price_per_day or int(price_per_day) <= 0:
            return render_template("sorry.html", message="Enter price per day")

        #Check if the vehicle ID exist
        check_vehicles_id = db.execute("SELECT id FROM vehicles")
        vehicle_ids = [row["id"] for row in check_vehicles_id]
        if int(vehicle_id) not in vehicle_ids:
            return render_template("sorry.html", message="Invalid vehicle id")

        #Check if the date it's valid
        check_start_date = datetime.strptime(start_date, "%Y-%m-%d")
        check_end_date = datetime.strptime(end_date, "%Y-%m-%d")
        current_time = datetime.now()

        if check_start_date < current_time:
            return render_template("sorry.html", message="The start date can't be in the past")

        if check_end_date <= check_start_date:
            return render_template("sorry.html", message="The end date can't be in the past or the same as the start")

        #Insert into the contracts table
        db.execute("INSERT INTO contracts (contract_number, first_name, last_name, phone_number, vehicle_id, start_date, end_date, contract_made_date, price_per_day) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", contract_number, first_name, last_name, phone_number, int(vehicle_id), start_date, end_date, current_time, price_per_day)

        return redirect("/contracts")
    else:
        return render_template("adding_contract.html")

#Both users

@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        #Check if the user provided the data
        username = request.form.get("username")
        if not username:
            return render_template("sorry.html", message="Provide a username")

        #Check if the user exist
        check_username = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(check_username) != 1:
            return render_template("sorry.html", message="Username doesn't exist")

        password = request.form.get("new_password")
        if not password:
            return render_template("sorry.html", message="Provide a new password")

        confirm_password = request.form.get("confirm_password")
        if not confirm_password:
            return render_template("sorry.html", message="Provide the same password")

        #Check if the passwords match
        if password != confirm_password:
            return render_template("sorry.html", message="Passwords don't match")

        #Update the password
        db.execute("UPDATE users SET password = ? WHERE username = ?", generate_password_hash(password), username)

        return redirect("/")
    else:
        return render_template("change_password.html")

@app.route("/about_us", methods=["GET", "POST"])
def about():
    return render_template("about_us.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

if __name__ == "__main__":
    app.run(debug=True)