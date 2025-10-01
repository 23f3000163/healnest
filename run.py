from app import app, db
from app.models import User

# This block allows us to run commands within the application context
with app.app_context():
    # Create all database tables based on the models in models.py
    db.create_all()

    # Check if the admin user already exists to avoid creating duplicates
    if not User.query.filter_by(role='admin').first():
        print("Admin user not found, creating one...")
        # Create a new User object for the admin
        admin_user = User(
            email='admin@hms.com',
            role='admin'
        )
        # Set the password using the property setter which handles hashing
        admin_user.password = 'password123' # Change this to a secure password
        
        # Add the new admin user to the session and commit to the database
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created successfully!")
    else:
        print("Admin user already exists.")


# This is the standard entry point for running a Flask app
if __name__ == '__main__':
    app.run(debug=True)