from flask import Blueprint, render_template, request, jsonify, redirect, session, url_for, flash
from flask_login import login_required, logout_user, login_user
from werkzeug.security import check_password_hash
from .models import User,Customer, SalmonOrder, SalmonOrderWeight
from . import db, login_manager, socketio
import os
from datetime import date, datetime, timedelta
from collections import defaultdict
from sqlalchemy import func
import pytz

bp = Blueprint('main', __name__)




# Routes
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        try:
            # Check if user exists and password is correct
            if user and check_password_hash(user.password, password):
                remember_me = False
                print(request.form.get('remember'))
                if 'remember' in request.form and request.form.get('remember') =="on":
                    remember_me = True
                    login_user(user, remember=remember_me)
                else:
                    login_user(user)
                return redirect(url_for('main.index'))

            else:
                flash("Invalid email or password.", 'danger')
                return redirect(url_for('main.login'))
        except ValueError:
            flash("Invalid email or password.", 'danger')
            return redirect(url_for('main.login'))

    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))


@bp.route('/emit_print_zebra', methods=['POST'])
@login_required
def emit_print_zebra():
    data = request.json
    order_id = data.get('order_id')
    socketio.emit('print_zebra', {'order_id': order_id})
    return jsonify({'status': 'Print zebra event emitted'})

# Routes
@bp.route('/emit_print_pdf', methods=['POST'])
@login_required
def emit_print_pdf():
    data = request.json
    order_id = data.get('order_id')
    socketio.emit('print_pdf', {'order_id': order_id})
    return jsonify({'status': 'Print pdf event emitted'})


@login_required
@socketio.on('keepalive')
def emit_keepalive_response(data):
    socketio.emit('keepalive_response', {})
    return jsonify({'status': 'Keepalive response emitted'})



@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    # selected_date = request.form.get('selected_date') or request.args.get('selected_date', (datetime.today() + timedelta(days=1)).date())
    selected_date_str = request.form.get('selected_date') or request.args.get('selected_date')
    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    else:
        # Default to tomorrow's date if none is provided
        selected_date = (datetime.today() + timedelta(days=1)).date()

    # Check if prev_date or next_date buttons were clicked
    if 'prev_date' in request.form:
        selected_date -= timedelta(days=1)
    elif 'next_date' in request.form:
        selected_date += timedelta(days=1)

    order_details = None
    if selected_date:
        order_details = (
            db.session.query(
                SalmonOrder.id, 
                SalmonOrder.customer, 
                SalmonOrder.date, 
                SalmonOrder.product,
                (func.coalesce(SalmonOrder.price * 1.14, 0)).label("price"),
                SalmonOrder.quantity,
                (func.coalesce(func.sum(SalmonOrderWeight.quantity), 0)).label("total_produced"),
                Customer.priority,
                Customer.packing,
            )
            .outerjoin(SalmonOrderWeight, SalmonOrder.id == SalmonOrderWeight.order_id)
            .filter(SalmonOrder.date == selected_date)
            .group_by(SalmonOrder.id)
            .outerjoin(Customer, SalmonOrder.customer == Customer.customer)
            .all()
        )
        grouped_orders = defaultdict(list)
        totals = {}  # Dictionary to store the total for each product group

        for order in order_details:
            grouped_orders[order[3]].append(order)
            if order[3] not in totals:
                totals[order[3]] = 0
            totals[order[3]] += (order[5])



        grouped_orders_sorted = dict(sorted(grouped_orders.items(), key=lambda x: (not x[0].startswith('Lohi'), x[0])))
        print(grouped_orders_sorted)

    return render_template('index.html', grouped_orders=grouped_orders_sorted, selected_date=selected_date, totals=totals, timedelta=timedelta)


@bp.route('/order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def order_detail(order_id):
    if request.method == 'POST':
        scale_reading = float(request.form['scale_reading'])
        weight = SalmonOrderWeight(order_id=order_id, 
                                    quantity=scale_reading, 
                                    production_time=datetime.now(pytz.timezone(os.environ.get('TIMEZONE'))))
        db.session.add(weight)
        db.session.commit()
        session['show_toast'] = True
        return redirect(url_for('main.order_detail', order_id=order_id))

    show_toast = session.pop('show_toast', False)

    # Using SQLAlchemy ORM to retrieve the order with total produced and weight details
    order = (
        db.session.query(
            SalmonOrder.id, 
            SalmonOrder.customer, 
            SalmonOrder.date, 
            SalmonOrder.product,
            (func.coalesce(SalmonOrder.price * 1.14, 0)).label("price"),
            SalmonOrder.quantity,
            (func.coalesce(func.sum(SalmonOrderWeight.quantity), 0)).label("total_produced"),
            Customer.priority,
            Customer.packing,
        )
        .outerjoin(SalmonOrderWeight, SalmonOrder.id == SalmonOrderWeight.order_id)
        .filter(SalmonOrder.id == order_id)
        .group_by(SalmonOrder.id)
        .outerjoin(Customer, SalmonOrder.customer == Customer.customer)
        .first()
    )

    weight_details = (
        db.session.query(SalmonOrderWeight.id, SalmonOrderWeight.quantity, SalmonOrderWeight.production_time)
        .filter(SalmonOrderWeight.order_id == order_id)
        .order_by(SalmonOrderWeight.production_time.asc())
        .all()
    )


    # # First, get the customer and date of the specified order
    # order_customer_date = (
    #     db.session.query(SalmonOrder.customer, SalmonOrder.date)
    #     .filter(SalmonOrder.id == order_id)
    #     .subquery()
    # )
    # # Subquery to get all orders with the same customer and date
    # similar_orders_subquery = (
    #     db.session.query(SalmonOrder.id)
    #     .join(order_customer_date, (SalmonOrder.customer == order_customer_date.c.customer) & (SalmonOrder.date == order_customer_date.c.date))
    #     .subquery()
    # )

    # # Modify your main query to join with the subquery
    # order = (
    #     db.session.query(
    #         SalmonOrder.id, 
    #         SalmonOrder.customer, 
    #         SalmonOrder.date, 
    #         SalmonOrder.product,
    #         (func.coalesce(SalmonOrder.price * 1.14, 0)).label("price"),
    #         SalmonOrder.quantity,
    #         (func.coalesce(func.sum(SalmonOrderWeight.quantity), 0)).label("total_produced"),
    #         Customer.priority,
    #         Customer.packing,
    #     )
    #     .outerjoin(SalmonOrderWeight, SalmonOrder.id == SalmonOrderWeight.order_id)
    #     .join(similar_orders_subquery, SalmonOrder.id == similar_orders_subquery.c.id)
    #     .group_by(SalmonOrder.id)
    #     .outerjoin(Customer, SalmonOrder.customer == Customer.customer)
    #     .all()
    # )

    # # Query for weight details remains the same
    # weight_details = (
    #     db.session.query(SalmonOrderWeight.id, SalmonOrderWeight.quantity, SalmonOrderWeight.production_time)
    #     .filter(SalmonOrderWeight.order_id == order_id)
    #     .order_by(SalmonOrderWeight.production_time.asc())
    #     .all()
    # )
    if not order:
        return "Order not found", 404

    return render_template('order_detail.html', order=order, show_toast=show_toast, weight_details=weight_details)


@bp.route('/weight/<int:weight_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_weight(weight_id):
    weight = SalmonOrderWeight.query.filter_by(id=weight_id).first()
    
    if not weight:
        return jsonify(success=False, error="Weight not found"), 404

    if request.method == 'POST':
        edit_val = request.form.get('edit_weight')
        weight.quantity = edit_val
        db.session.commit()
        return jsonify(success=True)

@bp.route('/weight/<int:weight_id>/delete', methods=['POST'])
@login_required
def delete_weight(weight_id):
    weight = SalmonOrderWeight.query.filter_by(id=weight_id).first()
    
    if not weight:
        return "Weight not found", 404

    db.session.delete(weight)
    db.session.commit()

    return redirect(url_for('main.order_detail', order_id=weight.order_id))


@bp.route('/order_editing', methods=['GET', 'POST'])
@login_required
def order_editing():
    week_str = request.args.get('week', calculate_current_iso_week())

    year, week = map(int, week_str.split('-W'))
    start_date = date.fromisocalendar(year, week, 1)
    end_date = start_date + timedelta(days=6)

    # Check if prev_week or next_week buttons were clicked
    if 'prev_week' in request.args:
        start_date -= timedelta(weeks=1)
    elif 'next_week' in request.args:
        start_date += timedelta(weeks=1)
    end_date = start_date + timedelta(days=6)


    # Update week_str to reflect the new week
    week_str = f"{start_date.year}-W{start_date.isocalendar()[1]:02d}"

    # Query the database for orders within the week
    orders = (
        db.session.query(SalmonOrder)
        .filter(SalmonOrder.date.between(start_date, end_date))
        .order_by(SalmonOrder.customer.asc())
        .all()
    )

    # Organize orders by customer and date
    orders_by_customer = defaultdict(lambda: defaultdict(list))
    for order in orders:
        orders_by_customer[order.customer][order.date].append(order)

    # List of dates in the week for column headers
    week_dates = [start_date + timedelta(days=i) for i in range(6)]
    # Render the order_editing template with necessary data
    return render_template('order_editing.html', week_str=week_str, orders_by_customer=orders_by_customer, week_dates=week_dates)

def calculate_current_iso_week():
    # Get the current date
    current_date = datetime.now()

    # Calculate the start and end of the current ISO week
    # ISO weeks start on Monday and end on Sunday
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Format the dates to match the `input[type=week]` value format (YYYY-W##)
    # Where ## is the ISO week number
    week_number = current_date.isocalendar()[1]
    year = start_of_week.year

    # Pad the week number with leading zero if necessary
    week_number_str = f"{week_number:02d}"

    # Combine into the full string
    week_range_str = f"{year}-W{week_number_str}"

    return week_range_str

