from app import app, db, bcrypt # Add bcrypt to the import
from app.models import User

if __name__ == '__main__':
    with app.app_context():
        # This will create all tables based on your models.py
        db.create_all()
        print("Database tables created.")

        # Check if the admin user exists
        if not User.query.filter_by(email='admin@hms.com').first():
            print("Admin user not found, creating one...")
            
            # Use the explicit bcrypt function to generate a secure hash
            hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
            
            admin_user = User(
                email='admin@hms.com',
                password_hash=hashed_password, # Store the hash directly
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists.")

    # Run the Flask app
    app.run(debug=True)



