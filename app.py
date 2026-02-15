import random
from flask import Flask, redirect, render_template, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from config import Config
from sqlalchemy.orm import aliased
from sqlalchemy import Numeric
from datetime import date, datetime, timedelta
import json
#for the login session implementation
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

app = Flask(__name__)
app.secret_key = 'Railway_Project_2024_Secure_Key_!@#'
app.config.from_object(Config)
db = SQLAlchemy(app)



class Train(db.Model):
    __tablename__ = 'train'
    train_no = db.Column(db.Integer, primary_key=True)
    station_order = db.Column(db.Integer, primary_key=True)
    train_name = db.Column(db.String(50))
    train_type = db.Column(db.String(30))
    station_name = db.Column(db.String(50))
    arrival_time = db.Column(db.String(10))
    departure_time = db.Column(db.String(10))
    distance_from_source = db.Column(db.Integer)
    train_fare = db.Column(Numeric(10,2),nullable=True)
    
@app.route('/')
def home_page():
    return render_template('home.html')

@app.route('/search')
def search_page():
    # SECURITY CHECK: If user is not in session, send them to login
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # --- NEW: Fetch dynamic stations from DB ---
    # This replaces the hard-coded list in HTML
    station_query = db.session.query(Train.station_name).distinct().order_by(Train.station_name).all()
    all_stations = [s[0] for s in station_query] # Flatten tuples into a list
    
    # Get search inputs
    src = request.args.get('from')
    dest = request.args.get('to')
    results = []

    if src and dest:
        StartStation = aliased(Train)
        EndStation = aliased(Train)

        results = db.session.query(StartStation, EndStation).join(
            EndStation, StartStation.train_no == EndStation.train_no
        ).filter(
            StartStation.station_name == src, # Exact match is better for dropdowns
            EndStation.station_name == dest,
            StartStation.station_order < EndStation.station_order
        ).all()
    
    return render_template('index.html', 
                           train_data=results, 
                           src=src, 
                           dest=dest, 
                           stations=all_stations)
    
    
@app.route('/book')
def book_ticket():
    train_no = request.args.get('train_no')
    from_stat = request.args.get('from_stat')
    to_stat = request.args.get('to_stat')
    selected_class = request.args.get('train_class', 'General')
    start_date_str = request.args.get('date')

    # FIX: Query the specific row for the departure station to get times
    # We filter by train_no and the station_name the user is starting from
    departure_row = Train.query.filter_by(train_no=train_no, station_name=from_stat).first()
    arrival_row = Train.query.filter_by(train_no=train_no, station_name=to_stat).first()

    arrival_date = start_date_str
    if start_date_str and departure_row and arrival_row:
        try:
            date_obj = datetime.strptime(start_date_str, '%Y-%m-%d')
            # If arrival time is numerically less than departure, it's the next day
            if arrival_row.arrival_time < departure_row.departure_time:
                arrival_date = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
        except ValueError:
            pass

    return render_template('book_ticket.html', 
                           train=departure_row, # Pass departure row for train info
                           arrival_data=arrival_row,
                           src=from_stat, 
                           dest=to_stat, 
                           t_class=selected_class, 
                           start_date=start_date_str,
                           arrival_date=arrival_date)
    
@app.route('/payment', methods=['POST'])
def payment():
    # 1. Capture the hidden inputs sent from book_ticket.html
    train_no = request.form.get('train_no')
    src_name = request.form.get('src_station')
    dest_name = request.form.get('dest_station')
    s_date = request.form.get('start_date')
    a_date = request.form.get('arrival_date')
    t_class = request.form.get('class')
    
    # 2. Parse the passenger JSON string back into a Python list
    passengers_raw = request.form.get('passengers_data')
    try:
        passengers = json.loads(passengers_raw) if passengers_raw else []
    except json.JSONDecodeError:
        passengers = []

    # 3. Database Lookups
    # Fetch details for the DESTINATION station (to get arrival time and fare)
    arrival_info = Train.query.filter_by(
        train_no=train_no, 
        station_name=dest_name
    ).first()
    
    # Fetch details for the SOURCE station (to get departure time)
    departure_info = Train.query.filter_by(
        train_no=train_no, 
        station_name=src_name
    ).first()

    # 4. Fare Calculation
    # We take the fare from the destination station row and multiply by passenger count
    unit_fare = arrival_info.train_fare if arrival_info and arrival_info.train_fare else 0
    total_amount = unit_fare * len(passengers)

    # 5. Send all data to passenger.html
    return render_template('passenger.html', 
                           passengers=passengers, 
                           train=arrival_info,       # Provides train_name, train_no, dest station_name
                           departure_info=departure_info, # Provides source departure_time
                           total=total_amount,
                           src=src_name,
                           dest=dest_name,
                           start_date=s_date,
                           arrival_date=a_date,
                           t_class=t_class)
    
class PassengerRecord(db.Model):
    __tablename__ = 'passenger'
    passenger_id = db.Column(db.String(10), primary_key=True)
    passenger_name = db.Column(db.String(50))
    age = db.Column(db.Integer)
    departure_station = db.Column(db.String(200))
    arrival_station = db.Column(db.String(200))
    departure_time = db.Column(db.String(50))
    arrival_time = db.Column(db.String(50))
    departure_date = db.Column(db.Date)
    arrival_date = db.Column(db.Date)
    train_fare = db.Column(db.Numeric(10, 2))

class Ticket(db.Model):
    __tablename__ = 'ticket'
    ticket_id = db.Column(db.String(10),primary_key = True)
    passenger_id = db.Column(db.String(10))
    train_no = db.Column(db.Integer)
    booking_date = db.Column(db.Date)
    meal_preference = db.Column(db.String(10))
    berth_preference = db.Column(db.String(10))
    booked_by = db.Column(db.Integer)

@app.route('/confirm_payment', methods=['POST'])
def confirm_payment():
    print("--CONFIRM PAYMENT route triggered")
    try:
        # Get Journey Data
        src = request.form.get('src')
        dest = request.form.get('dest')
        dep_time = request.form.get('dep_time') 
        arr_time = request.form.get('arr_time')
        train_no = request.form.get('train_no')
        
        dep_date = datetime.strptime(request.form.get('dep_date'), '%Y-%m-%d').date()
        arr_date = datetime.strptime(request.form.get('arr_date'), '%Y-%m-%d').date()
        
        fare = request.form.get('fare', 0)
        pass_raw = request.form.get('passengers_json')
        passengers = json.loads(pass_raw) if pass_raw else []
        
        if not passengers:
            return jsonify({"success":False,"error":"No passenger found"}),400
        
        first_p_id = None
        # FIX 1: Get count once to avoid ID duplication
        base_count = PassengerRecord.query.count() 
        today = date.today()
        
        for i, p in enumerate(passengers):
            formatted_p_id = f"P{str(base_count + i + 1).zfill(3)}"
            
            if first_p_id is None:
                first_p_id = formatted_p_id
            
            # Save Passenger
            record = PassengerRecord(
                passenger_id=formatted_p_id,
                passenger_name=p['name'],
                age=int(p['age']),
                departure_station=src,
                arrival_station=dest,
                departure_time=dep_time,
                arrival_time=arr_time,
                departure_date=dep_date,
                arrival_date=arr_date,
                train_fare=float(fare) / len(passengers)
            )
            db.session.add(record)

            # Save Ticket
            new_ticket = Ticket(
                ticket_id=f"T{str(random.randint(1000, 9999))}",
                passenger_id=formatted_p_id,
                train_no=int(train_no),
                booking_date=date.today(),
                booked_by=session.get('user_id'), # <--- ADD THIS LINE
                meal_preference=p.get('meal', 'None'),
                berth_preference=p.get('birth', 'None')
                )
            db.session.add(new_ticket)
        
        db.session.commit()
        return jsonify({"success": True, "redirect_url": url_for('show_ticket', p_id=first_p_id)})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/ticket/<p_id>')
def show_ticket(p_id):
    # Join PassengerRecord and Ticket to get all details in one query
    # This fetches the primary passenger you clicked on
    query_result = db.session.query(PassengerRecord, Ticket).join(
        Ticket, PassengerRecord.passenger_id == Ticket.passenger_id
    ).filter(PassengerRecord.passenger_id == p_id).first_or_404()

    # Now fetch ALL passengers booked for this same journey to show on the ticket
    all_results = db.session.query(PassengerRecord, Ticket).join(
        Ticket, PassengerRecord.passenger_id == Ticket.passenger_id
    ).filter(
        PassengerRecord.departure_date == query_result.PassengerRecord.departure_date,
        PassengerRecord.departure_time == query_result.PassengerRecord.departure_time,
        Ticket.train_no == query_result.Ticket.train_no
    ).all()

    # 'main' is the primary passenger for the header
    # 'results' is the list of all passengers for the table
    return render_template('ticket.html', results=all_results, main=query_result.PassengerRecord)


class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True,autoincrement = True)
    full_name = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    dob = db.Column(db.Date)
    gender = db.Column(db.String(1))
    user_name = db.Column(db.String(40), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) # Store hashed passwords
    state = db.Column(db.String(30))
    city = db.Column(db.String(30))
    pincode = db.Column(db.String(10))
    country = db.Column(db.String(30))
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('user_name') #
        password_attempt = request.form.get('password')
        
        # 1. Check if user exists in the database
        user = User.query.filter_by(user_name=username).first()
        
        # 2. Verify hashed password
        if user and check_password_hash(user.password, password_attempt):
            # 3. Store user details in session
            session['user_id'] = user.user_id
            session['user_name'] = user.user_name
            return redirect(url_for('home_page')) # Redirect to home on success
        else:
            return "Invalid login credentials. Please try again."
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get all details from the signup form
        new_user = User(
            full_name=request.form.get('name'),
            email=request.form.get('email'),
            dob=datetime.strptime(request.form.get('dob'), '%Y-%m-%d').date(),
            gender=request.form.get('gender'),
            user_name=request.form.get('username'),
            password=generate_password_hash(request.form.get('password')),
            state=request.form.get('state'),
            city=request.form.get('city'),
            pincode=request.form.get('pincode'),
            country=request.form.get('country')
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear() # Clears the login session
    return redirect(url_for('home_page'))

@app.route('/view_bookings', methods=['GET', 'POST'])
def view_bookings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    results = []
    search_date_str = request.form.get('booking_date') or request.args.get('booking_date')

    if search_date_str:
        target_date = datetime.strptime(search_date_str, '%Y-%m-%d').date()
        
        # We query based on 'booked_by' (Your ID)
        results = db.session.query(Ticket, PassengerRecord, Train).join(
            PassengerRecord, Ticket.passenger_id == PassengerRecord.passenger_id
        ).join(
            Train, Ticket.train_no == Train.train_no
        ).filter(
            Ticket.booked_by == session['user_id'], # <--- Filter by YOUR account
            Ticket.booking_date == target_date,
            Train.station_name == PassengerRecord.departure_station
        ).all()

    return render_template('view_bookings.html', bookings=results, search_date=search_date_str)

with app.app_context():
    db.create_all()
    
if __name__ == '__main__':
    app.run(debug=True)