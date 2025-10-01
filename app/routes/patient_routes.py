from flask import render_template, flash, redirect, url_for, request # Add request
from flask_login import login_required, current_user
from app.models import Department, Appointment, DoctorProfile, User # Add DoctorProfile and User
from . import patient_bp
from datetime import datetime
from app.forms import BookingForm # Add this new import
from app import db # Add this new import
from app.forms import BookingForm, UpdateProfileForm # Add UpdateProfileForm here

@patient_bp.route('/dashboard')
@login_required
def dashboard():
    # Ensure the logged-in user is a patient
    if current_user.role != 'patient':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
        
    # Query all departments to display for booking
    departments = Department.query.all()
    
    # Get all appointments for the current patient
    all_appointments = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.appointment_datetime.desc()).all()
    
    # Separate appointments into upcoming and past
    upcoming_appointments = []
    past_appointments = []
    
    for appt in all_appointments:
        if appt.appointment_datetime >= datetime.now() and appt.status == 'Booked':
            upcoming_appointments.append(appt)
        else:
            past_appointments.append(appt)
    
    return render_template(
        'patient/dashboard.html', 
        title='My Dashboard', 
        departments=departments,
        upcoming_appointments=upcoming_appointments,
        past_appointments=past_appointments
    )

# The routes for booking and canceling appointments will be added next

# ... (keep your existing dashboard route at the top) ...

@patient_bp.route('/book/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def book_appointment(doctor_id):
    # This function handles both showing the booking page (GET) and processing the booking (POST)

    # First, make sure the user is a patient
    if current_user.role != 'patient':
        flash('Only patients can book appointments.', 'danger')
        return redirect(url_for('main.home'))

    # Get the profile of the doctor being booked
    doctor_profile = DoctorProfile.query.get_or_404(doctor_id)
    form = BookingForm()

    # This block runs ONLY when the user submits the form
    if form.validate_on_submit():
        # Combine the date and time from the form into a single datetime object
        appointment_datetime = datetime.combine(form.appointment_date.data, form.appointment_time.data)

        # CRITICAL CHECK: See if this doctor already has an appointment at this exact time
        existing_appointment = Appointment.query.filter_by(
            doctor_id=doctor_profile.user_id,
            appointment_datetime=appointment_datetime,
            status='Booked' # Only check against currently booked appointments
        ).first()

        if existing_appointment:
            # If a booking exists, show a warning and redirect back to the booking page
            flash('This time slot is already booked. Please choose a different time.', 'warning')
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))

        # If the time slot is free, create the new appointment
        new_appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_profile.user_id,
            appointment_datetime=appointment_datetime,
            status='Booked'
        )
        # Save the new appointment to the database
        db.session.add(new_appointment)
        db.session.commit()

        flash('Your appointment has been successfully booked!', 'success')
        return redirect(url_for('patient.dashboard'))

    # This part runs when the user first visits the page (a GET request)
    # It just shows the booking form
    return render_template('patient/book_appointment.html', title='Book Appointment', form=form, doctor=doctor_profile)

# ... (keep all your existing routes, like dashboard and book_appointment, above this) ...

@patient_bp.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    """
    This route handles the cancellation of an appointment.
    It only accepts POST requests for security.
    """

    # Step A: Find the specific appointment in the database using its ID.
    # If no appointment with this ID is found, it will automatically show a 404 Not Found page.
    appointment = Appointment.query.get_or_404(appointment_id)

    # Step B: CRITICAL Security Check.
    # Verify that the person trying to cancel the appointment is the same person who booked it.
    # This prevents users from cancelling other people's appointments.
    if appointment.patient_id != current_user.id:
        flash('You are not authorized to cancel this appointment.', 'danger')
        return redirect(url_for('patient.dashboard'))

    # Step C: Update the appointment's status.
    appointment.status = 'Cancelled'

    # Step D: Save the change to the database.
    db.session.commit()

    # Step E: Show a confirmation message and redirect the user back to their dashboard.
    flash('Your appointment has been successfully cancelled.', 'info')
    return redirect(url_for('patient.dashboard'))

# ... (keep your existing routes: dashboard, book_appointment, cancel_appointment) ...

@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    This route handles viewing and updating the patient's own profile.
    """
    # Step A: Security check to ensure user is a patient.
    if current_user.role != 'patient':
        return redirect(url_for('main.home'))

    # Step B: Get the patient's profile from the database.
    # The 'patient_profile' relationship we defined in models.py makes this easy.
    profile = current_user.patient_profile
    
    # Step C: Create an instance of our form.
    # The `obj=profile` argument is the key: it tells the form to
    # pre-populate all its fields with the data from the 'profile' object.
    form = UpdateProfileForm(obj=profile)

    # Step D: This block runs only when the user submits the form.
    if form.validate_on_submit():
        # Update the profile object in memory with the new data from the form.
        profile.full_name = form.full_name.data
        profile.date_of_birth = form.date_of_birth.data
        profile.gender = form.gender.data
        profile.contact_number = form.contact_number.data
        profile.blood_group = form.blood_group.data
        profile.allergies = form.allergies.data

        # Step E: Save the updated profile to the database.
        db.session.commit()
        
        # Step F: Show a success message and reload the page.
        flash('Your profile has been updated successfully!', 'success')
        return redirect(url_for('patient.profile'))

    # Step G: If it's a GET request (the user is just visiting the page),
    # render the template and pass in the pre-populated form.
    return render_template('patient/profile.html', title='My Profile', form=form)

