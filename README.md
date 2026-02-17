# 🏥 HealNest – Hospital Management System

HealNest is a full-stack hospital management system built with Flask.  
It provides role-based dashboards for Admins, Doctors, and Patients, enabling streamlined appointment scheduling, medical record management, and department administration.

---

## 🚀 Live Features

### 👤 Patient
- Register & secure authentication
- Book appointments (7-day availability system)
- View upcoming & past appointments
- Medical history with printable prescriptions
- Profile management

### 🩺 Doctor
- Manage availability (morning/evening slots)
- Treat patients & add diagnosis/prescriptions
- View assigned patients
- Professional dashboard with smart grouping

### 🛠 Admin
- Manage doctors
- Manage patients
- Manage departments
- Monitor appointments
- Role-based access control

---

## 🎨 UI Highlights

- Premium UI system (`ui-system.css`)
- Unified design system across all pages
- Role-aware navbar
- Dynamic footer (Marketing + App modes)
- Responsive design
- Professional printable prescriptions
- Smart slot grouping (Morning / Evening)
- Auto-disable past slots

---

## 🧱 Tech Stack

- **Backend:** Flask 3
- **Database:** SQLite (Production-ready for PostgreSQL)
- **ORM:** SQLAlchemy
- **Authentication:** Flask-Login
- **Migrations:** Flask-Migrate / Alembic
- **Frontend:** Bootstrap 5 + Custom UI System
- **WSGI Server:** Gunicorn
- **Deployment:** Render

---

## ⚙️ Installation (Local Development)

```bash
git clone https://github.com/your-username/healnest.git
cd healnest

python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Mac/Linux

pip install -r requirements.txt
python run.py
