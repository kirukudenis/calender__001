#import Flask and modules
from flask import Flask, redirect, url_for, render_template, request, session, flash,jsonify
from datetime import timedelta, datetime
#import SQLAlchemy for databases
from flask_sqlalchemy import SQLAlchemy 
#import Flask-Mail and modules
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, SubmitField, PasswordField, BooleanField, IntegerField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, InputRequired, EqualTo, Length
import os
#calendar 
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
import secrets
from dateutil import parser
from datetime import datetime

#Create instance of web application
app = Flask(__name__)
app.secret_key = "hello"

#Database configuration values
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///database.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

#Configuration values for ReCaptcha
app.config["RECAPTCHA_PUBLIC_KEY"] = "6LcmmXYeAAAAAFSAHZXv51x6XC7ALl4PeLExGRuk"
app.config["RECAPTCHA_PRIVATE_KEY"] = "6LcmmXYeAAAAAAU-5MJmS6_3NcbggTARR4pGNLGJ"

#Configuration values for flask mail
app.config["DEBUG"] = True
#mail server (GMail)
app.config["MAIL_SERVER"]= "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
#allows for encrypted emails via mail server
app.config["MAIL_USE_SSL"]= True
#set email sender
app.config["MAIL_DEFAULT_SENDER"]= "ruqayahrahimnea2020@gmail.com"
app.config["MAIL_USERNAME"] ="ruqayahrahimnea2020@gmail.com"
app.config["MAIL_PASSWORD"] = "Password_432"

#instantiate mail app
mail = Mail(app)

#Initalise database
db = SQLAlchemy(app)


# initialize marshmallow 
# requiered for Javascript to intract  
# Python in JSON format
ma = Marshmallow(app)

#Create database model for stock
class Stock(db.Model):
	__tablename__ = 'stock'
	itemId = db.Column(db.Integer, primary_key=True)
	itemName = db.Column(db.String(50), nullable=False)
	quantity = db.Column(db.Integer, default=0)


#Create database model for users
class Users(db.Model):
	#Create primary key
	userId = db.Column(db.Integer, primary_key = True)
	username = db.Column(db.String(50), nullable=False, unique=True)
	#Create password field
	password_hash = db.Column(db.String(128))

	@property
	def password(self):
		raise AttributeError ("Password is not valid")

	@password.setter
	def password(self,password):
		#generate password hash from user input
		self.password_hash = generate_password_hash(password)

	#function to check password matches up with hash
	def verify_password(self,password):
		return check_password_hash(self.password_hash,password)

#Create a form class for requesting a quote
class ContactForm(FlaskForm):
	#create fields with validators
	name = StringField('Name', validators=[InputRequired()])
	email = StringField('Email',validators=[InputRequired()])
	phone = IntegerField ("Phone",validators=[InputRequired()])
	address = StringField ("Address",validators=[InputRequired()])
	userMessage = TextAreaField ("Message",validators=[InputRequired()])
	#Add recaptcha field
	recaptcha = RecaptchaField()

#Create a form class for booking details
class BookingForm(FlaskForm):
	#create fields with validators 
	firstname = StringField('First Name', validators=[InputRequired()])
	surname = StringField('Surname', validators=[InputRequired()])
	email = StringField('Email',validators=[InputRequired()])
	phone = IntegerField ("Phone",validators=[InputRequired()])
	address = StringField ("Address",validators=[InputRequired()])
	userMessage = TextAreaField ("Message",validators=[InputRequired()])

#Create a form class for users
class UserForm(FlaskForm):
	username = StringField ("Username", validators = [DataRequired()])
	password_hash = PasswordField ("Password", validators = [DataRequired(), EqualTo("password_hash2",message ="Passwords must match!")])
	password_hash2 = PasswordField("Confirm Password", validators=[DataRequired()])
	submit = SubmitField("Submit")

# Form to add a valid date to the backend
class CalenderEventForm(FlaskForm):
    date = StringField("Date", validators=[DataRequired()])
    submit = SubmitField("Creating appointment")

# Service model with the assumption there are services the 
# a use can book for severeal services 
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    date_added = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, name):
        self.name = name

# the classSchema class specifies the data that will be return in the
# json format 
"""JSON format 
{
    id : 1,
    name : Service_Am
    date_added : 2022-02-14 07:56:00.477704
 }
"""
class ServiceSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "date_added")



# appointment schema 
# service name used as the foreign key 
# appointement date and time used to track appointment 

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.ForeignKey("service.name"), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    attended = db.Column(db.Boolean, nullable=False, default=False)
    date_added = db.Column(db.DateTime, default=datetime.now)
    date_closed = db.Column(db.DateTime, nullable=True, default=None)

    def __init__(self, service, appointment_date, appointment_time):
        self.service = service
        self.appointment_time = appointment_time
        self.appointment_date = appointment_date

# JSON schema
# required jor javascript
class AppointMentSchema(ma.Schema):
    class Meta:
        fields = (
            "id", "service", "appointment_date", "appointment_time", "attended", "date_added", "date_closed")
#section end 3

appointment_schema = AppointMentSchema()
appointments_schema = AppointMentSchema(many=True)

# comment section 5
# function to get all the available time slots 
# slots that have not been booked 

def get_time_slots(date):
    dates = available_slots(date)
    return dates

# getting the appointments that have been made 
def booked_slots(date):
    taken = Appointment.query.filter_by(appointment_date=parse_date(date)).all()
    return taken

# getting the appoiments dates that have noot been booked yet 
# the times are from 08:00 till 18:00 
# dymanically generated
def available_slots(date):
    plains = [{"slot": x, "status": "available"} for x in range(8, 18)]
    not_available = booked_slots(date)
    for index, plain in enumerate(plains):
        for nots in not_available:
            if int(nots.appointment_time.strftime("%H")) == int(plain["slot"]):
                plains[index]["status"] = "not_available"
    return plains


def add_service(name):
    service = Service(name)
    db.session.add(service)
    db.session.commit()
	
# parse a string to datetime then print it back to string 
def parse_date(date):
    return parser.parse(parser.parse(f"{date}").strftime("%m-%d-%Y"))


# create appointment function 
# takes a user ... service  ... date[day] -> 23/02/2022 and slot[time] -> 17K00 time is parsed in the format_parse_time to 17:00
def create_appointment(user, service, date_, slot):
    splits = slot.split('_')
    date = parse_date(datetime.now()) if date_ == "init" else parse_date(date_)
    time = format_parse_time(splits[0])
    check = Appointment.query.filter_by(appointment_date=date).filter_by(appointment_time=time).first()
    # adding an appointment
    if not check:
        appoint = Appointment(user, "Management", date, time)
        db.session.add(appoint)
        db.session.commit()
        final = appointment_schema.dump(appoint)
    else:
        final = {
            "msg": None
        }
    return final


# format time 
# time is splitted at the "K" character and joined with the ":" character
# time format is "08K45"
def format_parse_time(time):
    return parser.parse(":".join(time.split("k"))).time()
#end section 5
def user_exists(username):
    return User.query.filter_by(username=username).first()



# comment section 6
# create appointment form 
@app.route("/appointment/make")
def appointment():
    form = CalenderEventForm()
    return render_template("appointment.html", form=form)

# endpoint to view all the appointments made 
@app.route("/appointment/view", methods=["POST", "GET"])
def mobile():
    return render_template("appointment_view.html")



# format date appoinment endpoint 
# a date string is passed "date_"
# the use for the date clicked by the user on the calender
@app.route("/format/date", methods=["POST"])
def format_date():
    date_ = request.json["date_"]
    parsed = parser.parse(f"{date_}").strftime("%A, %-d %B %Y")
    return jsonify({"date": parsed, "slots": get_time_slots(date_)})


# get all appontments that have been made.
@app.route("/appointment/get",methods=["POST"])
def get_appointments():
    date = request.json["date_"]
    return jsonify(appointments_schema.dump(booked_slots(date)))


# get all available appointment slots 
# in JSON format 
@app.route("/get/slots", methods=["POST"])
def get_slots():
    date_ = request.json["date_"]
    return jsonify(get_time_slots(date_))

# create appointment in a json format
# the date,user,and service and slot are required
# data should be passed in the JSON format
@app.route("/appointment/create", methods=["POST"])
def appointment_create():
    date_ = request.json["date"]
    slot_ = request.json["slot"]
    # user = request.json["user"]
    # service = request.json["service"]
    user = User.query.first().username
    service = Service.query.first().name if Service.query.first() else add_service("Manage")
    return jsonify(create_appointment(user, service, date_, slot_))

#end section 6


#Define path for home page
@app.route("/")
@app.route("/home")
#Define home page
def home():
    return render_template("home.html")


@app.route("/contact", methods=["GET","POST"])
#Define contact us page
def contact():
	#Instantiate form
	form = ContactForm()
	#Check if form has been submitted
	if form.validate_on_submit():
		#Create email message
		msg = Message("Hello",recipients=["ruqayahrahimnea2020@gmail.com"])
		#Send email
		mail.send(msg)
		#Return message to user
		return "Your message has been sent!"
	return render_template("contact.html", form=form )


@app.route("/login")
#Define login page
def login():
    return render_template("login.html")

@app.route("/booking", methods=["GET","POST"])
#Define booking page
def booking():
	#Instantiate form
	form = BookingForm()
	#Check if form has been submitted
	if form.validate_on_submit():
		return redirect(url_for("appointment"))
        
	return render_template("booking.html", form=form)

@app.route("/admin")
#Define admin page
def adminpage():
    return render_template("adminbase.html")


@app.route("/invoices")
#Define invoice page
def invoices():
    return render_template("invoices.html")

@app.route("/stocktake", methods=["POST","GET"])
#Define stocktake page
def stocktake():
    return render_template("stocktake.html")

#path for add user page
@app.route('/user/add', methods = ['GET','POST'])


# adding user funciton to add a sample user ... 
def add_user():
	#set form to UserForm
	form = UserForm()
	if form.validate_on_submit():
		#query database for any users with username entered
		user=Users.query.filter_by(username=form.username.data).first()
		#if nothing returned
		if user is None:
			#add user to database
			user = Users(username=form.username.data, password_hash=form.password_hash.data)
			db.session.add(user)
			db.session.commit()
			#clear form
			form.username.data = ''
			form.password_hash.data=''
		flash("user added")
	return render_template('add_user.html', form=form)


if __name__ == "__main__":
	db.create_all()
	app.run(debug=True)

