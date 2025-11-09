from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app.models import Appointment, Treatment, Availability, User, DoctorProfile, Department, Notification
from . import doctor_bp
from datetime import datetime, date, time, timedelta
from app.forms import TreatmentForm, UpdateAvailabilityForm, BookingForm
from app import db
from sqlalchemy import or_

@doctor_bp.route('/dashboard')
@login_required
def dashboard():
    """
    This route displays the doctor's dashboard, showing:
    1. A list of ALL upcoming (future) appointments.
    2. A master list of all patients assigned to this doctor.
    """
    if current_user.role != 'doctor':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))

    # --- 1. THIS IS THE CORRECTED QUERY ---
    # We now fetch all appointments from 'now' onwards, not just 'today'.
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.status == 'Booked',
        Appointment.appointment_datetime >= datetime.now() # Get all future appointments
    ).order_by(Appointment.appointment_datetime.asc()).all()

    # --- 2. Get All Assigned Patients ---
    assigned_patients = db.session.query(User).join(Appointment, User.id == Appointment.patient_id)\
        .filter(Appointment.doctor_id == current_user.id)\
        .distinct().all()

    # --- 3. Render the template with both lists ---
    return render_template(
        'doctor/dashboard.html', 
        title='Doctor Dashboard', 
        appointments=upcoming_appointments, # Pass the new list
        patients=assigned_patients
    )

@doctor_bp.route('/treat/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def treat_patient(appointment_id):
    """
    This route handles viewing a patient's history and submitting
    a new treatment to complete an appointment.
    """
    if current_user.role != 'doctor':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != current_user.id:
        flash('You are not authorized to treat this patient.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    patient_history = Appointment.query.filter(
        Appointment.patient_id == appointment.patient_id,
        Appointment.status == 'Completed'
    ).order_by(Appointment.appointment_datetime.desc()).all()

    form = TreatmentForm()

    if form.validate_on_submit():
        new_treatment = Treatment(
            appointment_id=appointment.id,
            visit_type=form.visit_type.data,
            tests_done=form.tests_done.data,
            diagnosis=form.diagnosis.data,
            prescription=form.prescription.data
        )
        db.session.add(new_treatment)
        
        appointment.status = 'Completed'
        
        # Create notification for patient
        doctor_name = current_user.doctor_profile.full_name
        notification_message = f"Dr. {doctor_name} has completed your appointment and added treatment details."
        new_notification = Notification(
            user_id=appointment.patient_id,
            message=notification_message
        )
        db.session.add(new_notification)

        db.session.commit()
        flash('Treatment has been recorded and the appointment is marked as completed.', 'success')
        return redirect(url_for('doctor.dashboard'))

    return render_template(
        'doctor/treat_patient.html', 
        title='Treat Patient', 
        form=form, 
        appointment=appointment, 
        patient_history=patient_history
    )

@doctor_bp.route('/availability', methods=['GET', 'POST'])
@login_required
def set_availability():
    """
    This is the NEW availability route that works with the new database model.
    It shows the next 7 days and saves 'morning'/'evening' slots.
    """
    if current_user.role != 'doctor':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    # Get the next 7 days starting from today
    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]

    if request.method == 'POST':
        # 1. Clear all *future* availability for this doctor
        Availability.query.filter(
            Availability.doctor_id == current_user.id,
            Availability.available_date >= today
        ).delete()

        # 2. Get all the checked slots from the form
        selected_slots = request.form.getlist('slots')
        
        # 3. Add the new availability slots
        for slot_str in selected_slots:
            date_str, slot_type = slot_str.split('_')
            available_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            new_slot = Availability(
                doctor_id=current_user.id,
                available_date=available_date,
                slot=slot_type  # e.g., 'morning' or 'evening'
            )
            db.session.add(new_slot)
        
        db.session.commit()
        flash('Your availability has been updated!', 'success')
        return redirect(url_for('doctor.set_availability'))

    # For a GET request, get the doctor's currently saved availability
    saved_slots = Availability.query.filter(
        Availability.doctor_id == current_user.id,
        Availability.available_date.in_(days)
    ).all()
    
    # Create a set of strings (e.g., "2025-11-09_morning") for easy checking in the template
    saved_slots_set = {f"{slot.available_date.isoformat()}_{slot.slot}" for slot in saved_slots}

    return render_template(
        'doctor/set_availability.html', 
        title='Set Availability', 
        days=days, 
        saved_slots=saved_slots_set
    )

@doctor_bp.route('/patient_history/<int:user_id>')
@login_required
def view_patient_history(user_id):
    """
    Shows a read-only view of a specific patient's complete history
    for the logged-in doctor.
    """
    if current_user.role != 'doctor':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    
    # Get the patient's User object
    patient = User.query.get_or_404(user_id)
    if patient.role != 'patient':
        flash('This user is not a patient.', 'warning')
        return redirect(url_for('doctor.dashboard'))

    # Get all COMPLETED appointments for this patient WITH THIS doctor
    patient_history = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.doctor_id == current_user.id, # Ensure doctor can only see their own history
        Appointment.status == 'Completed'
    ).order_by(Appointment.appointment_datetime.desc()).all()

    return render_template(
        'doctor/patient_history.html',
        title=f"History for {patient.patient_profile.full_name}",
        patient=patient,
        history=patient_history
    )