from scraper import EmlakjetScraper, HurriyetEmlakScraper
from models import db
from app import app

def main():
    print("*" * 50)
    print("Emlak Veri Toplama Aracı")
    print("*" * 50)
    
    try:
        # Flask uygulama bağlamı oluştur
        with app.app_context():
            # Emlakjet.com'dan veri topla
            print("\n[1/2] Emlakjet.com'dan veri çekiliyor...")
            emlakjet_scraper = EmlakjetScraper()
            emlakjet_listings = emlakjet_scraper.scrape_multiple_locations()
            print(f"Emlakjet'ten toplam {len(emlakjet_listings)} ilan toplandı")
            emlakjet_scraper.close_driver()
            
            # Hurriyetemlak.com'dan veri topla
            print("\n[2/2] Hürriyet Emlak'tan veri çekiliyor...")
            hurriyet_scraper = HurriyetEmlakScraper()
            hurriyet_listings = hurriyet_scraper.scrape_multiple_locations()
            print(f"Hürriyet Emlak'tan toplam {len(hurriyet_listings)} ilan toplandı")
            hurriyet_scraper.close_driver()
            
            # Toplam sonuçları raporla
            total_listings = len(emlakjet_listings) + len(hurriyet_listings)
            print("\n" + "=" * 50)
            print(f"Toplam {total_listings} ilan başarıyla veritabanına kaydedildi")
            print("=" * 50)
        
    except Exception as e:
        print(f"Veri toplama sırasında hata oluştu: {str(e)}")
        
if __name__ == "__main__":
    main() 