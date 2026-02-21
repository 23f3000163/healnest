"""
Admin Account Creation Script for HealNest

This script creates an admin account for the first time setup.
Use this before deploying to production.

Usage:
    python create_admin.py
"""

from app import app, db
from app.models import User

# Push app context
app.app_context().push()

def create_admin():
    """Create admin account interactively"""
    
    print("\n" + "="*50)
    print("HealNest - Admin Account Creation")
    print("="*50 + "\n")
    
    # Get admin email
    while True:
        admin_email = input("Enter admin email: ").strip()
        
        if not admin_email or "@" not in admin_email:
            print("❌ Invalid email format. Try again.")
            continue
            
        existing = User.query.filter_by(email=admin_email).first()
        if existing:
            print(f"❌ Account already exists: {admin_email}")
            print("   Try a different email.")
            continue
            
        break
    
    # Get password
    while True:
        password = input("Enter admin password (min 8 chars): ").strip()
        
        if len(password) < 8:
            print("❌ Password must be at least 8 characters.")
            continue
            
        confirm = input("Confirm password: ").strip()
        if password != confirm:
            print("❌ Passwords don't match. Try again.")
            continue
            
        break
    
    # Create admin
    try:
        admin_user = User(
            email=admin_email,
            role="admin",
            is_active=True,
            is_deleted=False,
            is_temp_password=False,
            must_change_password=False
        )
        admin_user.set_password(password)
        
        db.session.add(admin_user)
        db.session.commit()
        
        print("\n" + "="*50)
        print("✅ Admin Account Created Successfully!")
        print("="*50)
        print(f"📧 Email: {admin_email}")
        print(f"🔐 Password: {'*' * len(password)}")
        print("\n💡 Next Steps:")
        print("   1. Login at /login")
        print("   2. Access admin dashboard")
        print("   3. Create doctors and manage system")
        print("="*50 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating admin: {str(e)}")
        db.session.rollback()
        return False


if __name__ == "__main__":
    create_admin()
