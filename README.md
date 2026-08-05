# Smart Invoice Generator

A Flask-based Smart Invoice Generator that helps businesses manage customers, products, and invoices efficiently.

## Features

- 🔐 User Authentication (Login & Registration)
- 👥 Customer Management
- 📦 Product Management
- 🧾 Invoice Creation
- 📄 PDF Invoice Generation
- 🔍 Search and Filter
- 📊 Invoice Dashboard
- 💾 SQLite Database
- ✅ WTForms Validation
- 🔒 Secure Password Hashing

## Tech Stack

- Python 3
- Flask
- SQLAlchemy
- SQLite
- WTForms
- Bootstrap 5
- ReportLab
- Alembic
- Git & GitHub

## Project Structure

```
Smart Invoice Generator
│
├── app/
│   ├── models/
│   ├── routes/
│   ├── forms/
│   ├── services/
│   ├── templates/
│   └── static/
│
├── migrations/
├── tests/
├── requirements.txt
└── wsgi.py
```

## Installation

Clone the repository:

```bash
git clone https://github.com/Amballagiri/smart-invoice-generator.git
```

Go to the project folder:

```bash
cd smart-invoice-generator
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### Windows

```bash
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
flask --app wsgi run --debug
```

Open your browser:

```
http://127.0.0.1:5000
```

## Current Modules

- Authentication
- Customer Management
- Product Management
- Invoice Management
- PDF Invoice Generation

## Future Enhancements

- Email Invoice
- Sales Dashboard
- Excel Export
- Inventory Alerts
- GST Reports
- Online Deployment

## Author

**Amballa Giri**

GitHub:
https://github.com/Amballagiri

---

⭐ If you like this project, consider giving it a star!
