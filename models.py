from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    reservations = db.relationship('Reservation', backref='tenant', lazy='dynamic') 

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True) 
    address = db.Column(db.String(255),nullable=False)
    pin_code = db.Column(db.String(10),nullable=False, unique=True)
    price_per_hour = db.Column(db.Float, nullable=False)
    maximum_capacity = db.Column(db.Integer, nullable=False) 
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    spots = db.relationship('ParkingSpot', backref='parking_lot', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ParkingLot {self.name}>'

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_number = db.Column(db.String(20), nullable=False)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    status = db.Column(db.String(20), default='Available', nullable=False) 
    spot_reservations = db.relationship('Reservation', backref='parking_spot', lazy='dynamic')

    __table_args__ = (db.UniqueConstraint('lot_id', 'spot_number', name='_lot_spot_uc'),)

    def get_active_reservation(self):
        return self.spot_reservations.filter_by(status='active').first()

    def __repr__(self):
        return f'<ParkingSpot {self.spot_number} in Lot {self.lot_id} - Status: {self.status}>'

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id', ondelete='SET NULL'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_number = db.Column(db.String(20), nullable=False) 
    booking_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    check_in_timestamp = db.Column(db.DateTime, nullable=True)
    check_out_timestamp = db.Column(db.DateTime, nullable=True)
    total_cost = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)

    def __repr__(self):
        spot_info = self.parking_spot.spot_number if self.parking_spot else f"Deleted Spot (ID: {self.spot_id})"
        user_info = self.tenant.username if self.tenant else f"User ID: {self.user_id}"
        return f'<Reservation {self.id} | Spot {spot_info} | User {user_info} | Status: {self.status}>'