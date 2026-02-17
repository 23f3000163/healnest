from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, date, timedelta
from functools import wraps
from app import db, models
from . import admin_bp
from sqlalchemy.orm import aliased
from app.models import User, DoctorProfile


from app.forms import (
    AddDoctorForm,
    EditDoctorForm,
    EditPatientForm,
    DepartmentForm
)

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('main.login'))

        if current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.home'))

        return func(*args, **kwargs)
    return wrapper


# -------------------------------------------------
# Admin Dashboard
# -------------------------------------------------

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))


    now = datetime.utcnow()

    # ================= BASIC COUNTS =================

    doctor_count = models.User.query.filter_by(
        role='doctor',
        is_deleted=False
    ).count()

    patient_count = models.User.query.filter_by(
        role='patient',
        is_deleted=False
    ).count()

    appointment_count = (
         models.Appointment.query
        .filter(
            models.Appointment.appointment_datetime >= now,
            models.Appointment.status == "BOOKED"
        )
        .count()
        )

      # ================= RECENT DOCTORS =================

    doctors = (
        models.User.query
        .filter_by(role='doctor', is_deleted=False)
        .order_by(models.User.created_at.desc())
        .limit(7)
        .all()
    )

    # ================= RECENT PATIENTS =================

    patients = (
        models.User.query
        .filter_by(role='patient', is_deleted=False)
        .order_by(models.User.created_at.desc())
        .limit(7)
        .all()
    )


        # ================= UPCOMING APPOINTMENTS =================

    

    upcoming_appointments = (
        models.Appointment.query
          .filter(
                models.Appointment.appointment_datetime >= now,
                models.Appointment.status == "BOOKED"
        )
        .order_by(models.Appointment.created_at.asc())
        .limit(7)
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        doctor_count=doctor_count,
        patient_count=patient_count,
        appointment_count=appointment_count,
        doctors=doctors,
        patients=patients,
        appointments=upcoming_appointments
    )


@admin_bp.route('/dashboard/analytics')
@login_required
def dashboard_analytics():
    if current_user.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    today = datetime.utcnow().date()

    # ================= WEEKLY (LAST 7 DAYS) =================
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]

    weekly_data = []
    for day in last_7_days:
        count = models.Appointment.query.filter(
            func.date(models.Appointment.created_at) == day
        ).count()
        weekly_data.append(count)

    highest_week_value = max(weekly_data) if weekly_data else 0

    # ================= MONTHLY (LAST 30 DAYS) =================
    last_30_days = today - timedelta(days=30)

    monthly_raw = (
        db.session.query(
            func.date(models.Appointment.created_at),
            func.count(models.Appointment.id)
        )
        .filter(models.Appointment.created_at >= last_30_days)
        .group_by(func.date(models.Appointment.created_at))
        .all()
    )

    monthly_map = {str(date): count for date, count in monthly_raw}

    monthly_data = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        monthly_data.append(monthly_map.get(str(day), 0))

    highest_month_value = max(monthly_data) if monthly_data else 0

    # ================= USER DISTRIBUTION =================
    doctor_count = models.User.query.filter(
        models.User.role == 'doctor',
        models.User.is_deleted == False,
        models.User.is_active == True
).count()

    patient_count = models.User.query.filter(
        models.User.role == 'patient',
        models.User.is_deleted == False,
        models.User.is_active == True
).count()

    user_distribution = {
        "patients": patient_count,
        "doctors": doctor_count,
    }

    return jsonify({
        "weekly_chart": weekly_data,
        "monthly_chart": monthly_data,
        "highest_week_value": highest_week_value,
        "highest_month_value": highest_month_value,
        "user_distribution": user_distribution
    })

# -------------------------------------------------
# Doctor Management
# -------------------------------------------------
@admin_bp.route('/add_doctor', methods=['GET', 'POST'])
@login_required
def add_doctor():
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    form = AddDoctorForm()

    # Populate department dropdown
    form.department_id.choices = [
        (d.id, d.name)
        for d in models.Department.query.order_by(models.Department.name).all()
    ]

    if form.validate_on_submit():

        # Check email uniqueness
        existing = models.User.query.filter_by(email=form.email.data).first()
        if existing:
            flash("Email already exists.", "danger")
            return redirect(url_for("admin.add_doctor"))

        # Validate department
        department = models.Department.query.get(form.department_id.data)
        if not department:
            flash("Invalid department selected.", "danger")
            return redirect(url_for("admin.add_doctor"))


        temp_password = "Doctor@123"  # Temporary password

        # Create doctor user
        user = User(
            email=form.email.data,
            role="doctor",
            is_active=True,
            must_change_password=True    #  Force password change on first login
        )

        user.set_password(temp_password)

        db.session.add(user)
        db.session.flush()  # get user.id before commit

        # Create doctor profile
        profile = models.DoctorProfile(
            user_id=user.id,
            full_name=form.full_name.data,
            department_id=form.department_id.data,
            contact_number=form.contact_number.data
        )

        db.session.add(profile)
        db.session.commit()

        flash('Doctor added successfully. Temporary password is set.', 'success')
        return redirect(url_for('admin.manage_doctors'))

    return render_template('admin/add_doctor.html', form=form)


@admin_bp.route('/doctors')
@login_required
def manage_doctors():
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')

    query = (
        models.User.query
        .filter_by(role='doctor', is_deleted=False)   #  hide deleted doctors
        .join(models.DoctorProfile)
    )

    # ===== SORTING =====
    if sort == 'name':
        column = models.DoctorProfile.full_name
    elif sort == 'email':
        column = models.User.email
    elif sort == 'status':
        column = models.User.is_active
    else:
        column = models.User.created_at  # default

    if order == 'asc':
        query = query.order_by(column.asc())
    else:
        query = query.order_by(column.desc())

    doctors = query.paginate(
        page=page,
        per_page=10,
        error_out=False
    )

    return render_template(
        'admin/manage_doctors.html',
        doctors=doctors,
        sort=sort,
        order=order
    )




@admin_bp.route('/doctor/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_doctor(user_id):

    # 1️ Role security check
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    # 2️ Get user safely
    doctor_user = models.User.query.get_or_404(user_id)

    # 3️ Ensure correct role
    if doctor_user.role != 'doctor':
        flash('Invalid doctor account.', 'danger')
        return redirect(url_for('admin.manage_doctors'))

    # 4️ Ensure profile exists
    profile = doctor_user.doctor_profile
    if not profile:
        flash('Doctor profile is missing.', 'danger')
        return redirect(url_for('admin.manage_doctors'))

    # 5️ Bind form to profile
    form = EditDoctorForm(obj=profile)

    # 6️ Populate department dropdown
    form.department_id.choices = [
        (d.id, d.name)
        for d in models.Department.query.order_by(models.Department.name).all()
    ]

    if form.validate_on_submit():

        # Update profile fields
        profile.full_name = form.full_name.data
        profile.department_id = form.department_id.data
        profile.contact_number = form.contact_number.data

        # Update user email
        doctor_user.email = form.email.data

        db.session.commit()

        flash('Doctor profile updated successfully.', 'success')
        return redirect(url_for('admin.manage_doctors'))

    # Pre-fill email on GET
    if request.method == 'GET':
        form.email.data = doctor_user.email

    return render_template(
        'admin/edit_doctor.html',
        title='Edit Doctor',
        form=form
    )


# -------------------------------------------------
# Patient Management
# -------------------------------------------------
@admin_bp.route('/patient/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(user_id):

    # 1️ Role security check
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    # 2️ Get user safely
    patient_user = models.User.query.get_or_404(user_id)

    # 3️ Ensure correct role
    if patient_user.role != 'patient':
        flash('Invalid patient account.', 'danger')
        return redirect(url_for('admin.manage_patients'))

    # 4️ Ensure profile exists
    profile = patient_user.patient_profile
    if not profile:
        flash('Patient profile is missing.', 'danger')
        return redirect(url_for('admin.manage_patients'))

    # 5️ Bind form
    form = EditPatientForm(obj=profile)

    if form.validate_on_submit():

        # Update profile
        profile.full_name = form.full_name.data
        profile.contact_number = form.contact_number.data

        # Update email
        patient_user.email = form.email.data

        db.session.commit()

        flash('Patient profile updated successfully.', 'success')
        return redirect(url_for('admin.manage_patients'))

    # Pre-fill email on GET
    if request.method == 'GET':
        form.email.data = patient_user.email

    return render_template(
        'admin/edit_patient.html',
        title='Edit Patient',
        form=form
    )




@admin_bp.route('/patients')
@login_required
def manage_patients():
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')

    query = (
        models.User.query
        .filter_by(role='patient', is_deleted=False)   #  hide deleted patients
        .join(models.PatientProfile)
    )

    # ===== SORTING =====
    if sort == 'name':
        column = models.PatientProfile.full_name
    elif sort == 'email':
        column = models.User.email
    elif sort == 'status':
        column = models.User.is_active
    else:
        column = models.User.created_at

    if order == 'asc':
        query = query.order_by(column.asc())
    else:
        query = query.order_by(column.desc())

    patients = query.paginate(
        page=page,
        per_page=10,
        error_out=False
    )

    return render_template(
        'admin/manage_patients.html',
        patients=patients,
        sort=sort,
        order=order
    )




# -------------------------------------------------
#   ACTION ROUTES 
# -------------------------------------------------
@admin_bp.route('/doctor/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_doctor(user_id):

    if current_user.role != 'admin':
        flash("Unauthorized action.", "danger")
        return redirect(url_for('main.home'))

    user = models.User.query.get_or_404(user_id)

    if user.role != "doctor":
        flash("Invalid doctor.", "danger")
        return redirect(url_for('admin.manage_doctors'))

    #  SOFT DELETE
    user.is_deleted = True
    user.is_active = False

    db.session.commit()

    flash("Doctor deleted successfully.", "warning")
    return redirect(url_for('admin.manage_doctors'))



@admin_bp.route('/patient/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_patient(user_id):

    if current_user.role != 'admin':
        flash("Unauthorized action.", "danger")
        return redirect(url_for('main.home'))

    user = models.User.query.get_or_404(user_id)

    if user.role != "patient":
        flash("Invalid patient.", "danger")
        return redirect(url_for('admin.manage_patients'))

    #  SOFT DELETE
    user.is_deleted = True
    user.is_active = False

    db.session.commit()

    flash("Patient deleted successfully.", "warning")
    return redirect(url_for('admin.manage_patients'))




@admin_bp.route('/user/blacklist/<int:user_id>', methods=['POST'])
@login_required
def blacklist_user(user_id):
    if current_user.role != 'admin':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('main.home'))

    user = models.User.query.get_or_404(user_id)

    # Prevent double blacklist
    if not user.is_active:
        flash('User is already blacklisted.', 'warning')
        return redirect(request.referrer or url_for('admin.dashboard'))

    user.is_active = False
    db.session.commit()

    # Determine display name
    if user.role == 'doctor' and user.doctor_profile:
        display_name = f"Dr. {user.doctor_profile.full_name}"
    elif user.role == 'patient' and user.patient_profile:
        display_name = user.patient_profile.full_name
    else:
        display_name = user.email

    flash(f'{display_name} has been blacklisted.', 'warning')
    return redirect(request.referrer or url_for('admin.dashboard'))



@admin_bp.route('/user/activate/<int:user_id>', methods=['POST'])
@login_required
def activate_user(user_id):
    if current_user.role != 'admin':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('main.home'))

    user = models.User.query.get_or_404(user_id)

    # Prevent double activation
    if user.is_active:
        flash('User is already active.', 'info')
        return redirect(request.referrer or url_for('admin.dashboard'))

    user.is_active = True
    db.session.commit()

    # Determine display name
    if user.role == 'doctor' and user.doctor_profile:
        display_name = f"Dr. {user.doctor_profile.full_name}"
    elif user.role == 'patient' and user.patient_profile:
        display_name = user.patient_profile.full_name
    else:
        display_name = user.email

    flash(f'{display_name} has been re-activated.', 'success')
    return redirect(request.referrer or url_for('admin.dashboard'))


# -------------------------------------------------
# Department Management
# -------------------------------------------------

@admin_bp.route('/departments', methods=['GET', 'POST'])
@login_required
def manage_departments():
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    form = DepartmentForm()

    # CREATE department
    if form.validate_on_submit():
        existing = models.Department.query.filter_by(
            name=form.name.data.strip()
        ).first()

        if existing:
            flash('Department with this name already exists.', 'warning')
        else:
            department = models.Department(
                name=form.name.data.strip(),
                description=form.description.data.strip()
            )
            db.session.add(department)
            db.session.commit()
            flash('Department created successfully.', 'success')

        return redirect(url_for('admin.manage_departments'))

    # Pagination
    page = request.args.get('page', 1, type=int)

    departments = (
        models.Department.query
        .order_by(models.Department.name.asc())
        .paginate(page=page, per_page=10, error_out=False)
    )

    return render_template(
        'admin/manage_departments.html',
        title='Manage Departments',
        departments=departments,
        form=form
    )



@admin_bp.route('/departments/<int:dept_id>')
@login_required
def department_details(dept_id):
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    department = models.Department.query.get_or_404(dept_id)

    doctors = (
        models.User.query
        .filter_by(role='doctor')
        .join(models.DoctorProfile)
        .filter(models.DoctorProfile.department_id == department.id)
        .order_by(models.DoctorProfile.full_name)
        .all()
    )

    return render_template(
        'admin/department_details.html',
        title=department.name,
        department=department,
        doctors=doctors
    )


@admin_bp.route('/departments/edit', methods=['POST'])
@login_required
def edit_department():
    if current_user.role != 'admin':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('main.home'))

    dept_id = request.form.get('dept_id')
    department = models.Department.query.get_or_404(dept_id)

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash('Department name cannot be empty.', 'warning')
        return redirect(url_for('admin.manage_departments'))

    # Prevent duplicate names
    duplicate = models.Department.query.filter(
        models.Department.name == name,
        models.Department.id != department.id
    ).first()

    if duplicate:
        flash('Another department with this name already exists.', 'warning')
        return redirect(url_for('admin.manage_departments'))

    department.name = name
    department.description = description
    db.session.commit()

    flash('Department updated successfully.', 'success')
    return redirect(url_for('admin.manage_departments'))


@admin_bp.route('/departments/delete/<int:dept_id>', methods=['POST'])
@login_required
def delete_department(dept_id):

    # 1️ Role protection
    if current_user.role != 'admin':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('main.home'))

    department = models.Department.query.get_or_404(dept_id)

    # 2️ SAFETY CHECK — prevent delete if doctors exist
    if department.doctors:
        flash(
            "Cannot delete department because doctors are assigned.",
            "danger"
        )
        return redirect(url_for('admin.manage_departments'))

    # 3️ Safe to delete
    db.session.delete(department)
    db.session.commit()

    flash('Department deleted successfully.', 'success')
    return redirect(url_for('admin.manage_departments'))


# ---------------------------
# View All Appointments (Admin)
# ---------------------------
@admin_bp.route("/appointments")
@login_required
@admin_required
def manage_appointments():

    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'date')
    order = request.args.get('order', 'desc')

    doctor_id = request.args.get("doctor_id")
    status = request.args.get("status")
    date_str = request.args.get("date")

    query = models.Appointment.query

    # =========================
    # FILTER: Doctor
    # =========================
    if doctor_id:
        try:
            query = query.filter(
                models.Appointment.doctor_id == int(doctor_id)
            )
        except ValueError:
            pass

    # =========================
    # FILTER: Status
    # =========================
    if status:
        query = query.filter(
            models.Appointment.status == status
        )

    # =========================
    # FILTER: Date
    # =========================
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            query = query.filter(
                db.func.date(models.Appointment.appointment_datetime) == selected_date
            )
        except ValueError:
            pass

    # =========================
    # SORTING
    # =========================
    if sort == "status":
        column = models.Appointment.status
    elif sort == "doctor":
        column = models.Appointment.doctor_id
    else:
        column = models.Appointment.appointment_datetime  # default

    if order == "asc":
        query = query.order_by(column.asc())
    else:
        query = query.order_by(column.desc())

    # =========================
    # PAGINATION
    # =========================
    appointments = query.paginate(
        page=page,
        per_page=10,
        error_out=False
    )

    doctors = (
        models.User.query
        .filter_by(
            role="doctor",
            is_deleted=False,
            is_active=True
        )
        .join(models.DoctorProfile)
        .order_by(models.DoctorProfile.full_name)
        .all()
    )

    return render_template(
        "admin/manage_appointments.html",
        appointments=appointments,
        doctors=doctors,
        sort=sort,
        order=order
    )


@admin_bp.route("/patient/<int:patient_id>/history")
@login_required
def view_patient_history(patient_id):

    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.home"))

    patient = models.User.query.get_or_404(patient_id)

    history = (
        models.Appointment.query
        .filter(
            models.Appointment.patient_id == patient_id,
            models.Appointment.status == "COMPLETED"
        )
        .order_by(models.Appointment.appointment_datetime.desc())
        .all()
    )

    # Calculate age
    profile = patient.patient_profile
    patient_age = None

    if profile and profile.date_of_birth:
        today = date.today()
        patient_age = today.year - profile.date_of_birth.year - (
            (today.month, today.day) <
            (profile.date_of_birth.month, profile.date_of_birth.day)
        )

    return render_template(
        "shared/patient_history.html",
        patient=patient,
        history=history,
        patient_age=patient_age,
        back_url=url_for("admin.dashboard")
    )
