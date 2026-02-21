import random
from datetime import date
from app import app, db
from app.models import User, PatientProfile

# Push app context (since you are not using create_app)
app.app_context().push()

# --------------------------
# Random Helpers
# --------------------------

blood_groups = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]

def random_dob():
    year = random.randint(1980, 2005)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return date(year, month, day)

def random_phone():
    return "9" + "".join([str(random.randint(0, 9)) for _ in range(9)])

# --------------------------
# Patient Data (6–8 Only)
# --------------------------

patient_names = [
    "Rahul Agarwal",
    "Priya Sharma",
    "Aman Gupta",
    "Kavya Menon",
    "Yash Thakur",
    "Anjali Deshmukh",
    "Rohan Sinha",
    "Meera Iqbal"
]

created_count = 0

for name in patient_names:
    email = name.lower().replace(" ", ".") + "@gmail.com"

    # Skip if already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        print(f"Skipped existing patient: {name}")
        continue

    user = User(
        email=email,
        role="patient",
        is_active=True,
        is_temp_password=False,
        must_change_password=False
    )
    user.set_password("Patient@123")

    db.session.add(user)
    db.session.flush()

    profile = PatientProfile(
        user_id=user.id,
        full_name=name,
        date_of_birth=random_dob(),
        gender=random.choice(["Male", "Female"]),
        contact_number=random_phone(),
        blood_group=random.choice(blood_groups),
        allergies="None"
    )

    db.session.add(profile)
    created_count += 1
    print(f"Created patient: {name}")

db.session.commit()

print(f"\n✅ Seeding complete. {created_count} new patients added.")
from app import app, db
from app.models import Department, User, DoctorProfile, PatientProfile
from datetime import date


def seed_data():
    with app.app_context():

        # -----------------------------
        # 1️⃣ Departments
        # -----------------------------
        departments_data = [
            ("General Medicine", "Diagnosis and treatment of common illnesses."),
            ("Cardiology", "Heart and cardiovascular system treatment."),
            ("Orthopedics", "Bone and musculoskeletal treatment."),
            ("Pediatrics", "Medical care for infants and children."),
            ("Gynecology", "Women’s reproductive health."),
            ("Dermatology", "Skin disorders treatment."),
            ("Neurology", "Brain and nervous system treatment."),
            ("General Surgery", "General surgical procedures.")
        ]

        department_objects = {}

        for name, desc in departments_data:
            dept = Department.query.filter_by(name=name).first()
            if not dept:
                dept = Department(name=name, description=desc)
                db.session.add(dept)
                db.session.flush()
            department_objects[name] = dept

        db.session.commit()
        print("Departments created.")


        # -----------------------------
        # 2️⃣ Doctors
        # -----------------------------
        doctors_data = [
            # General Medicine (3)
            ("Dr. Rajesh Sharma", "rajesh.sharma@healnest.com", "General Medicine", "MBBS, MD", 12),
            ("Dr. Amit Verma", "amit.verma@healnest.com", "General Medicine", "MBBS, DNB", 8),
            ("Dr. Sandeep Kulkarni", "sandeep.kulkarni@healnest.com", "General Medicine", "MBBS, MD", 15),

            # Cardiology (2)
            ("Dr. Anil Mehta", "anil.mehta@healnest.com", "Cardiology", "MBBS, DM Cardiology", 14),
            ("Dr. Vivek Nair", "vivek.nair@healnest.com", "Cardiology", "MBBS, DM Cardiology", 9),

            # Orthopedics (2)
            ("Dr. Prakash Reddy", "prakash.reddy@healnest.com", "Orthopedics", "MBBS, MS Orthopedics", 11),
            ("Dr. Karthik Iyer", "karthik.iyer@healnest.com", "Orthopedics", "MBBS, MS Orthopedics", 7),

            # Pediatrics (2)
            ("Dr. Neha Kapoor", "neha.kapoor@healnest.com", "Pediatrics", "MBBS, MD Pediatrics", 10),
            ("Dr. Swati Deshmukh", "swati.deshmukh@healnest.com", "Pediatrics", "MBBS, MD Pediatrics", 6),

            # Single doctor departments
            ("Dr. Pooja Bansal", "pooja.bansal@healnest.com", "Gynecology", "MBBS, MS Gynecology", 13),
            ("Dr. Ritu Malhotra", "ritu.malhotra@healnest.com", "Dermatology", "MBBS, MD Dermatology", 9),
            ("Dr. Arvind Rao", "arvind.rao@healnest.com", "Neurology", "MBBS, DM Neurology", 16),
            ("Dr. Manoj Patil", "manoj.patil@healnest.com", "General Surgery", "MBBS, MS Surgery", 18),
        ]

        for name, email, dept_name, qualification, exp in doctors_data:
            if not User.query.filter_by(email=email).first():

                user = User(
                    email=email,
                    role="doctor",
                    is_active=True,
                    must_change_password=True
                )
                user.set_password("doctor123")

                db.session.add(user)
                db.session.flush()

                profile = DoctorProfile(
                    user_id=user.id,
                    department_id=department_objects[dept_name].id,
                    full_name=name,
                    qualifications=qualification,
                    experience_years=exp
                )

                db.session.add(profile)

        db.session.commit()
        print("Doctors created.")


        # -----------------------------
        # 3️⃣ Patients
        # -----------------------------
        patients_data = [
            ("Rahul Singh", "rahul.singh@gmail.com", date(1995, 5, 14), "Male"),
            ("Priya Sharma", "priya.sharma@gmail.com", date(1998, 7, 22), "Female"),
            ("Aman Gupta", "aman.gupta@gmail.com", date(1992, 3, 10), "Male"),
            ("Sneha Patel", "sneha.patel@gmail.com", date(2001, 9, 5), "Female"),
            ("Rohit Yadav", "rohit.yadav@gmail.com", date(1988, 12, 18), "Male"),
            ("Ananya Iyer", "ananya.iyer@gmail.com", date(1999, 4, 30), "Female"),
            ("Kunal Mishra", "kunal.mishra@gmail.com", date(1994, 11, 2), "Male"),
        ]

        for name, email, dob, gender in patients_data:
            if not User.query.filter_by(email=email).first():

                user = User(
                    email=email,
                    role="patient",
                    is_active=True,
                    must_change_password=True
                )
                user.set_password("patient123")

                db.session.add(user)
                db.session.flush()

                profile = PatientProfile(
                    user_id=user.id,
                    full_name=name,
                    date_of_birth=dob,
                    gender=gender
                )

                db.session.add(profile)

        db.session.commit()
        print("Patients created.")


if __name__ == "__main__":
    seed_data()


    