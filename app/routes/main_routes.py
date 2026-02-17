from flask import render_template, url_for, flash, redirect, request
from flask_login import (
    login_user,
    current_user,
    logout_user,
    login_required
)
from sqlalchemy import or_

from app import db, bcrypt, models
from app.forms import (
    RegistrationForm,
    LoginForm,
    RequestResetForm,
    ResetPasswordForm
)

from . import main_bp
from app.routes.main_routes import *


# ---------------------------
# Home
# ---------------------------
@main_bp.route("/")
@main_bp.route("/home")
def home():
    
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif current_user.role == "doctor":
            return redirect(url_for("doctor.dashboard"))
        else:
            return redirect(url_for("patient.dashboard"))

    return render_template("home.html", title="Home")


# ---------------------------
# Registration
# ---------------------------
@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = models.User(
            email=form.email.data,
            role="patient"
        )
        user.set_password(form.password.data)  # uses setter

        db.session.add(user)
        db.session.flush()  # gets user.id without committing

        profile = models.PatientProfile(
            user_id=user.id,
            full_name=form.email.data
        )
        db.session.add(profile)
        db.session.commit()

        flash("Your account has been created! You can now log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", title="Register", form=form)


# ---------------------------
# Login
# ---------------------------
@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()

    if form.validate_on_submit():
        user = models.User.query.filter_by(email=form.email.data).first()

        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):

             #  BLOCK deleted users FIRST
            if user.is_deleted:
                flash("This account has been deleted.", "danger")
                return redirect(url_for("main.login"))

            #  BLOCK inactive users
            if not user.is_active:
                flash("Your account is inactive.", "danger")
                return redirect(url_for("main.login"))

            if not user.is_active:
                flash("Your account is inactive.", "danger")
                return redirect(url_for("main.login"))


            login_user(user, remember=form.remember.data)

            #  FORCE password change ONLY for doctors
            if (
                user.role == "doctor"
                and user.must_change_password
            ):
                flash("Please change your temporary password.", "warning")
                return redirect(url_for("doctor.change_password"))

            next_page = request.args.get("next")

            if user.role == "admin":
                return redirect(next_page or url_for("admin.dashboard"))
            elif user.role == "doctor":
                return redirect(next_page or url_for("doctor.dashboard"))
            else:
                return redirect(next_page or url_for("patient.dashboard"))

        flash("Login unsuccessful. Please check email and password.", "danger")

    return render_template("login.html", title="Login", form=form)



# ---------------------------
# Logout
# ---------------------------
@main_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.home"))


@main_bp.route("/search")
@login_required
def search():
    query = request.args.get("query", "", type=str).strip()

    if not query:
        flash("Please enter a search term.", "warning")
        return redirect(request.referrer or url_for("main.home"))

    if current_user.role == "admin":

        # ================= PATIENT SEARCH =================
        patients = (
            models.PatientProfile.query
            .join(models.User)
            .filter(
                models.User.is_deleted == False,
                or_(
                    models.PatientProfile.full_name.ilike(f"%{query}%"),
                    models.User.email.ilike(f"%{query}%")
                )
            )
            .all()
        )

        # ================= DOCTOR SEARCH =================
        doctors = (
            models.DoctorProfile.query
            .join(models.User)
            .join(models.Department)
            .filter(
                models.User.is_deleted == False,
                or_(
                    models.DoctorProfile.full_name.ilike(f"%{query}%"),
                    models.User.email.ilike(f"%{query}%"),
                    models.Department.name.ilike(f"%{query}%")
                )
            )
            .all()
        )

        return render_template(
            "admin/search_results.html",
            query=query,
            patients=patients,
            doctors=doctors,
        )

    flash("Search is not available for your role.", "info")
    return redirect(request.referrer or url_for("main.home"))


# ---------------------------
# Notifications
# ---------------------------
@main_bp.route("/notifications")
@login_required
def notifications():
    all_notifications = (
        models.Notification.query
        .filter_by(user_id=current_user.id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )

    for notification in current_user.notifications:
        notification.is_read = True

    db.session.commit()

    return render_template(
        "notifications.html",
        title="My Notifications",
        notifications=all_notifications,
    )


# ---------------------------
# Password Reset
# ---------------------------
@main_bp.route("/reset_password", methods=["GET", "POST"])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RequestResetForm()

    if form.validate_on_submit():
        user = models.User.query.filter_by(email=form.email.data).first()

        if user:
            token = user.get_reset_token()
            reset_link = url_for(
                "main.reset_token", token=token, _external=True
            )
            print("\n--- PASSWORD RESET LINK ---")
            print(reset_link)
            print("--------------------------\n")

        flash(
            "If an account exists, reset instructions have been sent.",
            "info",
        )
        return redirect(url_for("main.login"))

    return render_template(
        "request_reset.html",
        title="Reset Password",
        form=form,
    )


@main_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    user = models.User.verify_reset_token(token)

    if user is None:
        flash("Invalid or expired token.", "warning")
        return redirect(url_for("main.reset_request"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.password = form.password.data
        db.session.commit()

        flash(
            "Your password has been updated! You can now log in.",
            "success",
        )
        return redirect(url_for("main.login"))

    return render_template(
        "reset_token.html",
        title="Reset Password",
        form=form,
    )

