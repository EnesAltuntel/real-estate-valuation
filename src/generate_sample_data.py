"""
Gayrimenkul değerleme modeli için örnek/sahte veri üreten script
"""
import random
from datetime import datetime, timedelta
from app import app
from models import db, ScrapedListing

# Veri üretilecek şehir ve ilçeler
LOCATIONS = [
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
PRICE_RANGES = {
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

# Oluşturulacak örnek mahalleler
NEIGHBORHOODS = {
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

def generate_fake_listing(city, district):
    """Sahte bir emlak ilanı üretir"""
    # Temel parametreler
    neighborhood = random.choice(NEIGHBORHOODS.get((city, district), ["Merkez"]))
    size_sqm = random.randint(70, 200)
    room_count = random.randint(1, 5)  # 1+0'dan 4+1'e kadar
    building_age = random.randint(0, 30)
    floor_number = random.randint(-1, 15)
    
    # Fiyat hesaplama
    base_price_sqm = random.randint(*PRICE_RANGES.get((city, district), (10000, 15000)))
    
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
    
    # Veri oluştur
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
    
    return listing

def generate_sample_data(num_records=500):
    """Belirtilen sayıda örnek veri üretir ve veritabanına kaydeder"""
    print(f"{num_records} adet sahte emlak ilanı üretiliyor...")
    
    listings = []
    for _ in range(num_records):
        # Rastgele bir şehir ve ilçe seç
        city, district = random.choice(LOCATIONS)
        # Sahte ilan oluştur
        listing = generate_fake_listing(city, district)
        listings.append(listing)
    
    # Veritabanına kaydet
    db.session.add_all(listings)
    db.session.commit()
    
    print(f"{num_records} adet sahte emlak ilanı başarıyla veritabanına eklendi")
    return listings

if __name__ == "__main__":
    with app.app_context():
        generate_sample_data(500)  # 500 sahte ilan üret 