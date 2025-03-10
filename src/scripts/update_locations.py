import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, City, District, Neighborhood
from app import app

def populate_locations():
    """Veritabanını Türkiye'nin şehir, ilçe ve mahalle verileriyle doldur"""
    with app.app_context():
        # Önce tüm mevcut verileri temizle
        Neighborhood.query.delete()
        District.query.delete()
        City.query.delete()
        
        # Şehirleri ekle (81 il)
        cities = {
            "İstanbul": [
                ("Kadıköy", ["Caferağa", "Fenerbahçe", "Göztepe", "Kozyatağı", "Suadiye", "Erenköy"]),
                ("Beşiktaş", ["Levent", "Etiler", "Bebek", "Arnavutköy", "Ortaköy", "Ulus"]),
                ("Üsküdar", ["Acıbadem", "Altunizade", "Beylerbeyi", "Çengelköy", "Kuzguncuk"]),
                ("Şişli", ["Nişantaşı", "Teşvikiye", "Harbiye", "Mecidiyeköy"]),
                ("Bakırköy", ["Ataköy", "Yeşilköy", "Florya", "Bahçelievler"])
            ],
            "Ankara": [
                ("Çankaya", ["Bahçelievler", "Çayyolu", "Oran", "Gaziosmanpaşa", "Kızılay"]),
                ("Yenimahalle", ["Batıkent", "Demetevler", "Karşıyaka", "Ostim", "Şentepe"]),
                ("Keçiören", ["Aktepe", "Esertepe", "Etlik", "Kalaba", "Ovacık"]),
                ("Mamak", ["Abidinpaşa", "Boğaziçi", "Derbent", "Kayaş"]),
                ("Altındağ", ["Anafartalar", "Ulus", "Samanpazarı", "Hamamönü"])
            ],
            "İzmir": [
                ("Konak", ["Alsancak", "Göztepe", "Güzelyalı", "Karataş", "Hatay"]),
                ("Karşıyaka", ["Bostanlı", "Mavişehir", "Atakent", "Çarşı", "Alaybey"]),
                ("Bornova", ["Evka", "Özkanlar", "Kazımdirik", "Erzene", "Küçükpark"]),
                ("Buca", ["Şirinyer", "Yıldız", "Çamlıkule", "Adatepe"]),
                ("Çiğli", ["Ataşehir", "Balatçık", "Egekent", "Küçükçiğli"])
            ],
            "Bursa": [
                ("Nilüfer", ["Görükle", "Özlüce", "İhsaniye", "Karaman"]),
                ("Osmangazi", ["Çekirge", "Demirtaş", "Hamitler", "Hüdavendigar"]),
                ("Yıldırım", ["Beyazıt", "Millet", "Yavuz Selim", "Yeşilyayla"])
            ],
            "Antalya": [
                ("Muratpaşa", ["Lara", "Konyaaltı", "Meltem", "Fener"]),
                ("Kepez", ["Varsak", "Göksu", "Teomanpaşa", "Özgürlük"]),
                ("Konyaaltı", ["Liman", "Hurma", "Sarısu", "Uncalı"])
            ]
        }

        # Verileri veritabanına ekle
        for city_name, districts in cities.items():
            city = City(name=city_name)
            db.session.add(city)
            db.session.flush()  # ID'yi al
            
            for district_name, neighborhoods in districts:
                district = District(name=district_name, city_id=city.id)
                db.session.add(district)
                db.session.flush()  # ID'yi al
                
                for neighborhood_name in neighborhoods:
                    neighborhood = Neighborhood(name=neighborhood_name, district_id=district.id)
                    db.session.add(neighborhood)
            
            print(f"{city_name} ve ilçeleri eklendi.")
        
        db.session.commit()
        print("Tüm lokasyon verileri başarıyla eklendi!")

if __name__ == "__main__":
    populate_locations() 