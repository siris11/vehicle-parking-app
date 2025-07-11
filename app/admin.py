from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from functools import wraps
from .forms import ParkingLotForm, EditProfileForm, ChangePasswordForm
from .models import ParkingLot, ParkingSpot, User, Reservation 
from . import db
import datetime 
from sqlalchemy import func 

bp = Blueprint('admin', __name__)

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
            maximum_capacity=form.maximum_capacity.data,
            is_active = True
        )
        db.session.add(new_lot)
        db.session.flush() # ID 
        for i in range(1, form.maximum_capacity.data + 1):
            spot_number = f"A{i:03d}" 
            spot = ParkingSpot(spot_number=spot_number, lot_id=new_lot.id, status='Available')
            db.session.add(spot)
        
        db.session.commit()
        flash(f'Parking lot \'{new_lot.name}\' created successfully with {new_lot.maximum_capacity} spots!', 'success')
        return redirect(url_for('admin.list_parking_lots'))
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
        
        #Add spots
        if new_capacity > original_capacity:
            add_spots = new_capacity - original_capacity
            last_present_spot = db.session.query(func.max(ParkingSpot.spot_number)).filter_by(lot_id=lot.id).scalar()
            
            start_from_number = 1
            if last_present_spot:
                try:
                    numeric_part = int(last_present_spot.lstrip('A'))
                    start_from_number = numeric_part + 1
                except (ValueError, TypeError):
                    print(f"Warning: Could not parse spot number '{last_present_spot}'. Starts from 1.")

            for i in range(start_from_number, start_from_number + add_spots):
                spot_number = f"A{i:03d}"
                spot = ParkingSpot(spot_number=spot_number, lot_id=lot.id, status='Available')
                db.session.add(spot)
            flash(f'Capacity increased. {add_spots} new spots added.', 'success')

        #Decrease
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
        flash(f'Cannot delete parking lot \'{lot.name}\'. It has active or pending reservations.', 'danger')
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

    return render_template('admin/view_spot_details.html', spot=spot, reservation=reservation, title=f'Details for Spot {spot.spot_number}', Reservation=Reservation) 

@bp.route('/spot/delete/<int:spot_id>', methods=['POST'])
@login_required
@admin_required
def delete_spot(spot_id):
    flash('Direct deletion of individual parking spots is not allowed', 'danger')
    
    spot = ParkingSpot.query.get(spot_id)
    if spot:
        return redirect(url_for('admin.view_lot_spots', lot_id=spot.lot_id))
    else:
        return redirect(url_for('admin.list_parking_lots'))
# def delete_spot(spot_id):
#     spot = ParkingSpot.query.get_or_404(spot_id)
#     lot = spot.parking_lot 

#     if spot.status in ['Occupied', 'Reserved']:
#         flash(f'Spot {spot.spot_number} in lot {lot.name} is {spot.status.lower()} and cannot be deleted.', 'danger')
#         return redirect(url_for('admin.view_lot_spots', lot_id=lot.id))

#     active_or_pending_reservation = Reservation.query.filter(
#         Reservation.spot_id == spot.id,
#         Reservation.status.in_(['active', 'pending'])
#     ).first()
#     if active_or_pending_reservation:
#         flash(f'Spot {spot.spot_number} in lot {lot.name} has an active or pending reservation and cannot be deleted.', 'danger')
#         return redirect(url_for('admin.view_lot_spots', lot_id=lot.id))

#     spot_number_deleted = spot.spot_number
#     db.session.delete(spot)
    
#     if lot.maximum_capacity > 0:
#         lot.maximum_capacity -= 1
    
#     db.session.commit()
#     flash(f'Parking spot {spot_number_deleted} in lot {lot.name} has been deleted. Lot capacity adjusted.', 'success')
#     return redirect(url_for('admin.view_lot_spots', lot_id=lot.id))


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

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
@admin_required 
def edit_profile():
    form = EditProfileForm(original_username=current_user.username, original_email=current_user.email)

    if request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.full_name.data = current_user.full_name

    if form.validate_on_submit():
        try:
            current_user.username = form.username.data
            current_user.email = form.email.data
            current_user.full_name = form.full_name.data
            db.session.commit()
            flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating your profile: {e}', 'danger')

    return render_template('user/edit_profile.html', title='Edit Admin Profile', form=form) # Re-use user template

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
@admin_required 
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        try:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been changed successfully!', 'success')
            return redirect(url_for('admin.dashboard')) # Redirect back to admin dashboard
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while changing your password: {e}', 'danger')
    return render_template('user/change_password.html', title='Change Admin Password', form=form) # Re-use user template