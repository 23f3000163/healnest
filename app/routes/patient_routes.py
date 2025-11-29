from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app.models import Department, Appointment, User, Notification, DoctorProfile, Availability
from . import patient_bp
from datetime import datetime, date, time, timedelta
from app.forms import BookingForm, UpdateProfileForm
from app import db
from sqlalchemy import or_

@patient_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Shows the main patient dashboard with department list
    and a preview of upcoming appointments.
    """
    if current_user.role != 'patient':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
        
    departments = Department.query.order_by('name').all()
    
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == current_user.id,
        Appointment.status == 'Booked',
        Appointment.appointment_datetime >= datetime.now()
    ).order_by(Appointment.appointment_datetime.asc()).all()
    
    return render_template(
        'patient/dashboard.html', 
        title='My Dashboard', 
        departments=departments,
        appointments=upcoming_appointments
    )

@patient_bp.route('/my_history')
@login_required
def my_history():
    if current_user.role != 'patient':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    
    # Patient sees ALL their completed appointments
    patient_history = Appointment.query.filter(
        Appointment.patient_id == current_user.id,
        Appointment.status == 'Completed'
    ).order_by(Appointment.appointment_datetime.desc()).all()

    # --- NEW: Calculate Patient Age ---
    patient_age = None
    if current_user.patient_profile and current_user.patient_profile.date_of_birth:
        today = date.today()
        patient_age = today.year - current_user.patient_profile.date_of_birth.year - \
                      ((today.month, today.day) < (current_user.patient_profile.date_of_birth.month, current_user.patient_profile.date_of_birth.day))

    return render_template(
        'admin/patient_history.html',
        title='My Appointment History',
        patient=current_user, 
        history=patient_history,
        patient_age=patient_age, 
        back_url=url_for('patient.dashboard')
    )
    

@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    Handles viewing and updating the patient's own profile.
    """
    if current_user.role != 'patient':
        return redirect(url_for('main.home'))

    profile = current_user.patient_profile
    form = UpdateProfileForm(obj=profile)

    if form.validate_on_submit():
        profile.full_name = form.full_name.data
        profile.date_of_birth = form.date_of_birth.data
        profile.gender = form.gender.data
        profile.contact_number = form.contact_number.data
        profile.blood_group = form.blood_group.data
        profile.allergies = form.allergies.data
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('patient.profile'))

    return render_template('patient/profile.html', title='My Profile', form=form)

@patient_bp.route('/department/<int:department_id>')
@login_required
def department_details(department_id):
    """
    Displays details for a specific department, including a list of its doctors.
    """
    if current_user.role != 'patient':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
        
    department = Department.query.get_or_404(department_id)
    return render_template(
        'patient/department_details.html',
        title=department.name,
        department=department
    )

@patient_bp.route('/doctor/<int:doctor_profile_id>')
@login_required
def doctor_details(doctor_profile_id):
    """
    Displays a detailed profile page for a specific doctor.
    """
    if current_user.role != 'patient':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))

    doctor_profile = DoctorProfile.query.get_or_404(doctor_profile_id)
    return render_template(
        'patient/doctor_details.html',
        title=f"Dr. {doctor_profile.full_name}",
        doctor=doctor_profile
    )

@patient_bp.route('/book/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def book_appointment(doctor_id):
    if current_user.role != 'patient':
        flash('Only patients can book appointments.', 'danger')
        return redirect(url_for('main.home'))

    doctor_profile = DoctorProfile.query.get_or_404(doctor_id)
    doctor_user_id = doctor_profile.user_id
    form = BookingForm()

  
    MORNING_START = time(8, 0)  
    MORNING_END = time(12, 0)   
    EVENING_START = time(16, 0) 
    EVENING_END = time(21, 0)   
    SLOT_DURATION = 30          

    if request.method == 'POST':
        selected_slot_str = request.form.get('selected_slot')
        
        if not selected_slot_str:
            flash('Please select a time slot.', 'warning')
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))

        # Parse the specific date and time selected
        date_part, time_part = selected_slot_str.split('_')
        appointment_date = datetime.strptime(date_part, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(time_part, '%H:%M').time()
        appointment_datetime = datetime.combine(appointment_date, appointment_time)

        # Check for double booking
        existing_appointment = Appointment.query.filter_by(
            doctor_id=doctor_user_id,
            appointment_datetime=appointment_datetime,
            status='Booked'
        ).first()

        if existing_appointment:
            flash('Sorry, that specific time slot has just been booked. Please choose another.', 'warning')
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))

        # Create Appointment
        new_appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_user_id,
            appointment_datetime=appointment_datetime,
            status='Booked'
        )
        db.session.add(new_appointment)
        
        # Notification
        msg = f"New appointment booked by {current_user.patient_profile.full_name} for {appointment_datetime.strftime('%d %b at %I:%M %p')}."
        db.session.add(Notification(user_id=doctor_user_id, message=msg))
        
        db.session.commit()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('patient.dashboard'))

    # --- GET Request: Generate Slots ---
    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]
    
    # 1. Get Doctor's Block Availability (e.g., is he working Morning?)
    avail_blocks = Availability.query.filter(
        Availability.doctor_id == doctor_user_id,
        Availability.available_date.in_(days)
    ).all()
    # Map: "2025-11-20" -> ['morning', 'evening']
    active_blocks = {}
    for block in avail_blocks:
        day_str = block.available_date.isoformat()
        if day_str not in active_blocks: active_blocks[day_str] = []
        active_blocks[day_str].append(block.slot)

    # 2. Get Specific Booked Times
    booked_appts = Appointment.query.filter(
        Appointment.doctor_id == doctor_user_id,
        db.func.date(Appointment.appointment_datetime).in_(days),
        Appointment.status == 'Booked'
    ).all()
    # Set of strings: "2025-11-20_09:30"
    booked_slots = {f"{a.appointment_datetime.strftime('%Y-%m-%d_%H:%M')}" for a in booked_appts}

    # 3. Generate the 30-min slots
    # Structure: generated_slots['2025-11-20']['morning'] = ['08:00', '08:30'...]
    generated_slots = {}

    def make_slots(start, end):
        times = []
        current = datetime.combine(today, start)
        end_dt = datetime.combine(today, end)
        while current < end_dt:
            times.append(current.time().strftime('%H:%M'))
            current += timedelta(minutes=SLOT_DURATION)
        return times

    morning_times = make_slots(MORNING_START, MORNING_END)
    evening_times = make_slots(EVENING_START, EVENING_END)

    for day in days:
        day_str = day.isoformat()
        generated_slots[day_str] = {'morning': [], 'evening': []}
        
        if day_str in active_blocks:
            # If doctor works morning, add 30-min morning slots
            if 'morning' in active_blocks[day_str]:
                for t in morning_times:
                    slot_key = f"{day_str}_{t}"
                    if slot_key not in booked_slots: # Only add if NOT booked
                        generated_slots[day_str]['morning'].append(t)
            
            # If doctor works evening, add 30-min evening slots
            if 'evening' in active_blocks[day_str]:
                for t in evening_times:
                    slot_key = f"{day_str}_{t}"
                    if slot_key not in booked_slots:
                        generated_slots[day_str]['evening'].append(t)

    return render_template(
        'patient/book_appointment.html', 
        title='Book Appointment', 
        form=form, 
        doctor=doctor_profile, 
        days=days,
        generated_slots=generated_slots
    )

@patient_bp.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.patient_id != current_user.id:
        flash('You are not authorized to cancel this appointment.', 'danger')
        return redirect(url_for('patient.dashboard'))

    appointment.status = 'Cancelled'
    db.session.commit()
    flash('Your appointment has been successfully cancelled.', 'info')
    return redirect(url_for('patient.dashboard'))

@patient_bp.route('/api/doctor/<int:doctor_id>/availability')
@login_required
def doctor_availability_api(doctor_id):
    """
    API endpoint to return available appointment slots for a doctor on a given date.
    Returns data in JSON format.
    """
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date parameter is required'}), 400

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    day_of_week = selected_date.strftime('%A')

    doctor_schedule = Availability.query.filter_by(doctor_id=doctor_id, day_of_week=day_of_week).all()
    if not doctor_schedule:
        return jsonify({'available_slots': []}) 

    booked_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        db.func.date(Appointment.appointment_datetime) == selected_date,
        Appointment.status == 'Booked'
    ).all()
    booked_times = {appt.appointment_datetime.time() for appt in booked_appointments}

    available_slots = []
    slot_duration = timedelta(minutes=60) 

    for schedule in doctor_schedule:
        current_time = datetime.combine(selected_date, schedule.start_time)
        end_time = datetime.combine(selected_date, schedule.end_time)
        
        while current_time + slot_duration <= end_time:
            if current_time.time() not in booked_times:
                available_slots.append(current_time.strftime('%H:%M'))
            current_time += slot_duration
            
    return jsonify({'available_slots': available_slots})

