from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from datetime import datetime, timedelta
from .forms import BookSpotForm, CheckInForm, ParkOutForm, EditProfileForm, ChangePasswordForm 
from .models import ParkingLot, ParkingSpot, User, Reservation 
from . import db
from sqlalchemy import or_ 
from werkzeug.security import generate_password_hash, check_password_hash 
import pytz 
bp = Blueprint('user', __name__)

IST = pytz.timezone('Asia/Kolkata')

@bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
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
    user_reservations_raw = Reservation.query.filter(
        Reservation.user_id == current_user.id,
        Reservation.status.in_(['pending', 'active', 'completed', 'cancelled'])
    ).order_by(Reservation.booking_timestamp.desc()).all()

    user_reservations_table = []
    has_active_or_pending_reservation = False
    current_user_reservation_detail = None 

    for res in user_reservations_raw:
        # Check for active or pending reservation for the alert/detail box
        if res.status in ['pending', 'active'] and not current_user_reservation_detail:
            has_active_or_pending_reservation = True
            # Prepare details for the single active/pending reservation
            booking_ist_str = res.booking_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
            check_in_ist_str = None
            if res.check_in_timestamp:
                check_in_ist_str = res.check_in_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
            
            current_user_reservation_detail = {
                'id': res.id,
                'parking_lot_name': res.parking_spot.parking_lot.name if res.parking_spot and res.parking_spot.parking_lot else 'N/A',
                'spot_number': res.parking_spot.spot_number if res.parking_spot else 'N/A',
                'vehicle_number': res.vehicle_number,
                'booking_timestamp_ist_str': booking_ist_str,
                'check_in_timestamp_ist_str': check_in_ist_str,
                'status': res.status,
                'total_cost': res.total_cost, # Will be None for active/pending
                'res_object': res # Keep the original object for actions
            }

        # Prepare all reservations for the history table
        booking_ist_str_for_table = res.booking_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
        check_in_ist_str_for_table = None
        if res.check_in_timestamp:
            check_in_ist_str_for_table = res.check_in_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
        check_out_ist_str_for_table = None
        if res.check_out_timestamp:
            check_out_ist_str_for_table = res.check_out_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
        
        user_reservations_table.append({
            'id': res.id,
            'parking_spot': res.parking_spot,
            'vehicle_number': res.vehicle_number,
            'booking_timestamp_ist_str': booking_ist_str_for_table,
            'check_in_timestamp_ist_str': check_in_ist_str_for_table,
            'check_out_timestamp_ist_str': check_out_ist_str_for_table,
            'total_cost': res.total_cost,
            'status': res.status
        })


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
            # Convert checkout timestamp to IST for chart labels
            checkout_ist_str = res.check_out_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d')
            parking_cost_chart_data.append([checkout_ist_str, res.total_cost])
    parking_cost_chart_data.reverse() # Show oldest first on chart

    # 2. Parking Frequency Chart Data (last 7 days)
    parking_frequency_data = {}
    today_utc = datetime.utcnow().date()
    today_ist = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(IST).date()

    for i in range(7):
        date_ist = today_ist - timedelta(days=i)
        parking_frequency_data[date_ist.strftime('%Y-%m-%d')] = 0
    
    for res in completed_reservations:
        if res.check_out_timestamp:
            # Convert check_out_timestamp to IST date for comparison
            checkout_date_ist = res.check_out_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).date()
            if (today_ist - checkout_date_ist).days < 7:
                date_str = checkout_date_ist.strftime('%Y-%m-%d')
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
                           user_reservations_table=user_reservations_table, # Pass the modified list for the table
                           has_active_or_pending_reservation=has_active_or_pending_reservation,
                           current_user_reservation_detail=current_user_reservation_detail, # Pass the single detail object
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
        return redirect(url_for('user.dashboard'))

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
            return redirect(url_for('user.dashboard')) 
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while booking the spot: {e}', 'danger')
            return render_template('user/book_spot.html', title=f'Book Spot in {lot.name}', form=form, lot=lot, allocated_spot=available_spot)
    
    return render_template('user/book_spot.html', 
                           title=f'Book Spot in {lot.name}', 
                           form=form, 
                           lot=lot, 
                           allocated_spot=available_spot)

@bp.route('/check_in_reservation/<int:reservation_id>', methods=['POST']) 
@login_required
def check_in_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.user_id != current_user.id:
        flash('You do not have permission to check into this reservation.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    if reservation.status != 'pending':
        flash('This reservation is not in a pending state and cannot be checked in.', 'danger')
        return redirect(url_for('user.dashboard'))

    spot = reservation.parking_spot
    if spot.status != 'Reserved' or reservation.spot_id != spot.id:
        flash('The parking spot status does not match the reservation status.', 'danger')
        return redirect(url_for('user.dashboard'))

    try:
        reservation.status = 'active' 
        reservation.check_in_timestamp = datetime.utcnow() 
        
        spot.status = 'Occupied' 
        
        db.session.commit()
        flash(f'Successfully checked into spot {spot.spot_number}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred during check-in: {e}', 'danger')
    
    return redirect(url_for('user.dashboard'))

@bp.route('/park_out_page/<int:reservation_id>', methods=['GET']) 
@login_required
def park_out_page(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.user_id != current_user.id:
        flash('You do not have permission to view this park out page.', 'danger')
        return redirect(url_for('user.dashboard'))
   
    check_in_ist_str = None
    current_time_ist_str = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M:%S (IST)')
    check_out_ist_str = None
    cancellation_ist_str = None
    estimated_duration_string = "N/A"
    estimated_cost = 0.0

    if reservation.status == 'active':
        if reservation.check_in_timestamp:
            check_in_ist_str = reservation.check_in_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M:%S (IST)')
            
            current_time_utc = datetime.utcnow()
            duration = current_time_utc - reservation.check_in_timestamp
            duration_hours = duration.total_seconds() / 3600.0
            
            charged_hours = max(1.0, (duration.total_seconds() / 3600.0))
            
            hours = int(duration_hours)
            minutes = int((duration_hours * 60) % 60)
            estimated_duration_string = f"{hours} hours {minutes} minutes"

            estimated_cost = max(1.0, round(duration_hours)) * reservation.parking_spot.parking_lot.price_per_hour
            estimated_cost = round(estimated_cost, 2)
    elif reservation.status == 'completed':
        if reservation.check_out_timestamp:
            check_out_ist_str = reservation.check_out_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')
    elif reservation.status == 'cancelled':
        if reservation.cancellation_timestamp:
            cancellation_ist_str = reservation.cancellation_timestamp.replace(tzinfo=pytz.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M (IST)')

    return render_template('user/release_spot.html', 
                           title='Confirm Park Out', 
                           reservation=reservation,
                           estimated_duration_string=estimated_duration_string,
                           estimated_cost=estimated_cost,
                           check_in_ist_str=check_in_ist_str, 
                           current_time_ist_str=current_time_ist_str,
                           check_out_ist_str=check_out_ist_str, 
                           cancellation_ist_str=cancellation_ist_str) 

@bp.route('/park_out_action/<int:reservation_id>', methods=['POST']) # Renamed route
@login_required
def park_out_action(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.user_id != current_user.id:
        flash('You do not have permission to park out from this reservation.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    if reservation.status != 'active':
        flash('This reservation is not in an active state and cannot be parked out.', 'danger')
        return redirect(url_for('user.dashboard'))

    spot = reservation.parking_spot
    parking_lot = spot.parking_lot

    if spot.status != 'Occupied' or reservation.spot_id != spot.id:
        flash('The parking spot status does not match the reservation status. Please contact support.', 'danger')
        return redirect(url_for('user.dashboard'))

    try:
        reservation.check_out_timestamp = datetime.utcnow()
        
        if reservation.check_in_timestamp:
            duration = reservation.check_out_timestamp - reservation.check_in_timestamp
            duration_hours = duration.total_seconds() / 3600.0
            
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
    
    return redirect(url_for('user.dashboard'))

@bp.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.user_id != current_user.id:
        flash('You do not have permission to cancel this reservation.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    if reservation.status != 'pending':
        flash('This reservation cannot be cancelled. It is either active or already completed/cancelled.', 'danger')
        return redirect(url_for('user.dashboard'))
    
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
    
    return redirect(url_for('user.dashboard'))

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
            current_user.full_name = form.full_name.data 
            db.session.commit()
            flash('Your profile has been updated successfully!', 'success')
            if current_user.is_admin:
                # Redirect admin to the admin dashboard
                return redirect(url_for('admin.dashboard'))
            else:
                # Redirect regular user to their dashboard
                return redirect(url_for('user.dashboard'))
    
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
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been changed successfully!', 'success')
            if current_user.is_admin:
                # Redirect admin to the admin dashboard
                return redirect(url_for('admin.dashboard'))
            else:
                # Redirect regular user to their dashboard
                return redirect(url_for('user.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while changing your password: {e}', 'danger')
    return render_template('user/change_password.html', title='Change Password', form=form)