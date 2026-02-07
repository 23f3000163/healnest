from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("main.login"))

        if current_user.role != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("main.home"))

        return func(*args, **kwargs)
    return wrapper


def doctor_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("main.login"))

        if current_user.role != "doctor":
            flash("Doctor access required.", "danger")
            return redirect(url_for("main.home"))

        return func(*args, **kwargs)
    return wrapper
