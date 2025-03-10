from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime
from models import db, ScrapedListing

class BaseScraper:
    """Temel scraper sınıfı, ortak metodları içerir"""
    
    def __init__(self):
        self.setup_driver()
    
    def setup_driver(self):
        """WebDriver'ı ayarla ve başlat"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def close_driver(self):
        """WebDriver'ı kapat"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def save_listings_to_db(self, listings):
        """Çekilen ilanları veritabanına kaydet"""
        try:
            db.session.add_all(listings)
            db.session.commit()
            print(f"Kayıt başarılı: {len(listings)} ilan veritabanına eklendi")
        except Exception as e:
            db.session.rollback()
            print(f"Veritabanı hatası: {str(e)}")


class EmlakjetScraper(BaseScraper):
    """Emlakjet.com üzerinden emlak ilanlarını çeker"""
    
    def scrape_listings(self, city, district, page_limit=3):
        """Belirli bir şehir ve ilçe için emlak ilanlarını çek"""
        listings = []
        
        for page in range(1, page_limit + 1):
            # URL'yi oluştur - emlakjet.com formatına göre
            url = f"https://www.emlakjet.com/satilik-konut/{city.lower()}-{district.lower()}/?page={page}"
            
            try:
                self.driver.get(url)
                time.sleep(random.uniform(2, 4))  # Random bekleme süresi
                
                # Sayfa içeriğini parse et
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # İlan kartlarını bul - emlakjet.com'un HTML yapısına göre
                listing_cards = soup.select('.ej-listing-card')
                
                if not listing_cards:
                    print(f"İlan bulunamadı: {city}-{district}, sayfa {page}")
                    continue
                
                print(f"Bulunan ilan sayısı: {len(listing_cards)}")
                
                for card in listing_cards:
                    try:
                        # Fiyat bilgisini çek
                        price_element = card.select_one('.ej-listing-card__price')
                        if not price_element:
                            continue
                            
                        price_text = price_element.text.strip()
                        price = int(''.join(filter(str.isdigit, price_text)))
                        
                        # Özellikler alanını bul
                        details_elements = card.select('.ej-listing-card__info')
                        
                        # Metrekare bilgisini çek
                        size_element = next((el for el in details_elements if "m²" in el.text), None)
                        size_sqm = 0
                        if size_element:
                            size_text = size_element.text.strip()
                            size_sqm = int(''.join(filter(str.isdigit, size_text)))
                        
                        # Oda sayısını çek
                        room_element = next((el for el in details_elements if "+" in el.text), None)
                        room_count = 2  # Varsayılan olarak 2+1
                        if room_element:
                            room_text = room_element.text.strip()
                            parts = room_text.split('+')
                            if len(parts) > 0 and parts[0].isdigit():
                                room_count = int(parts[0]) + 1
                        
                        # Bina yaşı için (tam bilgi olmayabilir)
                        building_age = 5  # Varsayılan olarak 5 yıl
                        age_element = next((el for el in details_elements if "yaşında" in el.text.lower()), None)
                        if age_element:
                            age_text = age_element.text.strip()
                            age_digits = ''.join(filter(str.isdigit, age_text))
                            if age_digits:
                                building_age = int(age_digits)
                        
                        # Kat bilgisi
                        floor_number = 1  # Varsayılan olarak 1. kat
                        floor_element = next((el for el in details_elements if "kat" in el.text.lower()), None)
                        if floor_element:
                            floor_text = floor_element.text.strip().lower()
                            if "giriş" in floor_text or "zemin" in floor_text:
                                floor_number = 0
                            elif "bodrum" in floor_text:
                                floor_number = -1
                            else:
                                floor_digits = ''.join(filter(str.isdigit, floor_text))
                                if floor_digits:
                                    floor_number = int(floor_digits)
                        
                        # Neighborhood tespiti
                        neighborhood = ""
                        location_element = card.select_one('.ej-listing-card__location')
                        if location_element:
                            location_parts = location_element.text.strip().split(',')
                            if len(location_parts) > 2:
                                neighborhood = location_parts[0].strip()
                        
                        # Veritabanına kaydet
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
                            scrape_date=datetime.utcnow()
                        )
                        
                        listings.append(listing)
                        
                    except Exception as e:
                        print(f"İlan ayrıştırma hatası: {str(e)}")
                        continue
                
                # Her sayfadan sonra rastgele bekle
                time.sleep(random.uniform(3, 6))
                
            except Exception as e:
                print(f"Sayfa çekme hatası ({page}): {str(e)}")
                continue
        
        # Tüm ilanları kaydet
        self.save_listings_to_db(listings)
        return listings
    
    def scrape_multiple_locations(self):
        """Birden fazla lokasyon için scraping işlemini yap"""
        locations = [
            ("istanbul", "kadikoy"),
            ("istanbul", "besiktas"),
            ("istanbul", "uskudar"),
            ("ankara", "cankaya"),
            ("ankara", "yenimahalle"),
            ("izmir", "konak"),
            ("izmir", "karsiyaka"),
            ("bursa", "nilufer"),
            ("antalya", "muratpasa")
        ]
        
        all_listings = []
        for city, district in locations:
            print(f"Emlakjet - {city.capitalize()} - {district.capitalize()} için veri çekiliyor...")
            listings = self.scrape_listings(city, district, page_limit=2)
            all_listings.extend(listings)
            time.sleep(random.uniform(5, 10))  # Lokasyonlar arası bekleme
        
        return all_listings


class HurriyetEmlakScraper(BaseScraper):
    """Hurriyetemlak.com üzerinden emlak ilanlarını çeker"""
    
    def scrape_listings(self, city, district, page_limit=3):
        """Belirli bir şehir ve ilçe için emlak ilanlarını çek"""
        listings = []
        
        for page in range(1, page_limit + 1):
            # URL'yi oluştur - hurriyetemlak.com formatına göre
            url = f"https://www.hurriyetemlak.com/{city.lower()}-{district.lower()}-satilik?page={page}"
            
            try:
                self.driver.get(url)
                time.sleep(random.uniform(2, 4))  # Random bekleme süresi
                
                # Sayfa içeriğini parse et
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # İlan kartlarını bul
                listing_cards = soup.select('.list-view-content')
                
                if not listing_cards:
                    print(f"İlan bulunamadı: {city}-{district}, sayfa {page}")
                    continue
                
                print(f"Bulunan ilan sayısı: {len(listing_cards)}")
                
                for card in listing_cards:
                    try:
                        # Fiyat bilgisini çek
                        price_element = card.select_one('.list-view-price')
                        if not price_element:
                            continue
                            
                        price_text = price_element.text.strip()
                        price = int(''.join(filter(str.isdigit, price_text)))
                        
                        # Özellikler alanını bul
                        details_elements = card.select('.list-view-features li')
                        
                        # Metrekare bilgisi
                        size_sqm = 0
                        size_element = next((el for el in details_elements if "m²" in el.text), None)
                        if size_element:
                            size_text = size_element.text.strip()
                            size_sqm = int(''.join(filter(str.isdigit, size_text)))
                        
                        # Oda sayısı
                        room_count = 2  # Varsayılan olarak 2+1
                        room_element = next((el for el in details_elements if "+" in el.text or "Oda" in el.text), None)
                        if room_element:
                            room_text = room_element.text.strip()
                            if "+" in room_text:
                                parts = room_text.split('+')
                                if len(parts) > 0 and parts[0].isdigit():
                                    room_count = int(parts[0]) + 1
                            else:
                                room_digits = ''.join(filter(str.isdigit, room_text))
                                if room_digits:
                                    room_count = int(room_digits)
                        
                        # Bina yaşı (tam bilgi olmayabilir)
                        building_age = 5  # Varsayılan olarak 5 yıl
                        age_element = next((el for el in details_elements if "yaş" in el.text.lower()), None)
                        if age_element:
                            age_text = age_element.text.strip()
                            age_digits = ''.join(filter(str.isdigit, age_text))
                            if age_digits:
                                building_age = int(age_digits)
                        
                        # Kat bilgisi
                        floor_number = 1  # Varsayılan olarak 1. kat
                        floor_element = next((el for el in details_elements if "kat" in el.text.lower()), None)
                        if floor_element:
                            floor_text = floor_element.text.strip().lower()
                            if "giriş" in floor_text or "zemin" in floor_text:
                                floor_number = 0
                            elif "bodrum" in floor_text:
                                floor_number = -1
                            else:
                                floor_digits = ''.join(filter(str.isdigit, floor_text))
                                if floor_digits:
                                    floor_number = int(floor_digits)
                        
                        # Mahalle bilgisi
                        neighborhood = ""
                        location_element = card.select_one('.list-view-location')
                        if location_element:
                            location_text = location_element.text.strip()
                            location_parts = location_text.split('/')
                            if len(location_parts) > 0:
                                neighborhood = location_parts[0].strip()
                        
                        # Veritabanına kaydet
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
                            scrape_date=datetime.utcnow()
                        )
                        
                        listings.append(listing)
                        
                    except Exception as e:
                        print(f"İlan ayrıştırma hatası: {str(e)}")
                        continue
                
                # Her sayfadan sonra rastgele bekle
                time.sleep(random.uniform(3, 6))
                
            except Exception as e:
                print(f"Sayfa çekme hatası ({page}): {str(e)}")
                continue
        
        # Tüm ilanları kaydet
        self.save_listings_to_db(listings)
        return listings
    
    def scrape_multiple_locations(self):
        """Birden fazla lokasyon için scraping işlemini yap"""
        locations = [
            ("istanbul", "kadikoy"),
            ("istanbul", "besiktas"),
            ("istanbul", "uskudar"),
            ("ankara", "cankaya"),
            ("ankara", "yenimahalle"),
            ("izmir", "konak"),
            ("izmir", "karsiyaka"),
            ("bursa", "nilufer"),
            ("antalya", "muratpasa")
        ]
        
        all_listings = []
        for city, district in locations:
            print(f"Hürriyet Emlak - {city.capitalize()} - {district.capitalize()} için veri çekiliyor...")
            listings = self.scrape_listings(city, district, page_limit=2)
            all_listings.extend(listings)
            time.sleep(random.uniform(5, 10))  # Lokasyonlar arası bekleme
        
        return all_listings


# Legacy Sahibinden.com scraper için eski sınıfı koruyalım
class SahibindenScraper(BaseScraper):
    def scrape_listings(self, city, district, page_limit=3):
        """Belirli bir şehir ve ilçe için emlak ilanlarını çek"""
        listings = []
        
        for page in range(1, page_limit + 1):
            # URL'yi oluştur
            url = f"https://www.sahibinden.com/satilik-daire/{city.lower()}-{district.lower()}?pagingOffset={(page-1)*20}"
            
            try:
                self.driver.get(url)
                time.sleep(random.uniform(2, 4))  # Random bekleme süresi
                
                # CAPTCHA veya popup kontrolü
                if "doğrulama" in self.driver.page_source.lower():
                    print(f"CAPTCHA detected for {city}-{district}, page {page}")
                    continue
                
                # Sayfa içeriğini parse et
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # İlan kartlarını bul
                listing_cards = soup.find_all('tr', class_='searchResultsItem')
                
                for card in listing_cards:
                    try:
                        # Temel bilgileri çek
                        price_text = card.find('td', class_='searchResultsPriceValue').text.strip()
                        price = int(''.join(filter(str.isdigit, price_text)))
                        
                        details = card.find_all('td', class_='searchResultsAttributeValue')
                        
                        # Metrekare bilgisini çek
                        size_text = details[0].text.strip()
                        size_sqm = int(''.join(filter(str.isdigit, size_text)))
                        
                        # Oda sayısını çek
                        room_text = details[1].text.strip()
                        room_count = int(room_text[0]) if room_text[0].isdigit() else 1
                        
                        # Bina yaşını çek
                        age_text = details[2].text.strip()
                        building_age = 0 if 'sıfır' in age_text.lower() else int(''.join(filter(str.isdigit, age_text))) if any(c.isdigit() for c in age_text) else 20
                        
                        # Kat bilgisini çek
                        floor_text = details[3].text.strip()
                        floor_number = 1
                        if floor_text.isdigit():
                            floor_number = int(floor_text)
                        elif 'giriş' in floor_text.lower():
                            floor_number = 0
                        elif 'bodrum' in floor_text.lower():
                            floor_number = -1
                        
                        # Veritabanına kaydet
                        listing = ScrapedListing(
                            city=city,
                            district=district,
                            neighborhood="",  # Mahalle bilgisi daha sonra eklenebilir
                            property_type="Daire",
                            price=price,
                            size_sqm=size_sqm,
                            room_count=room_count,
                            building_age=building_age,
                            floor_number=floor_number,
                            scrape_date=datetime.utcnow()
                        )
                        
                        listings.append(listing)
                        
                    except Exception as e:
                        print(f"Error parsing listing: {str(e)}")
                        continue
                
                # Her sayfadan sonra rastgele bekle
                time.sleep(random.uniform(3, 6))
                
            except Exception as e:
                print(f"Error scraping page {page}: {str(e)}")
                continue
        
        # Tüm ilanları kaydet
        self.save_listings_to_db(listings)
        return listings
    
    def scrape_multiple_locations(self):
        """Birden fazla lokasyon için scraping işlemini yap"""
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
        
        all_listings = []
        for city, district in locations:
            print(f"Scraping {city} - {district}...")
            listings = self.scrape_listings(city, district)
            all_listings.extend(listings)
            time.sleep(random.uniform(5, 10))  # Lokasyonlar arası bekleme
        
        return all_listings 