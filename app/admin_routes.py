from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from functools import wraps
from .forms import ParkingLotForm
# Ensure all models are imported
from .models import ParkingLot, ParkingSpot, User, Reservation 
from . import db
import datetime # Import datetime module
from sqlalchemy import func # Import func for database functions like DATE

bp = Blueprint('admin_routes', __name__)

# Decorator to ensure user is admin
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
    # --- Data for Summary Cards & Chart 1 (Spot Status) ---
    lots = ParkingLot.query.order_by(ParkingLot.name).all()
    
    total_spots = int(ParkingSpot.query.count() or 0)
    occupied_spots_overall = int(ParkingSpot.query.filter_by(status='Occupied').count() or 0)
    reserved_spots_overall = int(ParkingSpot.query.filter_by(status='Reserved').count() or 0)
    available_spots_overall = total_spots - occupied_spots_overall - reserved_spots_overall
    
    registered_users = int(User.query.filter_by(is_admin=False).count() or 0)

    current_lots = lots if lots else []

    # --- Data for Chart 2 (Reservation Status Breakdown) ---
    # Count reservations by their status
    pending_reservations = Reservation.query.filter_by(status='pending').count()
    active_reservations = Reservation.query.filter_by(status='active').count()
    completed_reservations = Reservation.query.filter_by(status='completed').count()
    cancelled_reservations = Reservation.query.filter_by(status='cancelled').count()

    # --- Data for Chart 3 (Daily Bookings Trend - Last 7 Days) ---
    daily_reservation_labels = []
    daily_reservation_counts = []
    
    # Get today's date
    today = datetime.date.today()
    
    # Loop for the last 7 days (from 6 days ago up to today)
    for i in range(6, -1, -1): 
        date = today - datetime.timedelta(days=i)
        
        # Format date for chart labels (e.g., 'Jun 01')
        daily_reservation_labels.append(date.strftime('%b %d'))
        
        # Count bookings for this specific date based on booking_timestamp
        # func.date() is used to extract the date part from a datetime column for comparison.
        count = db.session.query(Reservation).filter(
            func.date(Reservation.booking_timestamp) == date.strftime('%Y-%m-%d')
        ).count()
        daily_reservation_counts.append(count)


    return render_template('admin/dashboard.html', 
                           title='Admin Dashboard',
                           lots=current_lots,
                           total_spots=total_spots,
                           occupied_spots=occupied_spots_overall,
                           reserved_spots=reserved_spots_overall, 
                           available_spots=available_spots_overall,
                           registered_users=registered_users,
                           # Data for charts
                           pending_reservations=pending_reservations,
                           active_reservations=active_reservations,
                           completed_reservations=completed_reservations,
                           cancelled_reservations=cancelled_reservations,
                           daily_reservation_labels=daily_reservation_labels,
                           daily_reservation_counts=daily_reservation_counts)

@bp.route('/parking_lots')
@login_required
@admin_required
def list_parking_lots():
    lots = ParkingLot.query.order_by(ParkingLot.name).all()
    return render_template('admin/list_parking_lots.html', lots=lots, title='Manage Parking Lots')

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
            maximum_capacity=form.maximum_capacity.data
        )
        db.session.add(new_lot)
        db.session.flush() # Get the ID for the new_lot

        # Create parking spots for the lot
        for i in range(1, form.maximum_capacity.data + 1):
            spot_number = f"S{i:03d}" 
            spot = ParkingSpot(spot_number=spot_number, lot_id=new_lot.id, status='Available')
            db.session.add(spot)
        
        db.session.commit()
        flash(f'Parking lot \'{new_lot.name}\' created successfully with {new_lot.maximum_capacity} spots!', 'success')
        return redirect(url_for('admin_routes.list_parking_lots'))
    return render_template('admin/create_edit_parking_lot.html', form=form, title='Create Parking Lot', legend='New Parking Lot') 

@bp.route('/parking_lot/edit/<int:lot_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    form = ParkingLotForm(obj=lot)
    form._original_name = lot.name # Store original name for validation

    if form.validate_on_submit():
        original_capacity = lot.maximum_capacity
        new_capacity = form.maximum_capacity.data

        # Prevent increasing maximum_capacity
        if new_capacity > original_capacity:
            flash(f'Cannot increase the maximum capacity of parking lot \'{lot.name}\'. Physical expansion is not supported via this interface.', 'danger')
            return redirect(url_for('admin_routes.edit_parking_lot', lot_id=lot.id))

        # Update other fields first
        lot.name = form.name.data
        lot.address = form.address.data
        lot.pin_code = form.pin_code.data
        lot.price_per_hour = form.price_per_hour.data

        # Logic for decreasing capacity
        if new_capacity < original_capacity:
            spots_to_remove_count = original_capacity - new_capacity
            
            truly_available_spots_query = ParkingSpot.query.filter(
                ParkingSpot.lot_id == lot.id,
                ParkingSpot.status == 'Available'
            ).order_by(ParkingSpot.spot_number.desc())

            truly_available_spots = []
            for spot_candidate in truly_available_spots_query:
                active_or_pending_reservation = Reservation.query.filter(
                    Reservation.spot_id == spot_candidate.id,
                    Reservation.status.in_(['pending', 'active'])
                ).first()
                if not active_or_pending_reservation:
                    truly_available_spots.append(spot_candidate)
                
                if len(truly_available_spots) >= spots_to_remove_count:
                    break

            if len(truly_available_spots) < spots_to_remove_count:
                flash(f'Cannot reduce capacity by {spots_to_remove_count} spots. Only {len(truly_available_spots)} truly available spots can be removed. Please ensure spots are free and have no active or pending reservations.', 'danger')
                db.session.rollback()
                return redirect(url_for('admin_routes.edit_parking_lot', lot_id=lot.id))
            else:
                for i in range(spots_to_remove_count):
                    spot_to_remove = truly_available_spots[i]
                    db.session.delete(spot_to_remove)
                flash(f'Reduced capacity. {spots_to_remove_count} spots removed.', 'info')
        
        lot.maximum_capacity = new_capacity 
        db.session.commit()
        flash(f'Parking lot \'{lot.name}\' updated successfully!', 'success')
        return redirect(url_for('admin_routes.list_parking_lots'))
    
    return render_template('admin/create_edit_parking_lot.html', form=form, title='Edit Parking Lot', legend=f'Edit {lot.name}', lot=lot, ParkingSpot=ParkingSpot) 

@bp.route('/parking_lot/delete/<int:lot_id>', methods=['POST'])
@login_required
@admin_required
def delete_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    
    # Check for 'Occupied' or 'Reserved' spots
    occupied_or_reserved_spots = ParkingSpot.query.filter(
        ParkingSpot.lot_id == lot.id,
        ParkingSpot.status.in_(['Occupied', 'Reserved'])
    ).count()

    if occupied_or_reserved_spots > 0:
        flash(f'Cannot delete parking lot \'{lot.name}\'. It has occupied or reserved spots.', 'danger')
        return redirect(url_for('admin_routes.list_parking_lots'))
    
    # Also double-check for any active/pending reservations, even if spot status is 'Available'
    # This is a more robust check directly on the Reservation model
    active_or_pending_reservations_in_lot = Reservation.query.join(ParkingSpot).filter(
        ParkingSpot.lot_id == lot.id,
        Reservation.status.in_(['pending', 'active'])
    ).count()

    if active_or_pending_reservations_in_lot > 0:
        flash(f'Cannot delete parking lot \'{lot.name}\'. It has active or pending reservations.', 'danger')
        return redirect(url_for('admin_routes.list_parking_lots'))

    lot_name = lot.name
    db.session.delete(lot)
    db.session.commit()
    flash(f'Parking lot \'{lot_name}\' and its spots have been deleted.', 'success')
    return redirect(url_for('admin_routes.list_parking_lots'))

@bp.route('/view_spots/<int:lot_id>')
@login_required
@admin_required
def view_lot_spots(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = lot.spots.order_by(ParkingSpot.spot_number).all()
    # Pass the Reservation model to the template
    return render_template('admin/view_lot_spots.html', lot=lot, spots=spots, title=f'Spots in {lot.name}', Reservation=Reservation)


@bp.route('/view_spot_details/<int:spot_id>')
@login_required
@admin_required
def view_spot_details(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    reservation = Reservation.query.filter_by(
        spot_id=spot.id,
        status='active' 
    ).first()

    # Pass the Reservation model class to the template
    return render_template('admin/view_spot_details.html', spot=spot, reservation=reservation, title=f'Details for Spot {spot.spot_number}', Reservation=Reservation) 

@bp.route('/spot/delete/<int:spot_id>', methods=['POST'])
@login_required
@admin_required
def delete_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    lot = spot.parking_lot 

    if spot.status in ['Occupied', 'Reserved']:
        flash(f'Spot {spot.spot_number} in lot {lot.name} is {spot.status.lower()} and cannot be deleted.', 'danger')
        return redirect(url_for('admin_routes.view_lot_spots', lot_id=lot.id))

    active_or_pending_reservation = Reservation.query.filter(
        Reservation.spot_id == spot.id,
        Reservation.status.in_(['active', 'pending'])
    ).first()
    if active_or_pending_reservation:
        flash(f'Spot {spot.spot_number} in lot {lot.name} has an active or pending reservation and cannot be deleted.', 'danger')
        return redirect(url_for('admin_routes.view_lot_spots', lot_id=lot.id))

    spot_number_deleted = spot.spot_number
    db.session.delete(spot)
    
    if lot.maximum_capacity > 0:
        lot.maximum_capacity -= 1
    
    db.session.commit()
    flash(f'Parking spot {spot_number_deleted} in lot {lot.name} has been deleted. Lot capacity adjusted.', 'success')
    return redirect(url_for('admin_routes.view_lot_spots', lot_id=lot.id))


@bp.route('/users')
@login_required
@admin_required
def list_users():
    users = User.query.filter_by(is_admin=False).order_by(User.username).all()
    return render_template('admin/list_users.html', users=users, title='Registered Users')


@bp.route('/user_details/<int:user_id>')
@login_required
@admin_required
def user_details(user_id):
    user = User.query.get_or_404(user_id)
    reservations = user.reservations.order_by(Reservation.booking_timestamp.desc()).all()
    
    return render_template('admin/user_details.html', 
                            user=user, 
                            reservations=reservations,
                            title=f'Details for {user.full_name}')