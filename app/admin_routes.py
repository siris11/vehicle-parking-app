from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from functools import wraps
from .forms import ParkingLotForm
from .models import ParkingLot, ParkingSpot, User, Reservation
from . import db

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
    lots = ParkingLot.query.order_by(ParkingLot.name).all()
    
    total_spots = int(ParkingSpot.query.count() or 0)
    occupied_spots_overall = int(ParkingSpot.query.filter_by(status='O').count() or 0)
    available_spots_overall = total_spots - occupied_spots_overall
    registered_users = int(User.query.filter_by(is_admin=False).count() or 0)

    current_lots = lots if lots else []

    return render_template('admin/dashboard.html', title='Admin Dashboard',
                           lots=current_lots,
                           total_spots=total_spots,
                           occupied_spots=occupied_spots_overall,
                           available_spots=available_spots_overall,
                           registered_users=registered_users)

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
            spot_number = f"S{i:03d}" # Example: S001, S002
            spot = ParkingSpot(spot_number=spot_number, lot_id=new_lot.id, status='A')
            db.session.add(spot)
        
        db.session.commit()
        flash(f'Parking lot \'{new_lot.name}\' created successfully with {new_lot.maximum_capacity} spots!', 'success')
        return redirect(url_for('admin_routes.list_parking_lots'))
    return render_template('admin/create_edit_parking_lot.html', form=form, title='Create Parking Lot', legend='New Parking Lot', ParkingSpot=ParkingSpot)

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

        lot.name = form.name.data
        lot.address = form.address.data
        lot.pin_code = form.pin_code.data
        lot.price_per_hour = form.price_per_hour.data
        # Update capacity last, after spot adjustments if necessary

        if new_capacity > original_capacity:
            spots_to_add = new_capacity - original_capacity
            existing_spot_numbers = {spot.spot_number for spot in lot.spots.all()}
            
            candidate_suffix = 1
            spots_added_count = 0
            
            while spots_added_count < spots_to_add:
                prospective_spot_number = f"S{candidate_suffix:03d}"
                if prospective_spot_number not in existing_spot_numbers:
                    spot = ParkingSpot(spot_number=prospective_spot_number, parking_lot=lot, status='A')
                    db.session.add(spot)
                    existing_spot_numbers.add(prospective_spot_number) # Add to set to prevent re-adding in same transaction
                    spots_added_count += 1
                candidate_suffix += 1
                if candidate_suffix > 999 and spots_added_count < spots_to_add: # Safety break for S000-S999 format
                    flash('Could not generate enough unique spot numbers. Please check existing spots or capacity.','danger')
                    db.session.rollback() # Rollback spots added in this attempt
                    return render_template('admin/create_edit_parking_lot.html', form=form, title='Edit Parking Lot', legend=f'Edit {lot.name}', lot=lot, ParkingSpot=ParkingSpot)

        elif new_capacity < original_capacity:
            spots_to_remove_count = original_capacity - new_capacity
            # Prioritize removing spots that are available and have no reservations
            # For simplicity, we are removing available spots from highest number downwards as before.
            # A more complex version might allow choosing which spots to remove.
            available_spots_to_remove = lot.spots.filter_by(status='A').order_by(ParkingSpot.spot_number.desc()).limit(spots_to_remove_count).all()
            
            if len(available_spots_to_remove) < spots_to_remove_count:
                flash(f'Cannot reduce capacity by {spots_to_remove_count}. Only {len(available_spots_to_remove)} available spots can be removed. Please ensure spots are free or release them manually.', 'danger')
                # No rollback needed here as we haven't made changes yet for this path
                return redirect(url_for('admin_routes.edit_parking_lot', lot_id=lot.id))
            else:
                for spot_to_remove in available_spots_to_remove:
                    # Double check no active reservations, though status 'A' should mean none.
                    # This is more critical if allowing deletion of specific spots by admin in future.
                    if spot_to_remove.get_active_reservation():
                        flash(f'Cannot remove spot {spot_to_remove.spot_number} as it has an active reservation, despite being marked Available. Please resolve.', 'danger')
                        return redirect(url_for('admin_routes.edit_parking_lot', lot_id=lot.id))
                    db.session.delete(spot_to_remove)
                flash(f'Reduced capacity. {spots_to_remove_count} spots removed.', 'info')
        
        lot.maximum_capacity = new_capacity # Set the new capacity on the lot model
        db.session.commit()
        flash(f'Parking lot \'{lot.name}\' updated successfully!', 'success')
        return redirect(url_for('admin_routes.list_parking_lots'))
    
    return render_template('admin/create_edit_parking_lot.html', form=form, title='Edit Parking Lot', legend=f'Edit {lot.name}', lot=lot, ParkingSpot=ParkingSpot)

@bp.route('/parking_lot/delete/<int:lot_id>', methods=['POST'])
@login_required
@admin_required
def delete_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    # Check if all spots in the parking lot are empty (no active reservations)
    occupied_spots = lot.spots.filter_by(status='O').count()
    if occupied_spots > 0:
        flash(f'Cannot delete parking lot \'{lot.name}\'. It has occupied spots.', 'danger')
        return redirect(url_for('admin_routes.list_parking_lots'))
    
    # Cascading delete should handle spots due to relationship setting
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
    return render_template('admin/view_lot_spots.html', lot=lot, spots=spots, title=f'Spots in {lot.name}')


@bp.route('/view_spot_details/<int:spot_id>')
@login_required
@admin_required
def view_spot_details(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    reservation = None
    if spot.status == 'O':
        # Find the current reservation for this spot
        reservation = Reservation.query.filter_by(spot_id=spot.id, leaving_timestamp=None).first()
    return render_template('admin/view_spot_details.html', spot=spot, reservation=reservation, title=f'Details for Spot {spot.spot_number}', Reservation=Reservation)


@bp.route('/spot/delete/<int:spot_id>', methods=['POST'])
@login_required
@admin_required
def delete_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    lot = spot.parking_lot # Get the parent lot

    if spot.status == 'O':
        flash(f'Spot {spot.spot_number} in lot {lot.name} is occupied and cannot be deleted.', 'danger')
        return redirect(url_for('admin_routes.view_lot_spots', lot_id=lot.id))

    # Check for active reservations just in case, though status 'A' should mean none
    active_reservation = Reservation.query.filter_by(spot_id=spot.id, leaving_timestamp=None).first()
    if active_reservation:
        flash(f'Spot {spot.spot_number} in lot {lot.name} has an active reservation and cannot be deleted.', 'danger')
        return redirect(url_for('admin_routes.view_lot_spots', lot_id=lot.id))

    spot_number_deleted = spot.spot_number
    db.session.delete(spot)
    
    # Decrement capacity of the parent lot
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

# Add routes for summary charts later 