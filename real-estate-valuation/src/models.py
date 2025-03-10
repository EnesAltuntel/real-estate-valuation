from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    properties = db.relationship('Property', backref='owner', lazy=True)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Location details
    city = db.Column(db.String(50), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    neighborhood = db.Column(db.String(100), nullable=False)
    
    # Property characteristics
    property_type = db.Column(db.String(50), nullable=False)  # Apartment, House, etc.
    size_sqm = db.Column(db.Float, nullable=False)
    room_count = db.Column(db.Integer, nullable=False)
    building_age = db.Column(db.Integer)
    floor_number = db.Column(db.Integer)
    total_floors = db.Column(db.Integer)
    
    # Additional features
    heating_type = db.Column(db.String(50))
    has_elevator = db.Column(db.Boolean, default=False)
    has_parking = db.Column(db.Boolean, default=False)
    has_balcony = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    valuations = db.relationship('Valuation', backref='property', lazy=True)

class Valuation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    estimated_value = db.Column(db.Float, nullable=False)
    confidence_score = db.Column(db.Float)
    valuation_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Market data used for valuation
    similar_properties_count = db.Column(db.Integer)
    price_per_sqm = db.Column(db.Float)
    market_trend = db.Column(db.Float)  # Percentage change in last 3 months

class ScrapedListing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.String(50), unique=True)
    url = db.Column(db.String(500))
    price = db.Column(db.Float, nullable=False)
    
    # Property details (same as Property model)
    city = db.Column(db.String(50), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    neighborhood = db.Column(db.String(100), nullable=False)
    property_type = db.Column(db.String(50))
    size_sqm = db.Column(db.Float)
    room_count = db.Column(db.Integer)
    building_age = db.Column(db.Integer)
    floor_number = db.Column(db.Integer)
    
    scrape_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True) 