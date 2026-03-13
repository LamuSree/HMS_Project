import random
import time
from flask_mail import Mail, Message
from flask_wtf import CSRFProtect

from crypto_utils import encrypt_file, decrypt_file
from flask import send_file, send_from_directory
from flask import Flask, render_template, redirect, url_for, session, flash, request

import psycopg2
import os
import re
import requests

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from forms import RegisterForm, LoginForm
from face_auth.recognize import recognize_user
try:
    from voice_auth.voice_verify import verify_voice
except:
    verify_voice = None
from geopy.distance import geodesic
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# TomTom Configuration
# ================= Location Configuration =================

from geopy.distance import geodesic
import requests   # add this import if not already added

# TomTom API Key
TOMTOM_API_KEY = "VP3wZDKF4knI26YaRvfKMLlaD5QB7RfV"

# Center location (your confirmed Google Maps location)
CENTER_LAT = 12.730709771382946
CENTER_LON = 77.70853588784597

# Allow login within 2 km
ALLOWED_RADIUS = 2


# ================= TOMTOM FUNCTION =================

def get_location_from_tomtom(city):

    url = f"https://api.tomtom.com/search/2/geocode/{city}.json"

    params = {
        "key": TOMTOM_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data["results"]:
        lat = data["results"][0]["position"]["lat"]
        lon = data["results"][0]["position"]["lon"]

        return lat, lon

    return None, None

# Allow login within 2 km
ALLOWED_RADIUS = 2
app = Flask(__name__)
# ================= FILE UPLOAD CONFIG =================
UPLOAD_FOLDER = "static_uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("temp", exist_ok=True)

# ================= SECURITY CONFIGURATION =================
app.config['SECRET_KEY'] = '0c6c30573c34d440afba1582bb08d681be6b4ab52d95c218254ac57c673ce493'
limiter = Limiter(get_remote_address, app=app)

# Secure session cookies
app.config['SESSION_COOKIE_SECURE'] = False   # keep False for localhost testing
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Enable CSRF protection
csrf = CSRFProtect(app)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'hospitalmanagementsystemh@gmail.com'
app.config['MAIL_PASSWORD'] = 'wtru qhqi wprz hdbt'

mail = Mail(app)

app.config['SECRET_KEY'] = '0c6c30573c34d440afba1582bb08d681be6b4ab52d95c218254ac57c673ce493'

# ================= DATABASE ======

def get_db():
    return psycopg2.connect(
        host="localhost",
        database="men_sys",
        user="postgres",
        password="postgres123"
    )

# =====HOME =====

@app.route("/")
def home():
    return render_template("home.html")

# === REGISTER =====

@app.route("/register", methods=["GET","POST"])
def register():

    form = RegisterForm()

    if request.method == "POST":

        # ⭐ FIRST check Flask-WTF validation
        if not form.validate_on_submit():

            # SHOW ALL FORM ERRORS
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{field}: {error}")

            return render_template("register.html", form=form)

        username = form.username.data
        email = form.email.data
        password = form.password.data
        role = form.role.data

        # ---------- USERNAME VALIDATION ----------
        if not re.match(r'^[A-Z][a-zA-Z]{0,49}$', username):
            flash("Username must start with capital letter and contain only letters (max 50)")
            return redirect(url_for("register"))

        # ---------- EMAIL VALIDATION ----------
        if not re.match(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', email):
            flash("Email must be valid Gmail address")
            return redirect(url_for("register"))

        # ---------- PASSWORD VALIDATION ----------
        if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[!@$%^&*_]).{8,}$', password):
            flash("Password must contain uppercase, lowercase, number and special character")
            return redirect(url_for("register"))

        conn = get_db()
        cursor = conn.cursor()

        # ---------- DUPLICATE CHECK ----------
        cursor.execute("""
            SELECT * FROM users
            WHERE username=%s OR email=%s
        """,(username,email))

        if cursor.fetchone():
            flash("Username or Email already exists ❌")
            cursor.close()
            conn.close()
            return redirect(url_for("register"))

        # ---------- SPECIALIZATION ----------
        if role == "Doctor":
            specialization = form.specialization.data
        else:
            specialization = "General"   # avoid NULL if DB requires

        # ---------- HASH PASSWORD ----------
        hashed_password = generate_password_hash(password)

        # ---------- INSERT USER ----------
        cursor.execute("""
            INSERT INTO users(username,email,password,role,specialization,status,login_time,last_login)
            VALUES (%s,%s,%s,%s,%s,'Active',NOW(),NOW())
        """,(username,
             email,
             hashed_password,
             role,
             specialization))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Successfully Registered ✅")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)

# ================= LOGIN =================
# to prevent brute force attacks

@app.route("/login", methods=["GET","POST"])
@limiter.limit("5 per minute")
def login():

    form = LoginForm()

    if request.method == "POST":

        if not form.validate_on_submit():
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{field}: {error}")

            return render_template("login.html", form=form)

        username = form.username.data
        email = form.email.data
        password = form.password.data
        #input validation
        if not re.match(r'^[A-Za-z0-9_]{3,50}$', username):
            flash("Invalid username format")
            return redirect(url_for("login"))

        if not re.match(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', email):
            flash("Invalid email format")
            return redirect(url_for("login"))

        # ===== GET USER LOCATION =====
        user_lat = request.form.get("latitude")
        user_lon = request.form.get("longitude")

        if not user_lat or not user_lon:
            flash("Location not detected. Please allow location access.")
            return redirect(url_for("login"))

        from geopy.distance import geodesic

        center_location = (CENTER_LAT, CENTER_LON)
        user_location = (float(user_lat), float(user_lon))

        distance = geodesic(center_location, user_location).km

        if distance > ALLOWED_RADIUS:
            flash("Login denied. You must be within 2 km.")
            return redirect(url_for("login"))
        # ⭐ SAVE USER LOCATION IN SESSION
        session["lat"] = user_lat
        session["lon"] = user_lon

        # ===== DATABASE CHECK =====
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT username,password,role,specialization
            FROM users
            WHERE username=%s AND email=%s
        """,(username,email))

        user = cursor.fetchone()

        cursor.close()


        if user is None:
            flash("Invalid username or email")
            return redirect(url_for("login"))

        if not check_password_hash(user[1], password):
            flash("Incorrect password")
            return redirect(url_for("login"))

        # ===== PASSWORD VERIFIED =====

        otp = random.randint(100000,999999)

        session["otp"] = str(otp)
        session["otp_time"] = time.time()

        session["temp_user"] = user[0]
        session["temp_role"] = user[2]
        session["temp_specialization"] = user[3]

        # ===== SEND EMAIL OTP =====
        msg = Message(
            "HMS Login OTP",
            sender=app.config["MAIL_USERNAME"],
            recipients=[email]
        )

        msg.body = f"Your OTP is {otp}. Valid for 60 seconds."

        mail.send(msg)

        flash("OTP sent to your email 📧")

        return redirect(url_for("verify_otp"))

    return render_template("login.html", form=form)


# ================= OTP VERIFICATION =================

@app.route("/verify_otp", methods=["GET","POST"])
def verify_otp():

    if request.method == "POST":

        entered_otp = request.form["otp"]

        saved_otp = session.get("otp")
        otp_time = session.get("otp_time")


        if not saved_otp:
            flash("Session expired")
            return redirect(url_for("login"))

        # OTP expiry
        if time.time() - otp_time > 60:
            flash("OTP expired ❌")
            return redirect(url_for("login"))

        if entered_otp == saved_otp:

            username = session.get("temp_user")

            # ===== FACE RECOGNITION =====
            face_verified = recognize_user(username)

            if not face_verified:
                flash("Face does not match ❌")
                return redirect(url_for("login"))

            # ===== VOICE VERIFICATION =====
            voice_verified = verify_voice(username)

            if not voice_verified:
                flash("Voice does not match ❌")
                return redirect(url_for("login"))

            # ===== LOGIN COMPLETE =====
            session["user"] = session["temp_user"]
            session["role"] = session["temp_role"]
            session["specialization"] = session["temp_specialization"]

            # remove temporary data
            session.pop("otp")
            session.pop("otp_time")
            session.pop("temp_user")
            session.pop("temp_role")
            session.pop("temp_specialization")

            flash("Login Successful ✅")

            # ⭐ SAVE LOGIN TIME + LOCATION
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                           UPDATE users
                           SET last_login = NOW(),
                           latitude = %s,
                           longitude = %s
                           WHERE username = %s
                           """, (
                                session.get("lat"),
                                session.get("lon"),
                                session["user"]
                                ))
            conn.commit()
            cursor.close()
            conn.close()
            # remove temporary data
            session.pop("otp",None)
            session.pop("otp_time",None)
            session.pop("temp_user",None)
            session.pop("temp_role",None)
            session.pop("temp_specialization",None)
            flash("Login Successful ✅")

            # ===== ROLE BASED DASHBOARD =====

            if session["role"] == "Admin":
                return redirect(url_for("admin_dashboard"))

            elif session["role"] == "Doctor":
                return redirect(url_for("doctor_dashboard"))

            elif session["role"] == "Nurse":
                return redirect(url_for("nurse_dashboard"))

            else:
                return redirect(url_for("user_dashboard"))

        else:
            flash("Invalid OTP ❌")

    return render_template("verify_otp.html")


# ================= ADMIN =================
@app.route("/admin_dashboard")
def admin_dashboard():

    if session.get("role") != "Admin":
        return redirect(url_for("login"))

    return render_template("admin_dashboard.html", user=session["user"])

@app.route("/admin/doctors")
def admin_doctors():

    if session.get("role") != "Admin":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, specialization, status, last_login
        FROM users
        WHERE role='Doctor'
    """)

    doctors = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin_doctors.html", doctors=doctors)

@app.route("/admin/nurses")
def admin_nurses():

    if session.get("role") != "Admin":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username
        FROM users
        WHERE role='Nurse'
    """)

    nurses = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin_nurses.html", nurses=nurses)

import psycopg2.extras
# Admin Patients Management
@app.route("/admin/patients")
def admin_patients():

    if session.get("role") != "Admin":
        return redirect(url_for("login"))

    conn = get_db()

    # IMPORTANT → use DictCursor (so we use column names instead of numbers)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("""
        SELECT id,
               name,
               status,
               created_at
        FROM patients
        ORDER BY id DESC
    """)

    patients = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin_patients.html", patients=patients)


## admin_add_patient

@app.route("/admin/add_patient", methods=["GET","POST"])
def admin_add_patient():

    if session.get("role") != "Admin":
        return redirect(url_for("login"))

    if request.method == "POST":

        # ⭐ get all form data
        name = request.form.get("name")
        id_type = request.form.get("id_type")
        id_number = request.form.get("id_number")
        gender = request.form.get("gender")
        disease = request.form.get("disease")

        conn = get_db()
        cursor = conn.cursor()

        # ⭐ insert ALL columns
        cursor.execute("""
            INSERT INTO patients(name, id_type, id_number, gender, disease)
            VALUES(%s,%s,%s,%s,%s)
        """,(name, id_type, id_number, gender, disease))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Patient added successfully ✅")
        return redirect(url_for("admin_patients"))

    return render_template("admin_add_patient.html")


# ================= DOCTOR =================

@app.route("/doctor_dashboard")
def doctor_dashboard():

    if session.get("role") != "Doctor":
        return redirect(url_for("login"))

    return render_template(
        "doctor_dashboard.html",
        user=session["user"],
        specialization=session.get("specialization")
    )

# Doctor Patients

@app.route("/doctor/patients")
def doctor_patients():

    if session.get("role") != "Doctor":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patients")
    patients = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("doctor_patients.html", patients=patients)

# Doctor Appointments

@app.route("/doctor/appointments")
def doctor_appointments():

    if session.get("role") != "Doctor":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, patient_name, doctor_name,
               appointment_date, appointment_time,
               room_number, bed_number
        FROM appointments
    """)

    appointments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("doctor_appointments.html", appointments=appointments)

# ================= DOCTOR PRESCRIPTION =================

@app.route('/doctor_prescription', methods=['GET','POST'])
def doctor_prescription():

    # ⭐ Role protection (same as other doctor routes)
    if session.get("role") != "Doctor":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    # ⭐ INSERT PRESCRIPTION
    if request.method == "POST":

        patient = request.form.get("patient")
        medicine = request.form.get("medicine")
        notes = request.form.get("notes")

        cursor.execute("""
            INSERT INTO prescriptions (patient, doctor_name, medicine, notes)
            VALUES (%s,%s,%s,%s)
        """, (patient, session["user"], medicine, notes))

        conn.commit()

        flash("Prescription added successfully ✅")

    cursor.close()
    conn.close()

    return render_template("doctor_prescription.html")
 
# ⭐ Doctor Reports

@app.route("/doctor/reports")
def doctor_reports():

    if session.get("role") != "Doctor":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reports")
    reports = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("doctor_reports.html", reports=reports)

# ⭐ Lab Results

@app.route("/doctor/lab_results", methods=["GET","POST"])
def doctor_lab_results():

    if session.get("role") != "Doctor":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        patient = request.form.get("patient")
        result = request.form.get("result")

        # Example update (adjust to your table)
        cursor.execute("""
            UPDATE prescriptions
            SET results=%s
            WHERE patient=%s
        """,(result, patient))

        conn.commit()
        flash("Lab result updated ✅")

    cursor.close()
    conn.close()

    return render_template("doctor_lab_results.html")


# ⭐ Update Patient

@app.route("/doctor/update_patient", methods=["GET","POST"])
def doctor_update_patient():

    if session.get("role") != "Doctor":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        patient_id = request.form.get("patient_id")
        name = request.form.get("name")
        age = request.form.get("age")

        # Example update query (adjust columns if needed)
        cursor.execute("""
            UPDATE patients
            SET name=%s, age=%s
            WHERE id=%s
        """,(name, age, patient_id))

        conn.commit()
        flash("Patient updated successfully ✅")

    cursor.execute("SELECT * FROM patients")
    patients = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("doctor_update_patient.html", patients=patients)


# ⭐ Admit / Discharge
@app.route("/doctor/admit_discharge", methods=["GET","POST"])
def doctor_admit_discharge():

    if session.get("role") != "Doctor":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    # Example POST logic (optional)
    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        action = request.form.get("action")  # admit / discharge

        # Example update (modify based on your DB)
        cursor.execute("""
            UPDATE patients
            SET status=%s
            WHERE id=%s
        """,(action, patient_id))

        conn.commit()
        flash("Patient status updated ✅")

    cursor.execute("SELECT * FROM patients")
    patients = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("doctor_admit_discharge.html", patients=patients)



# ⭐ Order Tests

@app.route("/doctor/order_tests", methods=["GET","POST"])
def doctor_order_tests():

    if session.get("role") != "Doctor":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        patient = request.form.get("patient_id")
        test_name = request.form.get("test")

        # Example insert (adjust table if needed)
        cursor.execute("""
            INSERT INTO prescriptions(lab_report, patient, doctor_name)
            VALUES(%s,%s,%s)
        """,(test_name, patient, session["user"]))

        conn.commit()
        flash("Test ordered successfully ✅")

    cursor.close()
    conn.close()

    return render_template("doctor_order_tests.html")
# ================= NURSE =================

@app.route("/nurse_dashboard")
def nurse_dashboard():

    # Role protection
    if session.get("role") != "Nurse":
        return redirect(url_for("login"))

    return render_template("nurse_dashboard.html", user=session["user"])

# ================= NURSE FEATURES =================

# 📋 View Medical Prescriptions (DATABASE CONNECTED)
@app.route("/nurse_prescriptions")
def nurse_prescriptions():

    if session.get("role") != "Nurse":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    # Fetch prescriptions added by doctor
    cursor.execute("""
        SELECT patient, doctor_name, medicine, notes
        FROM prescriptions
        ORDER BY id DESC
    """)

    prescriptions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "nurse_prescriptions.html",
        user=session["user"],
        prescriptions=prescriptions
    )
    # ================= VIEW UPLOADED REPORTS =================

@app.route('/temp/<filename>')
def view_file(filename):
    return send_from_directory('temp', filename)
# ================= UPLOAD MEDICAL DOCUMENT =================

@app.route('/upload_document', methods=['POST'])
def upload_document():

    if session.get("role") != "Nurse":
        return redirect(url_for("login"))

    file = request.files['file']

    if file:

        filename = secure_filename(file.filename)

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        file.save(filepath)

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO documents (patient, filename) VALUES (%s,%s)",
            (session["user"], filename)
        )

        conn.commit()
        conn.close()

        flash("File uploaded successfully")

    return redirect(url_for("nurse_dashboard"))


# ================= NURSE FEATURES =================

# 📋 View Medical Prescriptions (DATABASE CONNECTED)
@app.route("/'/nurse_view_prescriptions'")
def nurse_view_prescriptions():

    if session.get("role") != "Nurse":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    # Fetch prescriptions added by doctor
    cursor.execute("""
        SELECT patient, doctor_name, medicine, notes
        FROM prescriptions
        ORDER BY id DESC
    """)

    prescriptions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "nurse_prescriptions.html",
        user=session["user"],
        prescriptions=prescriptions
    )
# 🩺 Update Patient Vitals
@app.route("/nurse_vitals", methods=["GET","POST"])
def nurse_vitals():

    if session.get("role") != "Nurse":
        return redirect(url_for("login"))

    if request.method == "POST":

        patient = request.form.get("patient")
        temp = request.form.get("temperature")
        bp = request.form.get("bp")
        pulse = request.form.get("pulse")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO patient_vitals
            (patient, temperature, blood_pressure, pulse, nurse_name)
            VALUES(%s,%s,%s,%s,%s)
        """,(patient, temp, bp, pulse, session["user"]))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Vitals updated successfully ✅")

    return render_template("nurse_vitals.html", user=session["user"])

# 📅 Assist Appointments
@app.route("/nurse_appointments")
def nurse_appointments():

    if session.get("role") != "Nurse":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT patient_name, doctor_name,
               appointment_date, appointment_time
        FROM appointments
        ORDER BY id DESC
    """)

    appointments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "nurse_appointments.html",
        user=session["user"],
        appointments=appointments
    )

# 👥 Patient Monitoring
@app.route("/nurse_monitoring")
def nurse_monitoring():

    if session.get("role") != "Nurse":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT patient, condition_notes, nurse_name, created_at
        FROM patient_observations
        ORDER BY id DESC
    """)

    observations = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "nurse_monitoring.html",
        user=session["user"],
        observations=observations
    )


# 💊 Give Medications & Injections
@app.route("/nurse_medications", methods=["GET","POST"])
def nurse_medications():

    if session.get("role") != "Nurse":
        return redirect(url_for("login"))

    if request.method == "POST":

        patient = request.form.get("patient")
        medicine = request.form.get("medicine")
        dosage = request.form.get("dosage")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO nurse_medications
            (patient, medicine, dosage, nurse_name)
            VALUES(%s,%s,%s,%s)
        """,(patient, medicine, dosage, session["user"]))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Medication given successfully ✅")

    return render_template("nurse_medications.html", user=session["user"])



# 👀 Observe Patient Condition
@app.route("/nurse_observe_patient", methods=["GET","POST"])
def nurse_observe_patient():

    if session.get("role") != "Nurse":
        return redirect(url_for("login"))

    if request.method == "POST":

        patient = request.form.get("patient")
        condition = request.form.get("condition")

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO patient_observations
                (patient, condition_notes, nurse_name)
                VALUES(%s,%s,%s)
            """,(patient, condition, session["user"]))

            conn.commit()
            flash("Patient condition saved successfully ✅")

        except:
            flash("Error saving patient condition ❌")

        finally:
            cursor.close()
            conn.close()

    return render_template("nurse_observe_patient.html", user=session["user"])



# 📄 Assist Discharge Planning
@app.route("/nurse_discharge_assist", methods=["GET","POST"])
def nurse_discharge_assist():

    if session.get("role") != "Nurse":
        return redirect(url_for("login"))

    if request.method == "POST":

        patient = request.form.get("patient")
        doctor = request.form.get("doctor")
        notes = request.form.get("notes")

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO discharge_plans
                (patient, doctor_name, notes, nurse_name)
                VALUES(%s,%s,%s,%s)
            """,(patient, doctor, notes, session["user"]))

            conn.commit()
            flash("Discharge plan saved successfully ✅")

        except:
            flash("Error saving discharge plan ❌")

        finally:
            cursor.close()
            conn.close()

    return render_template("nurse_discharge_assist.html", user=session["user"])



# 📂 Maintain Patient Records & Documents
@app.route("/nurse_records", methods=["GET","POST"])
def nurse_records():

    # Role protection
    if session.get("role") != "Nurse":
        return redirect(url_for("login"))

    if request.method == "POST":

        patient = request.form.get("patient")
        notes = request.form.get("notes")
        file = request.files.get("file")

        conn = get_db()
        cursor = conn.cursor()

        try:
            # ⭐ Save nursing notes
            if patient and notes:
                cursor.execute("""
                    INSERT INTO nurse_notes(patient, notes, nurse_name)
                    VALUES(%s,%s,%s)
                """, (patient, notes, session["user"]))

                conn.commit()
                flash("Notes saved successfully ✅")

            # ⭐ Upload + Encrypt file
            if file and file.filename:

                filename = secure_filename(file.filename)

                # temp path
                temp_path = os.path.join("temp", filename)

                # encrypted path
                encrypted_path = os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename + ".enc"
                )

                # save temp file
                file.save(temp_path)

                # AES encryption
                encrypt_file(temp_path, encrypted_path, "MY_SECRET_AES_KEY")

                # delete original file
                os.remove(temp_path)

                flash("Encrypted file uploaded successfully 🔐")

        except Exception as e:
            flash("Error occurred while saving data ❌")

        finally:
            cursor.close()
            conn.close()

    return render_template("nurse_records.html", user=session["user"])



# ================= PATIENT =================

@app.route("/user_dashboard")
def user_dashboard():

    if session.get("role") != "User":
        return redirect(url_for("login"))

    return render_template("user_dashboard.html", user=session["user"])


    doctors = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("patient_doctors.html", doctors=doctors)

# ================= PATIENT PRESCRIPTIONS =================

@app.route("/patient/prescriptions")
def patient_prescriptions():

    if session.get("role") != "User":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT medicine, doctor_name,notes
        FROM prescriptions
        WHERE patient=%s
        ORDER BY id DESC
    """,(session["user"],))

    prescriptions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "patient_prescriptions.html",
        prescriptions=prescriptions
    )


# ================= PATIENT VITALS =================

@app.route("/patient/vitals")
def patient_vitals():

    if session.get("role") != "User":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT temperature, blood_pressure, pulse, nurse_name
        FROM patient_vitals
        WHERE patient=%s
        ORDER BY id DESC
    """,(session["user"],))

    vitals = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("patient_vitals.html", vitals=vitals)

# ================= VIEW DOCTORS =================

@app.route("/patient/doctors")
def patient_doctors():

    if session.get("role") != "User":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, specialization
        FROM users
        WHERE role='Doctor'
    """)

    doctors = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("patient_doctors.html", doctors=doctors)

# ================= BOOK APPOINTMENT =================

@app.route("/patient/book_appointment", methods=["GET", "POST"])
def patient_book_appointment():

    if session.get("role") != "User":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, specialization
        FROM users
        WHERE role='Doctor'
    """)
    doctors = cursor.fetchall()

    if request.method == "POST":

        doctor = request.form.get("doctor")
        date = request.form.get("date")
        time = request.form.get("time")

        if doctor and date and time:

            cursor.execute("""
                INSERT INTO appointments
                (patient_name, doctor_name, appointment_date,
                 appointment_time, room_number, bed_number)
                VALUES (%s,%s,%s,%s,NULL,NULL)
            """,(session["user"], doctor, date, time))

            conn.commit()

            flash("Appointment booked successfully ✅")

            cursor.close()
            conn.close()

            return redirect(url_for("patient_book_appointment"))

    cursor.close()
    conn.close()

    return render_template("patient_book_appointment.html", doctors=doctors)


# ================= PATIENT REPORTS =================

@app.route("/patient/reports", methods=["GET","POST"])
def patient_reports():

    print("UPLOAD PATH:", app.config["UPLOAD_FOLDER"])   # ⭐ debug print

    if session.get("role") != "User":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    # ensure temp folder exists
    os.makedirs("temp", exist_ok=True)

    if request.method == "POST":

        file = request.files.get("file")

        if file and file.filename:

            filename = secure_filename(file.filename)

            temp_path = os.path.join("temp", filename)

            encrypted_filename = filename + ".enc"

            encrypted_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                encrypted_filename
            )

            try:
                # save temp file
                file.save(temp_path)

                # AES encryption
                encrypt_file(temp_path, encrypted_path, "MY_SECRET_AES_KEY")

                # delete temp file
                os.remove(temp_path)

                # save encrypted filename in DB
                cursor.execute("""
                    INSERT INTO reports(patient, filename)
                    VALUES(%s,%s)
                """,(session["user"], encrypted_filename))

                conn.commit()

                flash("Report uploaded & encrypted successfully 🔐")

            except Exception as e:
                print("ENCRYPT ERROR:", e)   # ⭐ shows real error in terminal
                flash("Encryption failed ❌")

    # fetch reports
    cursor.execute("""
    SELECT id, filename, uploaded_at
    FROM reports
    WHERE patient=%s
    ORDER BY id DESC
""",(session["user"],))


    reports = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("patient_reports.html", reports=reports)

# ================= VIEW REPORT (AUTO DECRYPT) =================

# ================= VIEW REPORT (ONE TIME DECRYPT ONLY) =================

@app.route("/view_report/<filename>")
def view_report(filename):

    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    try:

        # get current view count
        cursor.execute("""
            SELECT view_count
            FROM reports
            WHERE filename=%s
        """,(filename,))

        result = cursor.fetchone()

        if not result:
            flash("Report not found ❌")
            return redirect(url_for("patient_reports"))

        view_count = result[0]

        encrypted_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        # ⭐ allow only ONE decrypted view
        if view_count < 1:

            decrypted_name = filename.replace(".enc","")
            temp_decrypted = os.path.join("temp", decrypted_name)

            decrypt_file(encrypted_path, temp_decrypted, "MY_SECRET_AES_KEY")

            # increase view count
            cursor.execute("""
                UPDATE reports
                SET view_count = view_count + 1
                WHERE filename=%s
            """,(filename,))
            conn.commit()

            cursor.close()
            conn.close()

            return send_file(temp_decrypted)

        else:

            # after first view → send encrypted file
            cursor.close()
            conn.close()

            flash("Decrypted view already used. Encrypted file only 🔐")

            return send_file(
                encrypted_path,
                as_attachment=True
            )

    except Exception as e:

        print("ERROR:", e)
        flash("Error opening file ❌")
        return redirect(url_for("patient_reports"))


# ================= LOGOUT =================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)