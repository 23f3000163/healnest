from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app.models import Appointment, Treatment, Availability, Notification
from . import doctor_bp
from datetime import datetime
from app.forms import TreatmentForm, UpdateAvailabilityForm
from app import db

@doctor_bp.route('/dashboard')
@login_required
def dashboard():
    """
    This route displays the doctor's dashboard, showing a list of
    their upcoming appointments.
    """
    if current_user.role != 'doctor':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))

    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.status == 'Booked',
        Appointment.appointment_datetime >= datetime.now()
    ).order_by(Appointment.appointment_datetime.asc()).all()

    return render_template(
        'doctor/dashboard.html', 
        title='Doctor Dashboard', 
        appointments=upcoming_appointments
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
    
    # Security check: ensure the doctor owns this appointment
    if appointment.doctor_id != current_user.id:
        flash('You are not authorized to treat this patient.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    # Get patient's past completed appointments for their history
    patient_history = Appointment.query.filter(
        Appointment.patient_id == appointment.patient_id,
        Appointment.status == 'Completed'
    ).order_by(Appointment.appointment_datetime.desc()).all()

    form = TreatmentForm()

    if form.validate_on_submit():
        # Create a new treatment record
        new_treatment = Treatment(
            appointment_id=appointment.id,
            diagnosis=form.diagnosis.data,
            prescription=form.prescription.data
        )
        db.session.add(new_treatment)
        
        # Update the appointment status to 'Completed'
        appointment.status = 'Completed'
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
    if current_user.role != 'doctor':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    form = UpdateAvailabilityForm()

    if form.validate_on_submit():
        # Easiest way to update is to delete old slots and create new ones
        Availability.query.filter_by(doctor_id=current_user.id).delete()
        
        for slot_data in form.slots.data:
            if slot_data['start_time'] and slot_data['end_time']: # Ensure slot is not empty
                new_slot = Availability(
                    doctor_id=current_user.id,
                    day_of_week=slot_data['day_of_week'],
                    start_time=slot_data['start_time'],
                    end_time=slot_data['end_time']
                )
                db.session.add(new_slot)
        
        db.session.commit()
        flash('Your availability has been updated successfully!', 'success')
        return redirect(url_for('doctor.set_availability'))

    # Pre-populate the form with existing availability slots
    existing_slots = Availability.query.filter_by(doctor_id=current_user.id).all()
    if not request.method == 'POST' and existing_slots:
        form.slots.entries = [] # Clear default entry
        for slot in existing_slots:
            form.slots.append_entry(slot)
            
    return render_template('doctor/set_availability.html', title='Set Availability', form=form)