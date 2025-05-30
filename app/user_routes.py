from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .models import ParkingLot, ParkingSpot, Reservation, User
from .forms import BookSpotForm, EditProfileForm
from . import db
from sqlalchemy import or_, func, desc
from datetime import datetime, timedelta
from math import ceil
from collections import Counter

bp = Blueprint('user_routes', __name__, url_prefix='/user')

@bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if current_user.is_admin:
        # Admins should use their own dashboard
        return redirect(url_for('admin_routes.dashboard'))
    
    search_term = request.form.get('search_term', '').strip()
    
    query = ParkingLot.query
    if search_term:
        # Simple search: checks name, address, or pin_code
        query = query.filter(
            or_(
                ParkingLot.name.ilike(f'%{search_term}%'),
                ParkingLot.address.ilike(f'%{search_term}%'),
                ParkingLot.pin_code.ilike(f'%{search_term}%')
            )
        )
    parking_lots = query.order_by(ParkingLot.name).all()
    
    # Fetch recent parking history for the user (both active and completed for the table)
    user_reservations_table = Reservation.query.filter_by(user_id=current_user.id)\
                                       .order_by(Reservation.parking_timestamp.desc()).limit(5).all()
    
    # Fetch data for parking cost chart (last 5 completed reservations)
    completed_reservations_chart = Reservation.query.filter_by(user_id=current_user.id)\
                                        .filter(Reservation.leaving_timestamp.isnot(None))\
                                        .filter(Reservation.parking_cost.isnot(None))\
                                        .order_by(Reservation.leaving_timestamp.desc()).limit(5).all()
    
    parking_cost_chart_data = []
    if completed_reservations_chart:
        # Prepare in reverse chronological order for chart (oldest of the 5 first)
        for res in reversed(completed_reservations_chart):
            label = f"{res.parking_spot.parking_lot.name} ({res.leaving_timestamp.strftime('%b %d')})"
            parking_cost_chart_data.append([label, res.parking_cost])
            
    # Data for Parking Frequency Chart (Last 7 Days)
    parking_frequency_data = []
    today = datetime.utcnow().date()
    for i in range(6, -1, -1): # From 6 days ago to today
        day = today - timedelta(days=i)
        count = Reservation.query.filter_by(user_id=current_user.id)\
                                 .filter(func.date(Reservation.parking_timestamp) == day)\
                                 .count()
        parking_frequency_data.append([day.strftime('%a, %b %d'), count])

    # Data for Most Visited Lots Chart (Last 10 Completed Parkings)
    last_ten_completed_reservations = Reservation.query.filter_by(user_id=current_user.id)\
                                          .filter(Reservation.leaving_timestamp.isnot(None))\
                                          .join(ParkingSpot, Reservation.spot_id == ParkingSpot.id)\
                                          .join(ParkingLot, ParkingSpot.lot_id == ParkingLot.id)\
                                          .add_columns(ParkingLot.name.label("lot_name"))\
                                          .order_by(desc(Reservation.leaving_timestamp)).limit(10).all()
    
    lot_visit_counts = Counter()
    if last_ten_completed_reservations:
        for res_tuple in last_ten_completed_reservations:
            # The reservation object is res_tuple.Reservation, lot_name is res_tuple.lot_name
            lot_visit_counts[res_tuple.lot_name] += 1 
            
    most_visited_lots_data = [[lot_name, count] for lot_name, count in lot_visit_counts.most_common()]

    return render_template('user/dashboard.html', title='User Dashboard', 
                           parking_lots=parking_lots, 
                           user_reservations_table=user_reservations_table, # For the table
                           search_term=search_term,
                           parking_cost_chart_data=parking_cost_chart_data, # For the chart
                           parking_frequency_data=parking_frequency_data,
                           most_visited_lots_data=most_visited_lots_data)

# Placeholder for viewing spots in a lot (similar to admin_routes)
@bp.route('/lot/<int:lot_id>/spots')
@login_required
def view_lot_spots(lot_id):
    if current_user.is_admin:
        return redirect(url_for('admin_routes.view_spots', lot_id=lot_id)) # Or some other admin page

    lot = ParkingLot.query.get_or_404(lot_id)
    # Spots ordered by name for consistency, similar to admin view
    spots = ParkingSpot.query.filter_by(lot_id=lot.id).order_by(ParkingSpot.spot_number).all()
    return render_template('user/view_lot_spots_user.html', title=f"Spots in {lot.name}", lot=lot, spots=spots, ParkingSpot=ParkingSpot)

# Placeholder for booking a spot
@bp.route('/spot/<int:spot_id>/book', methods=['GET', 'POST'])
@login_required
def book_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    lot = ParkingLot.query.get_or_404(spot.lot_id)

    if current_user.is_admin:
        flash('Admins cannot book spots directly. This page is for user bookings.', 'warning')
        return redirect(url_for('admin_routes.view_spot_details', spot_id=spot.id))

    if spot.status != 'A': # Check status field
        flash(f'Spot {spot.spot_number} in {lot.name} is currently unavailable.', 'danger')
        return redirect(url_for('user_routes.view_lot_spots', lot_id=spot.lot_id))

    form = BookSpotForm()
    if form.validate_on_submit():
        try:
            reservation = Reservation(
                user_id=current_user.id,
                spot_id=spot.id,
                vehicle_number=form.vehicle_number.data
                # parking_timestamp is default utcnow
            )
            spot.status = 'O' # Set status to Occupied
            db.session.add(reservation)
            db.session.commit()
            flash(f'Successfully booked spot {spot.spot_number} in {lot.name} for vehicle {form.vehicle_number.data}!', 'success')
            return redirect(url_for('user_routes.dashboard')) # Redirect to user dashboard or a 'my bookings' page
        except Exception as e:
            db.session.rollback()
            flash(f'Error booking spot: {e}', 'danger')
    
    return render_template('user/book_spot.html', title=f'Book Spot: {spot.spot_number}', form=form, spot=spot, lot=lot)

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username, current_user.email)
    if form.validate_on_submit():
        try:
            current_user.username = form.username.data
            current_user.email = form.email.data
            db.session.commit()
            flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('user_routes.dashboard')) # Or to a profile view page
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {e}', 'danger')
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('user/edit_profile.html', title='Edit Profile', form=form)

# Placeholder for Release Spot Page (GET request to show form/confirmation)
@bp.route('/reservation/<int:reservation_id>/release', methods=['GET'])
@login_required
def release_spot_page(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id != current_user.id and not current_user.is_admin:
        flash('You are not authorized to release this spot.', 'danger')
        return redirect(url_for('user_routes.dashboard'))
    if reservation.leaving_timestamp:
        flash('This spot has already been released.', 'info')
        return redirect(url_for('user_routes.dashboard'))
    
    # Logic to calculate cost can be added here if needed before showing the page
    # For now, just showing a confirmation.
    # spot = reservation.parking_spot
    # lot = spot.parking_lot
    # duration = datetime.utcnow() - reservation.parking_timestamp
    # hours = ceil(duration.total_seconds() / 3600)
    # cost = hours * lot.price_per_hour

    return render_template('user/release_spot.html', title='Release Parking Spot', reservation=reservation)

# Placeholder for Release Spot Action (POST request to perform release)
@bp.route('/reservation/<int:reservation_id>/release/confirm', methods=['POST'])
@login_required
def release_spot_action(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id != current_user.id and not current_user.is_admin:
        flash('You are not authorized to release this spot.', 'danger')
        return redirect(url_for('user_routes.dashboard'))
    if reservation.leaving_timestamp:
        flash('This spot has already been released.', 'info')
        return redirect(url_for('user_routes.dashboard'))

    try:
        spot = reservation.parking_spot
        lot = spot.parking_lot # Get the lot for price_per_hour
        
        reservation.leaving_timestamp = datetime.utcnow()
        
        duration = reservation.leaving_timestamp - reservation.parking_timestamp
        hours = (duration.total_seconds() + 3599) // 3600 
        if hours < 1: hours = 1 
        reservation.parking_cost = hours * lot.price_per_hour
        
        spot.status = 'A' # Set status to Available
        db.session.commit()
        flash(f'Spot {spot.spot_number} in {lot.name} released. Total cost: ₹{reservation.parking_cost:.2f}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error releasing spot: {e}', 'danger')
    return redirect(url_for('user_routes.dashboard')) 