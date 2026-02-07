from app import app, db, bcrypt 
from app.models import User

if __name__ == '__main__':
    # with app.app_context():
    #     db.create_all()
    #     print("Database tables created.")

    #     if not User.query.filter_by(email='admin@hms.com').first():
    #         print("Admin user not found, creating one...")
            
        
    #         hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
            
    #         admin_user = User(
    #             email='admin@hms.com',
    #             password_hash=hashed_password, 
    #             role='admin'
    #         )
    #         db.session.add(admin_user)
    #         db.session.commit()
            print("Admin user created successfully!")
else:
            print("Admin user already exists.")

app.run(debug=True)



