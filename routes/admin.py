from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from functools import wraps
from forms import ParkingLotForm
from models import db, ParkingLot, ParkingSpot, User, Reservation 
from datetime import datetime, timedelta
from sqlalchemy import func, or_
import pytz 

bp = Blueprint('admin', __name__)
IST = pytz.timezone('Asia/Kolkata')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Spot Status
    lots = ParkingLot.query.order_by(ParkingLot.name).all()
    
    total_spots = int(ParkingSpot.query.count() or 0)
    occupied_spots_overall = int(ParkingSpot.query.filter_by(status='Occupied').count() or 0)
    reserved_spots_overall = int(ParkingSpot.query.filter_by(status='Reserved').count() or 0)
    available_spots_overall = total_spots - occupied_spots_overall - reserved_spots_overall
    
    registered_users = int(User.query.filter_by(is_admin=False).count() or 0)

    current_lots = lots if lots else []

    # Reservation Status Breakdown
    pending_reservations = Reservation.query.filter_by(status='pending').count()
    active_reservations = Reservation.query.filter_by(status='active').count()
    completed_reservations = Reservation.query.filter_by(status='completed').count()
    cancelled_reservations = Reservation.query.filter_by(status='cancelled').count()

    # Daily Bookings 7 days
    daily_reservation_labels = []
    daily_reservation_counts = []
    
    # UTC to IST
    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    now_ist = now_utc.astimezone(IST)
    today_ist = now_ist.date() 

    for i in range(6, -1, -1): 
        date_ist = today_ist - timedelta(days=i)
        daily_reservation_labels.append(date_ist.strftime('%b %d'))
        
        start_of_ist_day_utc = IST.localize(datetime(date_ist.year, date_ist.month, date_ist.day, 0, 0, 0)).astimezone(pytz.utc)
        end_of_ist_day_utc = IST.localize(datetime(date_ist.year, date_ist.month, date_ist.day, 23, 59, 59)).astimezone(pytz.utc)

        count = db.session.query(Reservation).filter(
            Reservation.booking_timestamp >= start_of_ist_day_utc,
            Reservation.booking_timestamp <= end_of_ist_day_utc
        ).count()
        daily_reservation_counts.append(count)

    # Revenue chart
    daily_revenue_labels = []
    daily_revenue_amounts = []
    
    daily_revenue_map = {}
    for i in range(6, -1, -1):
        date_ist = today_ist - timedelta(days=i)
        display_label = date_ist.strftime('%b %d')
        daily_revenue_labels.append(display_label)
        daily_revenue_map[date_ist.strftime('%Y-%m-%d')] = 0.0

    seven_days_ago_ist = today_ist - timedelta(days=7)
    start_of_period_utc = IST.localize(datetime(seven_days_ago_ist.year, seven_days_ago_ist.month, seven_days_ago_ist.day, 0, 0, 0)).astimezone(pytz.utc)

    recent_completed_reservations = Reservation.query.filter(
        Reservation.status == 'completed',
        Reservation.check_out_timestamp >= start_of_period_utc
    ).all()

    for res in recent_completed_reservations:
        if res.total_cost is not None and res.check_out_timestamp:
            checkout_timestamp_ist = res.check_out_timestamp.replace(tzinfo=pytz.utc).astimezone(IST)
            checkout_date_ist_str = checkout_timestamp_ist.strftime('%Y-%m-%d')
            
            if checkout_date_ist_str in daily_revenue_map:
                daily_revenue_map[checkout_date_ist_str] += res.total_cost

    for date_str in sorted(daily_revenue_map.keys()):
        daily_revenue_amounts.append(round(daily_revenue_map[date_str], 2))


    return render_template('admin/dashboard.html', 
                           title='Admin Dashboard',
                           lots=current_lots,
                           total_spots=total_spots,
                           occupied_spots=occupied_spots_overall,
                           reserved_spots=reserved_spots_overall, 
                           available_spots=available_spots_overall,
                           registered_users=registered_users,
                           pending_reservations=pending_reservations,
                           active_reservations=active_reservations,
                           completed_reservations=completed_reservations,
                           cancelled_reservations=cancelled_reservations,
                           daily_reservation_labels=daily_reservation_labels,
                           daily_reservation_counts=daily_reservation_counts,
                           daily_revenue_labels=daily_revenue_labels,
                           daily_revenue_amounts=daily_revenue_amounts)

@bp.route('/parking_lots')
@login_required
@admin_required
def list_parking_lots():
    lots = ParkingLot.query.order_by(ParkingLot.name).all()
    return render_template('admin/list_parking_lots.html', lots=lots, title='Manage Parking Lots')

@bp.route('/search', methods=['GET'])
@login_required
@admin_required
def search_all():
    search_term = request.args.get('search_term', '').strip()
    search_category = request.args.get('search_category')

    users_found = []
    lots_found = []
    
    if not search_term:
        if search_category == "users":
            users_found = User.query.order_by(User.username).all()
        elif (search_category == "lots" or search_category == "pincode"):
            lots_found = ParkingLot.query.order_by(ParkingLot.name).all()

    elif search_term and search_category:
        search_pattern = f"%{search_term}%"

        if search_category == 'users':
            users_found = User.query.filter(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern)
                )
            ).order_by(User.username).all()

        elif search_category == 'lots':
            lots_found = ParkingLot.query.filter(
                or_(
                    ParkingLot.name.ilike(search_pattern),
                    ParkingLot.address.ilike(search_pattern)
                )
            ).order_by(ParkingLot.name).all()

        elif search_category == 'pincode':
            lots_found = ParkingLot.query.filter(ParkingLot.pin_code.ilike(search_pattern)).order_by(ParkingLot.name).all()

    return render_template('admin/search_results.html',
                           title=f"Search Results for '{search_term}'",
                           search_term=search_term,
                           search_category=search_category,
                           users_found=users_found,
                           lots_found=lots_found)

@bp.route('/parking_lot/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_parking_lot():
    form = ParkingLotForm()
    if form.validate_on_submit():
        new_lot = ParkingLot(
            name=form.name.data,
            address=form.address.data,
            pin_code=form.pin_code.data,
            price_per_hour=form.price_per_hour.data,
            maximum_capacity=form.maximum_capacity.data,
            is_active=True
        )
        db.session.add(new_lot)
        db.session.flush()

        for i in range(1, form.maximum_capacity.data + 1):
            spot_number = f"S{i:03d}" 
            spot = ParkingSpot(spot_number=spot_number, lot_id=new_lot.id, status='Available')
            db.session.add(spot)
        
        db.session.commit()
        flash(f'Parking lot \'{new_lot.name}\' created successfully with {new_lot.maximum_capacity} spots!', 'success')
        return redirect(url_for('admin.list_parking_lots')) # Corrected blueprint
    return render_template('admin/create_edit_parking_lot.html', form=form, title='Create Parking Lot', legend='New Parking Lot') 

@bp.route('/parking_lot/edit/<int:lot_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    form = ParkingLotForm(obj=lot)
    form._original_name = lot.name 

    if form.validate_on_submit():
        original_capacity = lot.maximum_capacity
        new_capacity = form.maximum_capacity.data
        
        lot.name = form.name.data
        lot.address = form.address.data
        lot.pin_code = form.pin_code.data
        lot.price_per_hour = form.price_per_hour.data
        
        if new_capacity > original_capacity:
            add_spots = new_capacity - original_capacity
            last_present_spot = db.session.query(func.max(ParkingSpot.spot_number)).filter_by(lot_id=lot.id).scalar()
            
            start_from_number = 1
            if last_present_spot:
                try:
                    numeric_part = int(last_present_spot.lstrip('AS')) 
                    start_from_number = numeric_part + 1
                except (ValueError, TypeError):
                    print(f"Warning: Could not parse spot number '{last_present_spot}'. Starting new spots from S001.")

            for i in range(start_from_number, start_from_number + add_spots):
                spot_number = f"S{i:03d}" 
                spot = ParkingSpot(spot_number=spot_number, lot_id=lot.id, status='Available')
                db.session.add(spot)
            flash(f'Capacity increased. {add_spots} new spots added.', 'success')

        elif new_capacity < original_capacity:
            delete_spots = original_capacity - new_capacity

            spots_to_delete = ParkingSpot.query.filter(
                ParkingSpot.lot_id == lot.id,
                ParkingSpot.status == 'Available',
                ~ParkingSpot.spot_reservations.any(Reservation.status.in_(['pending', 'active']))
            ).order_by(ParkingSpot.spot_number.desc()).limit(delete_spots).all()

            if len(spots_to_delete) < delete_spots:
                flash(f'Cannot reduce capacity by {delete_spots} spots. Only {len(spots_to_delete)} truly available spots can be removed. Please ensure spots are free and have no active or pending reservations.', 'danger')
                db.session.rollback()
                return redirect(url_for('admin.edit_parking_lot', lot_id=lot.id)) 
            else:
                for spot_to_delete in spots_to_delete:
                    db.session.delete(spot_to_delete)
                flash(f'Reduced capacity. {delete_spots} spots removed.', 'info')

        lot.maximum_capacity = new_capacity
        db.session.commit()
        flash(f'Parking lot \'{lot.name}\' updated successfully!', 'success')
        return redirect(url_for('admin.list_parking_lots'))

    return render_template('admin/create_edit_parking_lot.html', form=form, title='Edit Parking Lot', legend=f'Edit {lot.name}', lot=lot, ParkingSpot=ParkingSpot)

@bp.route('/parking_lot/delete/<int:lot_id>', methods=['POST'])
@login_required
@admin_required
def delete_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    
    occupied_or_reserved_spots = ParkingSpot.query.filter(
        ParkingSpot.lot_id == lot.id,
        ParkingSpot.status.in_(['Occupied', 'Reserved'])
    ).count()

    if occupied_or_reserved_spots > 0:
        flash(f'Cannot delete parking lot \'{lot.name}\'. It has occupied or reserved spots.', 'danger')
        return redirect(url_for('admin.list_parking_lots')) 
    active_or_pending_reservations_in_lot = Reservation.query.join(ParkingSpot).filter(
        ParkingSpot.lot_id == lot.id,
        Reservation.status.in_(['pending', 'active'])
    ).count()

    if active_or_pending_reservations_in_lot > 0:
        flash(f'NOt possible to delete this lot \'{lot.name}\'. It has active or pending reservations.', 'danger')
        return redirect(url_for('admin.list_parking_lots')) 

    lot_name = lot.name
    db.session.delete(lot)
    db.session.commit()
    flash(f'Parking lot \'{lot_name}\' and its spots have been deleted.', 'success')
    return redirect(url_for('admin.list_parking_lots')) 

@bp.route('/view_spots/<int:lot_id>')
@login_required
@admin_required
def view_lot_spots(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = lot.spots.order_by(ParkingSpot.spot_number).all()
    
    return render_template('admin/view_lot_spots.html', 
                           lot=lot, 
                           spots=spots, 
                           title=f'Spots in {lot.name}', 
                           Reservation=Reservation)


@bp.route('/view_spot_details/<int:spot_id>')
@login_required
@admin_required
def view_spot_details(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    
    reservation = Reservation.query.filter_by(
        spot_id=spot.id,
        status='active' 
    ).first()

    parked_at_ist_str = None
    if reservation and reservation.booking_timestamp:
        parked_at_ist_str = reservation.booking_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M:%S (IST)')
    
    current_time_ist_str = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M:%S (IST)')

    # Reservation history for spot
    all_spot_reservations = spot.spot_reservations.order_by(Reservation.booking_timestamp.desc()).all()
    reservations_history_for_template = []
    for res in all_spot_reservations:
        booking_ist_str = res.booking_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
        check_in_ist_str = None
        if res.check_in_timestamp:
            check_in_ist_str = res.check_in_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
        check_out_ist_str = None
        if res.check_out_timestamp:
            check_out_ist_str = res.check_out_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
        
        reservations_history_for_template.append({
            'id': res.id,
            'tenant': res.tenant, 
            'vehicle_number': res.vehicle_number,
            'booking_timestamp_ist_str': booking_ist_str,
            'check_in_timestamp_ist_str': check_in_ist_str,
            'check_out_timestamp_ist_str': check_out_ist_str,
            'status': res.status,
            'total_cost': res.total_cost
        })

    return render_template('admin/view_spot_details.html', 
                             spot=spot, 
                             reservation=reservation, 
                             title=f'Details for Spot {spot.spot_number}', 
                             parked_at_ist_str=parked_at_ist_str, # IST string for active reservation
                             current_time_ist_str=current_time_ist_str, # IST string for current time
                             reservations_history=reservations_history_for_template) 


@bp.route('/spot/delete/<int:spot_id>', methods=['POST'])
@login_required
@admin_required
def delete_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    lot = spot.parking_lot 

    if spot.status in ['Occupied', 'Reserved']:
        flash(f'Spot {spot.spot_number} in lot {lot.name} is {spot.status.lower()} and cannot be deleted.', 'danger')
        return redirect(url_for('admin.view_lot_spots', lot_id=lot.id)) 

    active_or_pending_reservation = Reservation.query.filter(
        Reservation.spot_id == spot.id,
        Reservation.status.in_(['active', 'pending'])
    ).first()
    if active_or_pending_reservation:
        flash(f'Spot {spot.spot_number} in lot {lot.name} has an active or pending reservation and cannot be deleted.', 'danger')
        return redirect(url_for('admin.view_lot_spots', lot_id=lot.id)) 
    spot_number_deleted = spot.spot_number
    db.session.delete(spot)
    
    if lot.maximum_capacity > 0:
        lot.maximum_capacity -= 1
    
    db.session.commit()
    flash(f'Parking spot {spot_number_deleted} in lot {lot.name} has been deleted. Lot capacity decreased!!', 'success')
    return redirect(url_for('admin.view_lot_spots', lot_id=lot.id))


@bp.route('/users')
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.username).all()
    return render_template('admin/list_users.html', users=users, title='Registered Users')


@bp.route('/user_details/<int:user_id>')
@login_required
@admin_required
def user_details(user_id):
    user = User.query.get_or_404(user_id)
    reservations = user.reservations.order_by(Reservation.booking_timestamp.desc()).all()
    
    reservations_for_template = []
    for res in reservations:
        booking_ist_str = res.booking_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
        check_in_ist_str = None
        if res.check_in_timestamp:
            check_in_ist_str = res.check_in_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
        check_out_ist_str = None
        if res.check_out_timestamp:
            check_out_ist_str = res.check_out_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
        
        reservations_for_template.append({
            'id': res.id,
            'parking_spot': res.parking_spot, 
            'vehicle_number': res.vehicle_number,
            'booking_timestamp_ist_str': booking_ist_str, 
            'check_in_timestamp_ist_str': check_in_ist_str, 
            'check_out_timestamp_ist_str': check_out_ist_str,
            'total_cost': res.total_cost,
            'status': res.status,
            'user_id': res.user_id,
            'tenant': res.tenant 
        })

    return render_template('admin/user_details.html', 
                             user=user, 
                             reservations=reservations_for_template,
                             title=f'Details for {user.full_name}')
