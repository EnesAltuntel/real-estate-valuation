from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Property, Valuation, ScrapedListing
from scraper import SahibindenScraper
from valuation import PropertyValuator
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///real_estate.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize scraper and valuator
scraper = SahibindenScraper()
valuator = PropertyValuator()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    properties = Property.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', properties=properties)

@app.route('/property/add', methods=['GET', 'POST'])
@login_required
def add_property():
    if request.method == 'POST':
        property_data = {
            'city': request.form.get('city'),
            'district': request.form.get('district'),
            'neighborhood': request.form.get('neighborhood'),
            'property_type': request.form.get('property_type'),
            'size_sqm': float(request.form.get('size_sqm')),
            'room_count': int(request.form.get('room_count')),
            'building_age': int(request.form.get('building_age')),
            'floor_number': int(request.form.get('floor_number'))
        }
        
        property = Property(
            user_id=current_user.id,
            **property_data
        )
        db.session.add(property)
        db.session.commit()
        
        # Perform valuation
        valuation_result = valuator.estimate_value(property_data)
        valuator.save_valuation(property.id, valuation_result)
        
        flash('Property added successfully')
        return redirect(url_for('dashboard'))
    
    return render_template('add_property.html')

@app.route('/property/<int:property_id>')
@login_required
def view_property(property_id):
    property = Property.query.get_or_404(property_id)
    if property.user_id != current_user.id:
        flash('Unauthorized access')
        return redirect(url_for('dashboard'))
    
    valuations = Valuation.query.filter_by(property_id=property_id).order_by(Valuation.valuation_date.desc()).all()
    return render_template('property_detail.html', property=property, valuations=valuations)

@app.route('/api/market-data')
@login_required
def get_market_data():
    city = request.args.get('city')
    district = request.args.get('district')
    
    # Get historical price data
    three_months_ago = datetime.utcnow() - timedelta(days=90)
    listings = ScrapedListing.query.filter(
        ScrapedListing.city == city,
        ScrapedListing.district == district,
        ScrapedListing.scrape_date >= three_months_ago
    ).order_by(ScrapedListing.scrape_date).all()
    
    data = {
        'dates': [l.scrape_date.strftime('%Y-%m-%d') for l in listings],
        'prices': [l.price for l in listings],
        'price_per_sqm': [l.price / l.size_sqm if l.size_sqm else 0 for l in listings]
    }
    
    return jsonify(data)

@app.route('/api/update-listings')
@login_required
def update_listings():
    try:
        city = request.args.get('city')
        district = request.args.get('district')
        
        listings = scraper.scrape_listings(city, district)
        scraper.save_listings_to_db(listings)
        
        return jsonify({'success': True, 'message': f'Successfully scraped {len(listings)} listings'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 