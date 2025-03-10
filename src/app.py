from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Property, Valuation, ScrapedListing, City, District, Neighborhood, get_all_cities, get_city_districts, get_district_neighborhoods
from scraper import SahibindenScraper
from valuation import PropertyValuator
import os
from datetime import datetime, timedelta
import random

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
            flash('Bu e-posta adresi zaten kayıtlı')
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
        
        flash('Geçersiz e-posta veya şifre')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Tüm mülkleri ve değerlemelerini tek sorguda çek
    properties = Property.query.filter_by(user_id=current_user.id).all()
    
    # Her mülk için değerleme verilerini ayrı ayrı çek
    for prop in properties:
        valuations = Valuation.query.filter_by(property_id=prop.id).order_by(Valuation.valuation_date.desc()).all()
        if valuations:
            prop.valuations = valuations
        else:
            # Eğer değerleme yoksa, yeni bir değerleme yap
            property_data = {
                'city': prop.city,
                'district': prop.district,
                'neighborhood': prop.neighborhood,
                'property_type': prop.property_type,
                'size_sqm': float(prop.size_sqm),
                'room_count': int(prop.room_count),
                'building_age': int(prop.building_age),
                'floor_number': int(prop.floor_number)
            }
            valuation_result = valuator.estimate_value(property_data)
            new_valuation = valuator.save_valuation(prop.id, valuation_result)
            prop.valuations = [new_valuation] if new_valuation else []
    
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
        
        flash('Mülk başarıyla eklendi')
        return redirect(url_for('dashboard'))
    
    return render_template('add_property.html')

@app.route('/property/<int:property_id>')
@login_required
def view_property(property_id):
    property = Property.query.get_or_404(property_id)
    if property.user_id != current_user.id:
        flash('Yetkisiz erişim')
        return redirect(url_for('dashboard'))
    
    valuations = Valuation.query.filter_by(property_id=property_id).order_by(Valuation.valuation_date.desc()).all()
    latest_valuation = valuations[0] if valuations else None
    
    return render_template('property_detail.html', property=property, valuations=valuations, latest_valuation=latest_valuation)

@app.route('/api/locations/cities')
def get_cities():
    cities = get_all_cities()
    return jsonify(cities)

@app.route('/api/locations/districts/<city>')
def get_districts(city):
    districts = get_city_districts(city)
    return jsonify(districts)

@app.route('/api/locations/neighborhoods/<city>/<district>')
def get_neighborhoods(city, district):
    neighborhoods = get_district_neighborhoods(city, district)
    return jsonify(neighborhoods)

@app.route('/api/market-data')
def get_market_data():
    city = request.args.get('city')
    district = request.args.get('district')
    neighborhood = request.args.get('neighborhood')
    
    # Son 6 ayın tarihlerini oluştur
    today = datetime.now()
    dates = [(today - timedelta(days=30 * i)).strftime('%Y-%m-%d') for i in range(6)]
    dates.reverse()  # En eskiden en yeniye sırala
    
    # Metrekare fiyat bazını belirle (şehre göre farklı)
    if city == 'İstanbul':
        base_price = 25000
    elif city == 'Ankara':
        base_price = 12000
    elif city == 'İzmir':
        base_price = 15000
    else:
        base_price = 10000
    
    # Son 6 ay için fiyat değişimini simüle et
    growth_trend = 1.02  # %2'lik bir artış trendi
    prices_per_sqm = []
    
    # Bölgeye özgü düzeltme faktörü (ilçe bazlı)
    district_factor = 1.0
    if district in ['Kadıköy', 'Beşiktaş', 'Sarıyer', 'Çankaya', 'Karşıyaka']:
        district_factor = 1.2
    elif district in ['Üsküdar', 'Kağıthane', 'Keçiören', 'Bornova']:
        district_factor = 1.0
    else:
        district_factor = 0.9
    
    # Mahalle bazlı düzeltme
    neighborhood_factor = 1.0
    
    # İstanbul/Kadıköy mahalleleri
    if city == 'İstanbul' and district == 'Kadıköy':
        if neighborhood == 'Caferağa':
            neighborhood_factor = 74000 / 35000  # Kadıköy ortalamasına göre düzeltme
        elif neighborhood == 'Erenköy':
            neighborhood_factor = 125000 / 35000
        elif neighborhood == 'Fenerbahçe':
            neighborhood_factor = 176000 / 35000
        elif neighborhood == 'Göztepe':
            neighborhood_factor = 132000 / 35000
        elif neighborhood == 'Kozyatağı':
            neighborhood_factor = 106000 / 35000
        elif neighborhood == 'Suadiye':
            neighborhood_factor = 150000 / 35000
    
    # İstanbul/Üsküdar mahalleleri
    if city == 'İstanbul' and district == 'Üsküdar':
        if neighborhood == 'Acıbadem':
            neighborhood_factor = 115570 / 30000  # Üsküdar ortalamasına göre düzeltme
        elif neighborhood == 'Altunizade':
            neighborhood_factor = 130000 / 30000
        elif neighborhood == 'Beylerbeyi':
            neighborhood_factor = 84000 / 30000
        elif neighborhood == 'Kuzguncuk':
            neighborhood_factor = 102000 / 30000
        elif neighborhood == 'Çengelköy':
            neighborhood_factor = 83000 / 30000
    
    # Fiyatları hesapla
    base_price = base_price * district_factor * neighborhood_factor
    for i in range(6):
        # Biraz rastgelelik ekle
        random_factor = 0.98 + (random.random() * 0.04)  # %±2 rastgele dalgalanma
        month_price = base_price * (growth_trend ** i) * random_factor
        prices_per_sqm.append(int(month_price))
    
    # Ortalama m² fiyatı (en son ay)
    avg_price_sqm = prices_per_sqm[-1]
    
    # Örnek mülk için toplam fiyatlar (m² fiyatı * mülk büyüklüğü)
    property_size = float(request.args.get('size_sqm', 80))
    total_prices = [int(price * property_size) for price in prices_per_sqm]
    
    # Son 3 aydaki fiyat trendi (% olarak)
    if len(prices_per_sqm) >= 3:
        trend = ((prices_per_sqm[-1] / prices_per_sqm[-3]) - 1) * 100
    else:
        trend = 0
    
    return jsonify({
        'dates': dates,
        'prices': total_prices,
        'price_per_sqm': prices_per_sqm,
        'avg_price_sqm': avg_price_sqm,
        'price_trend': f"{trend:.1f}%",
        'market_trend': trend,
        'avg_days_on_market': 45,
        'inventory': 120
    })

@app.route('/api/update-listings')
def update_listings():
    city = request.args.get('city')
    district = request.args.get('district')
    
    try:
        listings = scraper.scrape_listings(city, district)
        return jsonify({'success': True, 'listings_count': len(listings)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update-valuation/<int:property_id>')
@login_required
def update_valuation(property_id):
    """Mülk değerlemesini güncelleyen endpoint"""
    try:
        # Mülkü veritabanından al
        property = Property.query.get_or_404(property_id)
        
        # Güvenlik kontrolü - mülk sahibi mi?
        if property.user_id != current_user.id:
            return jsonify({
                'success': False, 
                'message': 'Bu mülk üzerinde işlem yapmaya yetkiniz yok'
            }), 403
        
        # Mülk verilerini hazırla
        property_data = {
            'city': property.city,
            'district': property.district,
            'neighborhood': property.neighborhood,
            'property_type': property.property_type,
            'size_sqm': property.size_sqm,
            'room_count': property.room_count,
            'building_age': property.building_age,
            'floor_number': property.floor_number
        }
        
        # Değerlemeyi yapan sınıfı kullanarak yeni değerleme oluştur
        valuation_result = valuator.estimate_value(property_data)
        valuator.save_valuation(property.id, valuation_result)
        
        return jsonify({
            'success': True, 
            'message': 'Değerleme başarıyla güncellendi',
            'estimated_value': valuation_result['estimated_value'],
            'confidence_score': valuation_result['confidence_score'],
            'market_trend': valuation_result['market_trend']
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Değerleme güncellenirken hata oluştu: {str(e)}'
        }), 500

@app.route('/api/similar-properties/<int:property_id>')
@login_required
def similar_properties(property_id):
    """Belirli bir mülke benzeyen diğer mülkleri getiren endpoint"""
    try:
        # Mülkü veritabanından al
        property = Property.query.get_or_404(property_id)
        
        # Güvenlik kontrolü
        if property.user_id != current_user.id:
            return jsonify({
                'success': False, 
                'message': 'Bu mülk üzerinde işlem yapmaya yetkiniz yok'
            }), 403
        
        # Filtreleri hazırla - aynı şehir ve ilçedeki mülkler
        # ve metrekare, oda sayısı ve yaş bakımından benzer mülkler
        size_min = max(property.size_sqm * 0.7, 0)  # En az %70'i
        size_max = property.size_sqm * 1.3  # En fazla %130'u
        
        room_min = max(property.room_count - 1, 1)  # En az 1 oda az
        room_max = property.room_count + 1  # En fazla 1 oda fazla
        
        age_min = max(property.building_age - 5, 0)  # En az 5 yaş az
        age_max = property.building_age + 5  # En fazla 5 yaş fazla
        
        # Kullanıcının kendi mülkleri arasından benzer olanları bul
        similar_properties = Property.query.filter(
            Property.user_id == current_user.id,
            Property.id != property_id,  # Kendisi hariç
            Property.city == property.city,
            Property.district == property.district,
            Property.size_sqm.between(size_min, size_max),
            Property.room_count.between(room_min, room_max),
            Property.building_age.between(age_min, age_max)
        ).limit(5).all()
        
        # Sonuçları döndür
        result = []
        for prop in similar_properties:
            # En son değerleme bilgisini al
            latest_valuation = Valuation.query.filter_by(property_id=prop.id).order_by(Valuation.valuation_date.desc()).first()
            estimated_value = latest_valuation.estimated_value if latest_valuation else 0
            
            result.append({
                'id': prop.id,
                'location': f"{prop.neighborhood}",
                'size_sqm': prop.size_sqm,
                'room_count': prop.room_count,
                'building_age': prop.building_age,
                'estimated_value': estimated_value,
                'price_per_sqm': round(estimated_value / prop.size_sqm) if prop.size_sqm else 0
            })
        
        return jsonify({
            'success': True,
            'properties': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Benzer mülkler getirilirken hata oluştu: {str(e)}'
        }), 500

@app.route('/admin/generate-test-data')
def generate_test_data():
    """Sahte emlak verileri oluşturur (yalnızca test amaçlı)"""
    
    # Veri üretilecek şehir ve ilçeler
    locations = [
        ("İstanbul", "Kadıköy"),
        ("İstanbul", "Beşiktaş"),
        ("İstanbul", "Üsküdar"),
        ("Ankara", "Çankaya"),
        ("Ankara", "Yenimahalle"),
        ("İzmir", "Konak"),
        ("İzmir", "Karşıyaka"),
        ("Bursa", "Nilüfer"),
        ("Antalya", "Muratpaşa")
    ]
    
    # Her şehir ve ilçe için ortalama m² fiyatları
    price_ranges = {
        ("İstanbul", "Kadıköy"): (30000, 40000),
        ("İstanbul", "Beşiktaş"): (35000, 45000),
        ("İstanbul", "Üsküdar"): (25000, 35000),
        ("Ankara", "Çankaya"): (12000, 18000),
        ("Ankara", "Yenimahalle"): (8000, 15000),
        ("İzmir", "Konak"): (15000, 25000),
        ("İzmir", "Karşıyaka"): (13000, 22000),
        ("Bursa", "Nilüfer"): (10000, 15000),
        ("Antalya", "Muratpaşa"): (12000, 20000)
    }
    
    # Örnek mahalle isimleri
    neighborhoods = {
        ("İstanbul", "Kadıköy"): ["Caferağa", "Fenerbahçe", "Göztepe", "Koşuyolu", "Moda"],
        ("İstanbul", "Beşiktaş"): ["Levent", "Etiler", "Bebek", "Arnavutköy", "Ortaköy"],
        ("İstanbul", "Üsküdar"): ["Acıbadem", "Altunizade", "Beylerbeyi", "Kuzguncuk", "Kandilli"],
        ("Ankara", "Çankaya"): ["Kavaklıdere", "Çukurambar", "Bahçelievler", "Gaziosmanpaşa", "Ayrancı"],
        ("Ankara", "Yenimahalle"): ["Batıkent", "Demetevler", "İvedik", "Karşıyaka", "Şentepe"],
        ("İzmir", "Konak"): ["Alsancak", "Göztepe", "Hatay", "Güzelyalı", "Karantina"],
        ("İzmir", "Karşıyaka"): ["Bostanlı", "Atakent", "Donanmacı", "Alaybey", "Tersane"],
        ("Bursa", "Nilüfer"): ["Fethiye", "İhsaniye", "Karaman", "Beşevler", "Altınşehir"],
        ("Antalya", "Muratpaşa"): ["Konyaaltı", "Lara", "Meltem", "Şirinyalı", "Fener"]
    }
    
    num_records = 500  # Oluşturulacak kayıt sayısı
    created_count = 0
    
    try:
        # Veritabanındaki mevcut veri sayısı
        existing_count = ScrapedListing.query.count()
        
        # Mevcut veri varsa, işlemi iptal et
        if existing_count > 100:
            return jsonify({
                'success': False, 
                'message': f'Veritabanında zaten {existing_count} kayıt var. Veriler zaten yeterli.'
            })
            
        # Sahte veriler oluştur
        for _ in range(num_records):
            # Rastgele bir şehir ve ilçe seç
            city, district = random.choice(locations)
            
            # Temel parametreler
            neighborhood = random.choice(neighborhoods.get((city, district), ["Merkez"]))
            size_sqm = random.randint(70, 200)
            room_count = random.randint(1, 5)  # 1+0'dan 4+1'e kadar
            building_age = random.randint(0, 30)
            floor_number = random.randint(-1, 15)
            
            # Fiyat hesaplama
            base_price_sqm = random.randint(*price_ranges.get((city, district), (10000, 15000)))
            
            # Faktörler
            size_factor = 1.0 + (size_sqm - 100) * 0.001  # Daha büyük daireler biraz daha pahalı
            room_factor = 1.0 + (room_count - 2) * 0.05  # Oda sayısı arttıkça fiyat artar
            age_factor = 1.0 - min(0.3, building_age * 0.01)  # En fazla %30 yaştan dolayı indirim
            floor_factor = 1.0 + (floor_number * 0.01)  # Üst katlar biraz daha değerli
            
            # Toplam fiyat hesabı (rastgele fark ekleyerek)
            price = round(size_sqm * base_price_sqm * size_factor * room_factor * age_factor * floor_factor)
            price += random.randint(-price // 10, price // 10)  # ±%10 rastgele değişim
            
            # Tarihleri rastgele belirle (son 6 ay içinde)
            days_ago = random.randint(1, 180)  # Son 6 ay
            scrape_date = datetime.utcnow() - timedelta(days=days_ago)
            
            # Veri oluştur ve ekle
            listing = ScrapedListing(
                city=city,
                district=district,
                neighborhood=neighborhood,
                property_type="Daire",
                price=price,
                size_sqm=size_sqm,
                room_count=room_count,
                building_age=building_age,
                floor_number=floor_number,
                scrape_date=scrape_date
            )
            
            db.session.add(listing)
            created_count += 1
            
            # Her 100 kayıtta bir commit yaparak bellek kullanımını optimize et
            if created_count % 100 == 0:
                db.session.commit()
        
        # Kalan kayıtları da kaydet
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'{created_count} adet sahte emlak ilanı başarıyla oluşturuldu',
            'total_records': created_count + existing_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': f'Hata oluştu: {str(e)}'
        })

# Market Metrics API Routes

@app.route('/api/metrics/sqm-price')
def get_sqm_price_metrics():
    """Bölgelere göre metrekare fiyat karşılaştırması"""
    districts = ["Kadıköy", "Beşiktaş", "Üsküdar", "Şişli", "Maltepe", "Ataşehir"]
    
    # Gerçek hayatta bu veriler veritabanından dinamik olarak gelir
    values = [32000, 28500, 22000, 25000, 19000, 21000]
    
    return jsonify({
        'districts': districts,
        'values': values
    })

@app.route('/api/metrics/market-time')
def get_market_time():
    """Bölgelere göre ortalama satışta kalma süresi"""
    districts = ["Kadıköy", "Beşiktaş", "Üsküdar", "Şişli", "Maltepe", "Ataşehir"]
    
    # Gün cinsinden ortalama pazarda kalma süresi
    values = [45, 40, 65, 55, 80, 60]
    
    return jsonify({
        'districts': districts,
        'values': values
    })

@app.route('/api/metrics/annual-return')
def get_annual_return():
    """Bölgelere göre yıllık getiri oranı"""
    districts = ["Kadıköy", "Beşiktaş", "Üsküdar", "Şişli", "Maltepe", "Ataşehir"]
    
    # Yüzde cinsinden yıllık getiri oranı
    values = [12.5, 11.8, 9.2, 10.5, 8.7, 9.8]
    
    return jsonify({
        'districts': districts,
        'values': values
    })

@app.route('/api/metrics/price-rent-ratio')
def get_price_rent_ratio():
    """Bölgelere göre fiyat/kira oranı"""
    districts = ["Kadıköy", "Beşiktaş", "Üsküdar", "Şişli", "Maltepe", "Ataşehir"]
    
    # Fiyat/kira oranı (kaç yılda kendini amorti ediyor)
    values = [24, 23, 19, 21, 17, 18]
    
    return jsonify({
        'districts': districts,
        'values': values
    })

# Portfolio Distribution API Routes

@app.route('/api/portfolio/property-types')
def get_property_types():
    """Portföydeki gayrimenkul tipleri dağılımı"""
    # Örnek veri - gerçek uygulamada veritabanından çekilir
    types = ["Daire", "Villa", "Müstakil Ev", "İş Yeri", "Arsa"]
    counts = [65, 15, 8, 10, 2]
    
    return jsonify({
        'types': types,
        'counts': counts
    })

@app.route('/api/portfolio/room-counts')
def get_room_counts():
    """Portföydeki oda sayısı dağılımı"""
    # Örnek veri - gerçek uygulamada veritabanından çekilir
    counts = ["1+0", "1+1", "2+1", "3+1", "4+1 ve üzeri"]
    properties = [5, 20, 40, 25, 10]
    
    return jsonify({
        'counts': counts,
        'properties': properties
    })

@app.route('/api/portfolio/building-ages')
def get_building_ages():
    """Portföydeki bina yaşı dağılımı"""
    # Örnek veri - gerçek uygulamada veritabanından çekilir
    ranges = ["0-5 yıl", "6-10 yıl", "11-15 yıl", "16-20 yıl", "20+ yıl"]
    counts = [30, 25, 20, 15, 10]
    
    return jsonify({
        'ranges': ranges,
        'counts': counts
    })

@app.route('/api/portfolio/size-ranges')
def get_size_ranges():
    """Portföydeki metrekare aralığı dağılımı"""
    # Örnek veri - gerçek uygulamada veritabanından çekilir
    ranges = ["0-75 m²", "76-100 m²", "101-150 m²", "151-200 m²", "200+ m²"]
    counts = [15, 35, 30, 15, 5]
    
    return jsonify({
        'ranges': ranges,
        'counts': counts
    })

@app.route('/api/comparative-price-trends')
def get_comparative_price_trends():
    """Bölgeye özel karşılaştırmalı performans grafiği için veri"""
    # Zaman eksenini oluştur (son 6 ay)
    today = datetime.now()
    months = []
    for i in range(5, -1, -1):
        date = today - timedelta(days=30*i)
        months.append(date.strftime('%Y-%m'))
    
    # Şehirler ve bölgeler
    selected_district = request.args.get('district', 'Kadıköy')
    selected_city = request.args.get('city', 'İstanbul')
    
    # Fiyat endeksi (100 = 6 ay önceki değer)
    # Her şehir ve bölge için farklı trend belirle
    district_trends = {
        'Kadıköy': [100, 102, 104, 107, 110, 113],
        'Beşiktaş': [100, 103, 105, 108, 111, 115],
        'Üsküdar': [100, 101, 102, 104, 105, 107],
        'Şişli': [100, 104, 106, 107, 109, 112],
        'Maltepe': [100, 101, 103, 105, 106, 108],
        'Ataşehir': [100, 102, 103, 106, 107, 110],
        'Yenimahalle': [100, 101, 102, 104, 105, 106],
        'Çankaya': [100, 102, 104, 106, 108, 110],
    }
    
    city_trends = {
        'İstanbul': [100, 102, 104, 106, 108, 110],
        'Ankara': [100, 101, 102, 103, 104, 105],
        'İzmir': [100, 103, 105, 107, 108, 110]
    }
    
    # Ulusal trend ve enflasyon
    national_trend = [100, 102, 103, 105, 107, 109]
    inflation = [100, 103, 106, 110, 113, 117]
    
    # Seçilen bölge için veriyi belirle
    district_data = district_trends.get(selected_district, district_trends['Kadıköy'])
    city_data = city_trends.get(selected_city, city_trends['İstanbul'])
    
    return jsonify({
        'months': months,
        'district': {
            'name': selected_district,
            'values': district_data,
            'change': round((district_data[-1] - 100), 1)  # Son 6 aydaki % değişim
        },
        'city': {
            'name': selected_city, 
            'values': city_data,
            'change': round((city_data[-1] - 100), 1)
        },
        'national': {
            'name': 'Ulusal Ortalama',
            'values': national_trend,
            'change': round((national_trend[-1] - 100), 1)
        },
        'inflation': {
            'name': 'Enflasyon',
            'values': inflation,
            'change': round((inflation[-1] - 100), 1)
        }
    })

if __name__ == '__main__':
    app.run(debug=True) 