# Admin Creation Guide for HealNest

## Current Status: ❌ No Admin Creation Code Found

Your project **does NOT have any admin creation functionality** yet. There are three ways to create an admin account:

---

## Option 1: Manual Database Script (Recommended for First Admin)

Create a new file `create_admin.py` in your project root:

```python
from app import app, db, bcrypt
from app.models import User

app.app_context().push()

# Check if admin already exists
admin_email = "admin@healnest.com"
existing_admin = User.query.filter_by(email=admin_email).first()

if existing_admin:
    print(f"❌ Admin already exists: {admin_email}")
else:
    # Create new admin
    admin_user = User(
        email=admin_email,
        role="admin",
        is_active=True,
        is_deleted=False,
        is_temp_password=False,
        must_change_password=False
    )
    admin_user.set_password("AdminPassword@123")  # Change this!
    
    db.session.add(admin_user)
    db.session.commit()
    
    print(f"✅ Admin created successfully!")
    print(f"   Email: {admin_email}")
    print(f"   Password: AdminPassword@123")
    print(f"   ⚠️  NEVER leave default password in production!")
```

### Run the script:

```bash
python create_admin.py
```

---

## Option 2: Flask Shell (Interactive)

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Start Flask shell
flask shell
```

Then in the shell:

```python
from app.models import User
from app import db

# Create admin
admin = User(
    email="admin@healnest.com",
    role="admin",
    is_active=True,
    is_deleted=False
)
admin.set_password("SecurePassword@123")

db.session.add(admin)
db.session.commit()

print("✅ Admin created!")
```

---

## Option 3: Add Admin Registration Route (For Multiple Admins)

Modify `app/routes/main_routes.py` to add:

```python
@main_bp.route("/admin/register", methods=["GET", "POST"])
def register_admin():
    """Create admin account (should be protected in production)"""
    
    if current_user.is_authenticated and current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("main.home"))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = models.User(
            email=form.email.data,
            role="admin"  # ← Key difference
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash("Admin account created!", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", title="Register Admin", form=form)
```

⚠️ **Security WARNING:** This route should be protected in production!

---

## Current Registration System

Your registration system (**main_routes.py** lines 38-68):

```python
@main_bp.route("/register", methods=["GET", "POST"])
def register():
    # ... existing code ...
    user = models.User(
        email=form.email.data,
        role="patient"  # ← Always creates patient!
    )
```

**Current Behavior:**
- ✅ Patients can self-register
- ❌ No public admin registration
- ❌ No admin creation during setup

---

## User Model (app/models.py)

Your User model supports three roles:

```python
class User(db.Model, UserMixin):
    role = db.Column(db.String(10), nullable=False)
    
    __table_args__ = (
        db.CheckConstraint(
            "role IN ('admin', 'doctor', 'patient')",
            name="check_valid_role"
        ),
    )
```

**Available Roles:**
- `admin` - Full system access
- `doctor` - Doctor-specific features
- `patient` - Patient-specific features

---

## Next Steps for Production

### 1. Create First Admin (Use Option 1)

```bash
python create_admin.py
```

### 2. Login with Admin Credentials

- **Email:** admin@healnest.com
- **Password:** Your chosen password

### 3. Create Doctors via Admin Panel

Admins can create doctors via: **Admin Dashboard → Manage Doctors → Add Doctor**

### 4. Remove Creation Scripts from Production

Before deploying to Render:

```bash
# Remove the creation script
rm create_admin.py
```

---

## Admin Dashboard Features

Once logged in as admin, you have access to:

- ✅ Manage Doctors
- ✅ Manage Patients
- ✅ Manage Departments
- ✅ View Appointments
- ✅ Search Users
- ✅ User Status Management (activate/deactivate)

See: `app/routes/admin_routes.py` for full admin functionality

---

## Checklist for Deployment

- [ ] Create first admin account before deploying
- [ ] Change default password if using automated script
- [ ] Remove `create_admin.py` from production deployment
- [ ] Verify admin can login successfully
- [ ] Test admin dashboard features

---

## Files to Reference

- **Models:** [app/models.py](app/models.py) - User model definition
- **Routes:** [app/routes/admin_routes.py](app/routes/admin_routes.py) - Admin functionality
- **Registration:** [app/routes/main_routes.py](app/routes/main_routes.py#L38) - Registration logic
