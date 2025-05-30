from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    reservations = db.relationship('Reservation', backref='tenant', lazy='dynamic') # Changed from 'user' to 'tenant'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True) # prime_location_name
    address = db.Column(db.String(255))
    pin_code = db.Column(db.String(10))
    price_per_hour = db.Column(db.Float, nullable=False) # Price
    maximum_capacity = db.Column(db.Integer, nullable=False) # maximum_number_of_spots
    spots = db.relationship('ParkingSpot', backref='parking_lot', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ParkingLot {self.name}>'

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_number = db.Column(db.String(20), nullable=False) # e.g., A01, B12
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    status = db.Column(db.String(1), default='A', nullable=False)  # O=Occupied, A=Available
    reservations = db.relationship('Reservation', backref='parking_spot', lazy='dynamic')

    __table_args__ = (db.UniqueConstraint('lot_id', 'spot_number', name='_lot_spot_uc'),)

    def get_active_reservation(self):
        """Returns the active reservation for this spot, if any."""
        return self.reservations.filter_by(leaving_timestamp=None).first()

    def __repr__(self):
        return f'<ParkingSpot {self.spot_number} in Lot {self.lot_id}>'

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parking_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    leaving_timestamp = db.Column(db.DateTime, nullable=True)
    parking_cost = db.Column(db.Float, nullable=True)
    vehicle_number = db.Column(db.String(20), nullable=True) # Optional: if you want to store vehicle number

    def __repr__(self):
        return f'<Reservation {self.id} for Spot {self.spot_id} by User {self.user_id}>' 