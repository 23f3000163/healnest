# 🏥 HealNest: Production-Ready Hospital Management System

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-green?style=for-the-badge&logo=flask&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-purple?style=for-the-badge&logo=bootstrap&logoColor=white)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge)

> **A modular, scalable, and secure full-stack Hospital Management System built with Flask.**

---

## 📌 Overview

**HealNest** is a full-stack Hospital Management System designed with a focus on modular architecture and scalability. It supports role-based dashboards, smart appointment scheduling, and patient medical records, all wrapped in a unified premium UI system.

Unlike typical academic projects, HealNest is structured for **production deployment**. It demonstrates real-world backend patterns including Blueprint routing, factory patterns, and secure role-based access control.

---

## ✨ Key Features

### 👥 Role-Based Access Control
The system features distinct dashboards and permissions for three key roles:

| **🛠 Admin** | **🩺 Doctor** | **👤 Patient** |
| :--- | :--- | :--- |
| • Manage Doctors & Patients<br>• Manage Departments<br>• View Global Appointments<br>• Admin Dashboard | • Set Availability (Next 7 days)<br>• Morning/Evening Slot Grouping<br>• Add Diagnosis & Prescriptions<br>• View Patient History | • Secure Registration & Login<br>• Book Appointments (Smart 7-Day)<br>• View History & Print Rx<br>• Profile Management |

### 📅 Smart Appointment System
* **7-Day Window:** Only shows availability for the upcoming week to prevent scheduling conflicts.
* **Auto-Expiry:** Expired slots are automatically disabled.
* **Slot Grouping:** Intuitive Morning/Evening segmentation.
* **Safety:** Confirmation modals before booking actions.

### 🎨 Premium UI System
Built on **Bootstrap 5**, HealNest features a custom design layer:
* Dynamic Footer (Marketing vs. App mode).
* Role-aware navigation bars.
* Professional, printable prescription layouts.
* Clean, card-based dashboard design with subtle animations.

---

## ⚙️ Tech Stack

HealNest relies on a robust, industry-standard stack:

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Backend** | **Flask 3** | Core framework |
| **ORM** | **SQLAlchemy** | Database interactions |
| **Auth** | **Flask-Login** | Session management & Security |
| **Forms** | **WTForms** | Data validation & CSRF protection |
| **Migrations**| **Flask-Migrate** | Alembic-based database schema tracking |
| **Frontend** | **Bootstrap 5** | Responsive UI + Custom CSS Layer |
| **Server** | **Gunicorn** | Production WSGI Server |
| **Database** | **SQLite** | Dev (PostgreSQL ready for Prod) |

---

## 🧠 Architecture & Structure

HealNest follows the **Application Factory Pattern** and uses **Blueprints** to keep code modular.

```text
healnest/
│
├── app/
│   ├── routes/          # Blueprint routes (auth, main, doctor, etc.)
│   ├── templates/       # HTML Templates (Jinja2)
│   ├── static/          # CSS, JS, Images
│   ├── models.py        # Database Models
│   └── __init__.py      # App Factory Setup
│
├── migrations/          # Alembic Migration Versions
├── instance/            # Instance-specific config (ignored by Git)
├── run.py               # Entry point
├── requirements.txt     # Dependencies
├── Procfile             # Render/Heroku Deployment
└── README.md            # Documentation


---

## 🚀 Local Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/healnest.git](https://github.com/your-username/healnest.git)
cd healnest

2. Create Virtual Environment

Windows:
python -m venv venv
.\venv\Scripts\activate

Mac/Linux:
python3 -m venv venv
source venv/bin/activate

3. Install Dependencies
pip install -r requirements.txt

4. Initialize Database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

5. Run the Application
