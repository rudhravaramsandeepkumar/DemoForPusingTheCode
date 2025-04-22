# app.py
from flask import render_template, redirect, request, session, url_for, Flask, jsonify
from flask import send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
from models import init_app, db
from models.user import User
from models.fuel_type import FuelType
from models.order import Order
from models.delivery_schedule import DeliverySchedule
from models.review import Review

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_KEY_PREFIX'] = 'helloo'
app.config['SESSION_COOKIE_NAME'] = 'Bookstorevsession'
app.secret_key = "Kc5c3zTk'-3<&BdL:P92O{_(:-NkY+KLJ"

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
init_app(app)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    from models.user import User
    from datetime import datetime

    error = None

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        if password != confirm_password:
            error = "Passwords do not match"
        elif User.query.filter_by(email=email).first():
            error = "User with this email already exists"
        else:
            user = User(
                username=username,
                email=email,
                password=password,  # Not hashed (per your earlier flows)
                role=role,
                created_at=datetime.now()
            )
            db.session.add(user)
            db.session.commit()
            return redirect('/login')

    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    from models.user import User

    error = None

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            if user.role == 'admin':
                return redirect('/admin/dashboard')
            else:
                return redirect('/user/dashboard')
        else:
            error = "Invalid email or password"

    return render_template('login.html', error=error)


@app.route('/user/dashboard')
def user_dashboard():
    from models.order import Order
    from models.fuel import Fuel
    from models.fuel_type import FuelType
    from models.delivery_schedule import DeliverySchedule

    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect('/login')

    user_id = session['user_id']
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.order_date.desc()).all()

    order_history = []
    for o in orders:
        fuel = Fuel.query.get(o.fuel_id)
        fuel_type = FuelType.query.get(fuel.fuel_type_id) if fuel else None
        delivery_slot = DeliverySchedule.query.get(o.delivery_schedule_id)

        order_history.append({
            'id': o.id,
            'fuel_name': fuel.name if fuel else 'Unknown',
            'type': fuel_type.type_name if fuel_type else 'N/A',
            'price': fuel.price if fuel else 0,
            'quantity': o.quantity,
            'total': round(o.quantity * (fuel.price if fuel else 0), 2),
            'order_date': o.order_date.strftime('%d %b, %Y'),
            'delivery_time': delivery_slot.delivery_time if delivery_slot else 'TBD',
            'status': o.status
        })

    return render_template('user/dashboard.html', orders=order_history, username=session.get('username'))


@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    from models.order import Order
    from models.fuel import Fuel

    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect('/login')

    order_id = request.form.get('order_id')
    order = Order.query.get(order_id)

    if order and order.user_id == session['user_id'] and order.status == 'Pending':
        order.status = 'Cancelled'

        # Restore fuel stock
        fuel = Fuel.query.get(order.fuel_id)
        if fuel:
            fuel.stock += order.quantity

        db.session.commit()

    return redirect('/user/dashboard')


@app.route('/fuel_catalog')
def fuel_catalog():
    from models.fuel import Fuel
    from models.fuel_type import FuelType

    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect('/login')

    fuels = Fuel.query.all()
    fuel_list = []

    for f in fuels:
        fuel_type = FuelType.query.get(f.fuel_type_id)
        fuel_list.append({
            'id': f.id,
            'name': f.name,
            'price': f.price,
            'stock': f.stock,
            'type': fuel_type.type_name if fuel_type else 'Unknown'
        })

    return render_template('user/fuel_catalog.html', fuels=fuel_list)


@app.route('/book_fuel', methods=['GET', 'POST'])
def book_fuel():
    from models.fuel import Fuel
    from models.delivery_schedule import DeliverySchedule
    from models.order import Order
    from datetime import datetime

    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect('/login')

    fuels = Fuel.query.all()
    schedules = DeliverySchedule.query.filter_by(availability=True).all()

    if request.method == 'POST':
        fuel_id = int(request.form['fuel_id'])
        quantity = float(request.form['quantity'])
        address = request.form['address']
        schedule_id = int(request.form['delivery_schedule_id'])

        fuel = Fuel.query.get(fuel_id)
        schedule = DeliverySchedule.query.get(schedule_id)

        if not fuel or not schedule or not schedule.availability:
            return "Invalid fuel or delivery slot.", 400

        if fuel.stock < quantity:
            return "Insufficient stock.", 400

        total_price = fuel.price * quantity
        fuel.stock -= quantity

        order = Order(
            user_id=session['user_id'],
            fuel_id=fuel_id,
            quantity=quantity,
            total_amount=total_price,
            status='Pending',
            address=address,
            delivery_schedule_id=schedule.id,
            order_date=datetime.now()
        )

        db.session.add(order)
        db.session.commit()
        return redirect('/user/dashboard')

    return render_template('user/book_fuel.html', fuels=fuels, schedules=schedules)


@app.route('/add_delivery_schedule', methods=['POST'])
def add_delivery_schedule():
    delivery_time = request.form.get('delivery_time')
    availability = request.form.get('availability') == 'true'

    schedule = DeliverySchedule(
        delivery_time=delivery_time,
        availability=availability
    )
    try:
        db.session.add(schedule)
        db.session.commit()
        db.session.close()
        return jsonify({"message": "Delivery schedule added."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to add delivery schedule", "error": str(e)}), 400


@app.route('/test_seed_fuels', methods=['POST'])
def test_seed_fuels():
    from models.fuel import Fuel
    from models.fuel_type import FuelType

    data = request.get_json()

    if not data or 'fuel_type' not in data or 'fuel' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    # Add fuel type (or get existing)
    fuel_type = FuelType.query.filter_by(type_name=data['fuel_type']).first()
    if not fuel_type:
        fuel_type = FuelType(type_name=data['fuel_type'])
        db.session.add(fuel_type)
        db.session.commit()

    # Add fuel
    fuel_data = data['fuel']
    new_fuel = Fuel(
        name=fuel_data['name'],
        price=fuel_data['price'],
        stock=fuel_data['stock'],
        fuel_type_id=fuel_type.id
    )
    db.session.add(new_fuel)
    db.session.commit()

    return jsonify({'message': 'Fuel type and fuel added successfully'}), 201


@app.route('/fuel_details/<int:id>', methods=['GET', 'POST'])
def fuel_details(id):
    from models.fuel import Fuel
    from models.fuel_type import FuelType
    from models.delivery_schedule import DeliverySchedule
    from models.order import Order
    from datetime import datetime

    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect('/login')

    fuel = Fuel.query.get_or_404(id)
    fuel_type = FuelType.query.get(fuel.fuel_type_id)
    schedules = DeliverySchedule.query.filter_by(availability=True).all()

    if request.method == 'POST':
        quantity = float(request.form['quantity'])
        address = request.form['address']
        schedule_id = int(request.form['delivery_schedule_id'])

        if fuel.stock < quantity:
            return "Insufficient fuel stock", 400

        total_price = fuel.price * quantity
        fuel.stock -= quantity

        order = Order(
            user_id=session['user_id'],
            fuel_id=fuel.id,
            quantity=quantity,
            total_amount=total_price,
            status='Pending',
            delivery_schedule_id=schedule_id,
            order_date=datetime.now(),
            address=address
        )

        db.session.add(order)
        db.session.commit()
        return redirect('/user/dashboard')

    return render_template('user/fuel_details.html', fuel=fuel, fuel_type=fuel_type, schedules=schedules)


# @app.route('/get_order_details/<int:order_id>')
# def get_order_details(order_id):
#     from models.order import Order
#     from models.fuel import Fuel
#     from models.fuel_type import FuelType
#     from models.delivery_schedule import DeliverySchedule
#
#     if 'user_id' not in session:
#         return redirect('/login')
#
#     order = Order.query.get_or_404(order_id)
#
#     if session['role'] != 'admin' and order.user_id != session['user_id']:
#         return "Unauthorized", 403
#
#     fuel = Fuel.query.get(order.fuel_id)
#     fuel_type = FuelType.query.get(fuel.fuel_type_id) if fuel else None
#     delivery = DeliverySchedule.query.get(order.delivery_schedule_id)
#
#     return render_template('user/order_details.html', order=order, fuel=fuel, fuel_type=fuel_type, delivery=delivery)


@app.route('/get_order_details/<int:order_id>')
def get_order_details(order_id):
    from models.order import Order
    from models.fuel import Fuel
    from models.fuel_type import FuelType
    from models.delivery_schedule import DeliverySchedule

    if 'user_id' not in session:
        return redirect('/login')

    order = Order.query.get_or_404(order_id)

    if session['role'] != 'admin' and order.user_id != session['user_id']:
        return "Unauthorized", 403

    fuel = Fuel.query.get(order.fuel_id)
    fuel_type = FuelType.query.get(fuel.fuel_type_id) if fuel else None
    delivery = DeliverySchedule.query.get(order.delivery_schedule_id)

    return render_template(
        'user/order_details.html',
        order=order,
        fuel=fuel,
        fuel_type=fuel_type,
        delivery=delivery
    )


@app.route('/admin/dashboard')
def admin_dashboard():
    from models.order import Order
    from models.user import User
    from sqlalchemy import func

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='Pending').count()
    total_customers = User.query.filter_by(role='customer').count()
    total_revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0

    stats = {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'total_customers': total_customers,
        'total_revenue': round(total_revenue, 2)
    }

    return render_template('admin/dashboard.html', stats=stats)


@app.route('/admin/orders')
def admin_orders():
    from models.order import Order
    from models.user import User
    from models.fuel import Fuel
    from models.fuel_type import FuelType
    from models.delivery_schedule import DeliverySchedule

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    orders = Order.query.order_by(Order.order_date.desc()).all()
    all_orders = []

    for o in orders:
        user = User.query.get(o.user_id)
        fuel = Fuel.query.get(o.fuel_id)
        fuel_type = FuelType.query.get(fuel.fuel_type_id) if fuel else None
        schedule = DeliverySchedule.query.get(o.delivery_schedule_id)

        all_orders.append({
            'id': o.id,
            'customer_name': user.username if user else 'Unknown',
            'fuel_name': f"{fuel.name} ({fuel_type.type_name})" if fuel and fuel_type else 'Unknown',
            'quantity': o.quantity,
            'total': o.total_amount,
            'delivery_time': schedule.delivery_time if schedule else 'N/A',
            'status': o.status
        })

    return render_template('admin/orders.html', orders=all_orders)


@app.route('/admin/mark_delivered', methods=['POST'])
def admin_mark_delivered():
    from models.order import Order

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    order_id = request.form.get('order_id')
    order = Order.query.get(order_id)

    if order and order.status == 'Pending':
        order.status = 'Delivered'
        db.session.commit()

    return redirect('/admin/orders')


@app.route('/admin/cancel_order', methods=['POST'])
def admin_cancel_order():
    from models.order import Order
    from models.fuel import Fuel

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    order_id = request.form.get('order_id')
    order = Order.query.get(order_id)

    if order and order.status == 'Pending':
        order.status = 'Cancelled'

        # Restore stock
        fuel = Fuel.query.get(order.fuel_id)
        if fuel:
            fuel.stock += order.quantity

        db.session.commit()

    return redirect('/admin/orders')


@app.route('/admin/users')
def admin_users():
    from models.user import User

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/delete_user', methods=['POST'])
def admin_delete_user():
    from models.user import User

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    user_id = request.form.get('user_id')

    # Prevent self-deletion
    if int(user_id) == session['user_id']:
        return "You cannot delete your own admin account.", 403

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()

    return redirect('/admin/users')

@app.route('/admin/fuel')
def admin_fuel():
    from models.fuel import Fuel
    from models.fuel_type import FuelType

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    fuels = Fuel.query.all()
    fuel_list = []

    for f in fuels:
        fuel_type = FuelType.query.get(f.fuel_type_id)
        fuel_list.append({
            'id': f.id,
            'name': f.name,
            'price': f.price,
            'stock': f.stock,
            'type_name': fuel_type.type_name if fuel_type else 'N/A'
        })

    return render_template('admin/fuel.html', fuels=fuel_list)


@app.route('/admin/delete_fuel', methods=['POST'])
def delete_fuel():
    from models.fuel import Fuel

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    fuel_id = request.form.get('fuel_id')
    fuel = Fuel.query.get(fuel_id)

    if fuel:
        db.session.delete(fuel)
        db.session.commit()

    return redirect('/admin/fuel')


@app.route('/admin/add_fuel', methods=['GET', 'POST'])
def add_fuel():
    from models.fuel import Fuel
    from models.fuel_type import FuelType

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = float(request.form['stock'])
        fuel_type_id = int(request.form['fuel_type_id'])

        new_fuel = Fuel(
            name=name,
            price=price,
            stock=stock,
            fuel_type_id=fuel_type_id
        )
        db.session.add(new_fuel)
        db.session.commit()
        return redirect('/admin/fuel')

    fuel_types = FuelType.query.all()
    return render_template('admin/add_fuel.html', fuel_types=fuel_types)


@app.route('/admin/update_fuel_stock', methods=['POST'])
def update_fuel_stock():
    from models.fuel import Fuel

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    fuel_id = request.form.get('fuel_id')
    stock = request.form.get('stock')

    fuel = Fuel.query.get(fuel_id)
    if fuel and stock:
        try:
            fuel.stock = float(stock)
            db.session.commit()
        except:
            db.session.rollback()

    return redirect('/admin/fuel')


@app.route('/admin/fuel_types', methods=['GET', 'POST'])
def admin_fuel_types():
    from models.fuel_type import FuelType

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    error_message = None

    if request.method == 'POST':
        type_name = request.form.get('type_name')

        if FuelType.query.filter_by(type_name=type_name).first():
            error_message = "Fuel type already exists."
        else:
            new_type = FuelType(type_name=type_name)
            db.session.add(new_type)
            db.session.commit()
            return redirect('/admin/fuel_types')

    fuel_types = FuelType.query.order_by(FuelType.id).all()
    return render_template('admin/fuel_types.html', fuel_types=fuel_types, error_message=error_message)


@app.route('/admin/delete_fuel_type', methods=['POST'])
def delete_fuel_type():
    from models.fuel_type import FuelType

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    type_id = request.form.get('fuel_type_id')
    fuel_type = FuelType.query.get(type_id)

    if fuel_type:
        db.session.delete(fuel_type)
        db.session.commit()

    return redirect('/admin/fuel_types')


@app.route('/logout')
def logout():
    session.clear()  # This removes all session keys (user_id, role, etc.)
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)
