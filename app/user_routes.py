from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from datetime import datetime, timedelta
from .forms import BookSpotForm, CheckInForm, ParkOutForm, EditProfileForm, ChangePasswordForm 
from .models import ParkingLot, ParkingSpot, User, Reservation 
from . import db
from sqlalchemy import or_ 
from werkzeug.security import generate_password_hash, check_password_hash 

bp = Blueprint('user_routes', __name__)

@bp.route('/dashboard', methods=['GET', 'POST']) # Allow POST for search form
@login_required
def dashboard():
    # Initialize search variables
    search_term = request.form.get('search_term') if request.method == 'POST' else request.args.get('search_term')
    
    # Fetch parking lots - apply search filter if term exists
    if search_term:
        search_pattern = f"%{search_term}%"
        parking_lots = ParkingLot.query.filter(
            or_(
                ParkingLot.name.ilike(search_pattern),
                ParkingLot.address.ilike(search_pattern),
                ParkingLot.pin_code.ilike(search_pattern)
            )
        ).order_by(ParkingLot.name).all()
        if not parking_lots:
            flash(f"No parking lots found matching '{search_term}'.", 'info')
    else:
        parking_lots = ParkingLot.query.order_by(ParkingLot.name).all()
    
    # Fetch current user's active AND pending reservations
    user_current_reservations = Reservation.query.filter(
        Reservation.user_id == current_user.id,
        Reservation.status.in_(['pending', 'active', 'completed', 'cancelled']) # Include all for history table
    ).order_by(Reservation.booking_timestamp.desc()).all() # Order by booking time

    # This flag is still useful for displaying user-specific messages/buttons
    has_active_or_pending_reservation = any(res.status in ['pending', 'active'] for res in user_current_reservations)

    # Forms (passed to template if needed for rendering within dashboard)
    book_form = BookSpotForm()
    check_in_form = CheckInForm() 
    park_out_form = ParkOutForm()

    # --- Data for Charts (User Dashboard) ---
    # Fetch completed reservations for chart data
    completed_reservations = Reservation.query.filter_by(
        user_id=current_user.id,
        status='completed'
    ).order_by(Reservation.check_out_timestamp.desc()).all()

    # 1. Parking Cost Chart Data (last 10 completed parkings)
    parking_cost_chart_data = []
    for res in completed_reservations[:10]: # Take last 10
        if res.total_cost is not None and res.check_out_timestamp:
            parking_cost_chart_data.append([res.check_out_timestamp.strftime('%Y-%m-%d'), res.total_cost])
    parking_cost_chart_data.reverse() # Show oldest first on chart

    # 2. Parking Frequency Chart Data (last 7 days)
    parking_frequency_data = {}
    today = datetime.utcnow().date()
    for i in range(7):
        date = today - timedelta(days=i)
        parking_frequency_data[date.strftime('%Y-%m-%d')] = 0
    
    for res in completed_reservations:
        if res.check_out_timestamp and (today - res.check_out_timestamp.date()).days < 7:
            date_str = res.check_out_timestamp.strftime('%Y-%m-%d')
            parking_frequency_data[date_str] = parking_frequency_data.get(date_str, 0) + 1
    
    parking_frequency_chart_data = sorted(parking_frequency_data.items()) # Sort by date

    # 3. Most Visited Lots Chart Data (last 10 completed parkings)
    most_visited_lots_raw = {}
    for res in completed_reservations[:10]: # Take last 10
        if res.parking_spot and res.parking_spot.parking_lot:
            lot_name = res.parking_spot.parking_lot.name
            most_visited_lots_raw[lot_name] = most_visited_lots_raw.get(lot_name, 0) + 1
    
    most_visited_lots_data = list(most_visited_lots_raw.items())


    return render_template('user/dashboard.html', 
                           title='User Dashboard',
                           parking_lots=parking_lots,
                           user_reservations_table=user_current_reservations, # Pass all reservations for the table
                           has_active_or_pending_reservation=has_active_or_pending_reservation,
                           book_form=book_form,
                           check_in_form=check_in_form,
                           park_out_form=park_out_form,
                           search_term=search_term, # Pass search term back to template
                           # Chart data
                           parking_cost_chart_data=parking_cost_chart_data,
                           parking_frequency_data=parking_frequency_chart_data,
                           most_visited_lots_data=most_visited_lots_data)

@bp.route('/book_spot/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def book_spot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    form = BookSpotForm()

    available_spot = ParkingSpot.query.filter_by(lot_id=lot.id, status='Available').order_by(ParkingSpot.spot_number).first()

    if not available_spot:
        flash(f'No available spots found in {lot.name} at the moment. Please try another lot or wait for a spot to clear.', 'danger')
        return redirect(url_for('user_routes.dashboard'))

    if form.validate_on_submit():
        try:
            new_reservation = Reservation(
                user_id=current_user.id,
                spot_id=available_spot.id, 
                vehicle_number=form.vehicle_number.data,
                booking_timestamp=datetime.utcnow(),
                status='pending' 
            )
            available_spot.status = 'Reserved' 
            
            db.session.add(new_reservation)
            db.session.commit()
            
            flash(f'Spot {available_spot.spot_number} in {lot.name} has been successfully reserved for vehicle {form.vehicle_number.data}! Please check in when you arrive.', 'success')
            return redirect(url_for('user_routes.dashboard')) 
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while booking the spot: {e}', 'danger')
            return render_template('user/book_spot.html', title=f'Book Spot in {lot.name}', form=form, lot=lot, allocated_spot=available_spot)
    
    return render_template('user/book_spot.html', 
                           title=f'Book Spot in {lot.name}', 
                           form=form, 
                           lot=lot, 
                           allocated_spot=available_spot)

@bp.route('/check_in_reservation/<int:reservation_id>', methods=['POST']) # Renamed route
@login_required
def check_in_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.user_id != current_user.id:
        flash('You do not have permission to check into this reservation.', 'danger')
        return redirect(url_for('user_routes.dashboard'))
    
    if reservation.status != 'pending':
        flash('This reservation is not in a pending state and cannot be checked in.', 'danger')
        return redirect(url_for('user_routes.dashboard'))

    spot = reservation.parking_spot
    if spot.status != 'Reserved' or reservation.spot_id != spot.id:
        flash('The parking spot status does not match the reservation status.', 'danger')
        return redirect(url_for('user_routes.dashboard'))

    try:
        reservation.status = 'active' 
        reservation.check_in_timestamp = datetime.utcnow() 
        
        spot.status = 'Occupied' 
        
        db.session.commit()
        flash(f'Successfully checked into spot {spot.spot_number}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred during check-in: {e}', 'danger')
    
    return redirect(url_for('user_routes.dashboard'))

@bp.route('/park_out_page/<int:reservation_id>', methods=['GET']) # Route to display the park-out confirmation page
@login_required
def park_out_page(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.user_id != current_user.id:
        flash('You do not have permission to view this park out page.', 'danger')
        return redirect(url_for('user_routes.dashboard'))
    
    if reservation.status != 'active':
        flash('This reservation is not in an active state.', 'danger')
        return redirect(url_for('user_routes.dashboard'))

    # Calculate estimated cost and duration for display on the page
    estimated_duration_string = "N/A"
    estimated_cost = 0.0

    if reservation.check_in_timestamp:
        current_time = datetime.utcnow()
        duration = current_time - reservation.check_in_timestamp
        duration_hours = duration.total_seconds() / 3600.0
        
        # Round up to nearest hour for display, ensure minimum 1 hour charge
        charged_hours = max(1.0, (duration.total_seconds() / 3600.0)) # Use raw duration for display calculation
        
        # Format duration string
        hours = int(duration_hours)
        minutes = int((duration_hours * 60) % 60)
        estimated_duration_string = f"{hours} hours {minutes} minutes"

        # Calculate estimated cost based on lot price
        # For actual cost, we will round up to nearest hour.
        estimated_cost = max(1.0, round(duration_hours)) * reservation.parking_spot.parking_lot.price_per_hour
        estimated_cost = round(estimated_cost, 2) # Round to 2 decimal places

    return render_template('user/release_spot.html', 
                           title='Confirm Park Out', 
                           reservation=reservation,
                           estimated_duration_string=estimated_duration_string,
                           estimated_cost=estimated_cost)

@bp.route('/park_out_action/<int:reservation_id>', methods=['POST']) # Renamed route
@login_required
def park_out_action(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.user_id != current_user.id:
        flash('You do not have permission to park out from this reservation.', 'danger')
        return redirect(url_for('user_routes.dashboard'))
    
    if reservation.status != 'active':
        flash('This reservation is not in an active state and cannot be parked out.', 'danger')
        return redirect(url_for('user_routes.dashboard'))

    spot = reservation.parking_spot
    parking_lot = spot.parking_lot

    if spot.status != 'Occupied' or reservation.spot_id != spot.id:
        flash('The parking spot status does not match the reservation status. Please contact support.', 'danger')
        return redirect(url_for('user_routes.dashboard'))

    try:
        reservation.check_out_timestamp = datetime.utcnow()
        
        if reservation.check_in_timestamp:
            duration = reservation.check_out_timestamp - reservation.check_in_timestamp
            duration_hours = duration.total_seconds() / 3600.0
            
            # Ensure minimum 1 hour charge, round up to nearest hour for final calculation
            charged_hours = max(1.0, round(duration_hours))
            reservation.total_cost = charged_hours * parking_lot.price_per_hour
        else:
            flash('Error: Check-in timestamp missing for an active reservation. Cost set to 0.', 'danger')
            reservation.total_cost = 0.0 
            
        reservation.status = 'completed' 
        spot.status = 'Available' 
        
        db.session.commit()
        
        flash(f'Successfully parked out from spot {spot.spot_number}. Your parking cost is ₹{reservation.total_cost:.2f}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred during park-out: {e}', 'danger')
    
    return redirect(url_for('user_routes.dashboard'))

@bp.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.user_id != current_user.id:
        flash('You do not have permission to cancel this reservation.', 'danger')
        return redirect(url_for('user_routes.dashboard'))
    
    if reservation.status != 'pending':
        flash('This reservation cannot be cancelled. It is either active or already completed/cancelled.', 'danger')
        return redirect(url_for('user_routes.dashboard'))
    
    try:
        spot = reservation.parking_spot
        
        reservation.status = 'cancelled' 
        
        if spot.status == 'Reserved' and spot.id == reservation.spot_id:
            spot.status = 'Available'
        
        db.session.commit()
        flash(f'Reservation for spot {spot.spot_number} has been cancelled.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while cancelling the reservation: {e}', 'danger')
    
    return redirect(url_for('user_routes.dashboard'))

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    # Pass current user's username and email to the form for validation
    form = EditProfileForm(original_username=current_user.username, original_email=current_user.email)
    
    # Populate form fields with current user data on GET request
    if request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.full_name.data = current_user.full_name # Populate full_name

    if form.validate_on_submit():
        try:
            current_user.username = form.username.data
            current_user.email = form.email.data
            current_user.full_name = form.full_name.data # Update full_name
            db.session.commit()
            flash('Your profile has been updated successfully!', 'success')
            if current_user.is_admin:
                # Redirect admin to the admin dashboard
                return redirect(url_for('admin_routes.dashboard'))
            else:
                # Redirect regular user to their dashboard
                return redirect(url_for('user_routes.dashboard'))
    
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating your profile: {e}', 'danger')

    return render_template('user/edit_profile.html', title='Edit Profile', form=form)

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        try:
            # The validate_current_password method in the form already checks the current password
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been changed successfully!', 'success')
            if current_user.is_admin:
                # Redirect admin to the admin dashboard
                return redirect(url_for('admin_routes.dashboard'))
            else:
                # Redirect regular user to their dashboard
                return redirect(url_for('user_routes.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while changing your password: {e}', 'danger')
    return render_template('user/change_password.html', title='Change Password', form=form)

# @bp.route('/view_lot_spots/<int:lot_id>')
# @login_required
# def view_lot_spots(lot_id):
#     lot = ParkingLot.query.get_or_404(lot_id)
#     spots = lot.spots.order_by(ParkingSpot.spot_number).all()
    
#     # You might want to filter spots by status for user view, e.g., only show available/reserved
#     # For now, showing all spots in the lot with their status
    
#     return render_template('user/view_lot_spots.html', lot=lot, spots=spots, title=f'Spots in {lot.name}')