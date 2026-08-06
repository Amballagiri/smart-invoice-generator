from app import create_app
from app.extensions import db
from app.models import User, Customer, Invoice
from datetime import date
from decimal import Decimal

app = create_app({
    'TESTING': True,
    'WTF_CSRF_ENABLED': False,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'SECRET_KEY': 'test-secret'
})

with app.app_context():
    db.create_all()
    user = User(username='owner', email='owner@example.com')
    user.set_password('secure-password')
    db.session.add(user)
    db.session.commit()
    customer = Customer(
        name='Acme Ltd',
        email='contact@acme.test',
        phone='9999999999',
        address='123 Main Street',
        city='Mumbai',
        state='MH',
        postal_code='400001',
        country='India',
        user=user,
    )
    db.session.add(customer)
    db.session.commit()
    invoice = Invoice(
        customer=customer,
        created_by=user,
        invoice_date=date.today(),
        due_date=date.today(),
        status='Draft',
        notes='Thank you for your business',
        currency='INR',
        payment_method='Bank transfer',
        template_name='Modern Blue',
        round_off=Decimal('0.00'),
        discount=Decimal('10.00'),
        gst_total=Decimal('27.00'),
        grand_total=Decimal('317.00'),
    )
    db.session.add(invoice)
    db.session.commit()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
    response = client.get(f'/invoices/{invoice.id}')
    print('STATUS', response.status_code)
    print('HAS_CSS', b'invoice_detail.css' in response.data)
    print('HAS_TITLE', b'Invoice detail' in response.data)
    print('HAS_INVOICE_NUMBER', invoice.invoice_number.encode() in response.data)
