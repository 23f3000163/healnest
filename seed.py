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
