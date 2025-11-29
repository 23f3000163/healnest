from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app.models import Appointment, Treatment, Availability, User, DoctorProfile, Department, Notification
from . import doctor_bp
from datetime import datetime, date, time, timedelta
from app.forms import TreatmentForm, UpdateAvailabilityForm, BookingForm, DoctorUpdateProfileForm
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
        Appointment.appointment_datetime >= datetime.now() 
    ).order_by(Appointment.appointment_datetime.asc()).all()

    # --- 2. Get All Assigned Patients ---
    assigned_patients = db.session.query(User).join(Appointment, User.id == Appointment.patient_id)\
        .filter(Appointment.doctor_id == current_user.id)\
        .distinct().all()

    # --- 3. Render the template with both lists ---
    return render_template(
        'doctor/dashboard.html', 
        title='Doctor Dashboard', 
        appointments=upcoming_appointments, 
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
    if current_user.role != 'doctor':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('doctor.dashboard'))
    
    patient = User.query.get_or_404(user_id)
    if patient.role != 'patient':
        flash('This user is not a patient.', 'warning')
        return redirect(url_for('doctor.dashboard'))

    # Doctor sees only appointments THEY completed for this patient
    patient_history = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.doctor_id == current_user.id,
        Appointment.status == 'Completed'
    ).order_by(Appointment.appointment_datetime.desc()).all()

    # --- NEW: Calculate Patient Age ---
    patient_age = None
    if patient.patient_profile and patient.patient_profile.date_of_birth:
        today = date.today()
        patient_age = today.year - patient.patient_profile.date_of_birth.year - \
                      ((today.month, today.day) < (patient.patient_profile.date_of_birth.month, patient.patient_profile.date_of_birth.day))

    return render_template(
        'admin/patient_history.html', # Reusing the smart template
        title=f"History for {patient.patient_profile.full_name}",
        patient=patient,
        history=patient_history,
        patient_age=patient_age, # Pass the new age variable
        back_url=url_for('doctor.dashboard')
    )

@doctor_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    Handles viewing and updating the doctor's own profile.
    """
    if current_user.role != 'doctor':
        return redirect(url_for('main.home'))

    profile = current_user.doctor_profile
    form = DoctorUpdateProfileForm(obj=profile)

    if form.validate_on_submit():
        profile.full_name = form.full_name.data
        profile.contact_number = form.contact_number.data
        profile.qualifications = form.qualifications.data
        # Save new fields
        try:
            profile.experience_years = int(form.experience_years.data) if form.experience_years.data else 0
        except ValueError:
            profile.experience_years = 0 # Handle non-integer input safely
            
        profile.bio = form.bio.data
        
        db.session.commit()
        flash('Your profile has been updated successfully!', 'success')
        return redirect(url_for('doctor.profile'))

    return render_template('doctor/profile.html', title='My Profile', form=form)

@doctor_bp.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    """
    Allows a doctor to cancel an upcoming appointment.
    """
    if current_user.role != 'doctor':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    appointment = Appointment.query.get_or_404(appointment_id)

    # Security Check: Ensure the appointment belongs to this doctor
    if appointment.doctor_id != current_user.id:
        flash('You cannot cancel an appointment that does not belong to you.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    # Update Status
    appointment.status = 'Cancelled'

    # Professional Touch: Notify the patient
    patient_msg = f"Dr. {current_user.doctor_profile.full_name} has cancelled your appointment scheduled for {appointment.appointment_datetime.strftime('%d %b at %I:%M %p')}."
    notification = Notification(user_id=appointment.patient_id, message=patient_msg)
    db.session.add(notification)

    db.session.commit()
    flash('Appointment cancelled successfully. The patient has been notified.', 'info')
    
    return redirect(url_for('doctor.dashboard'))




