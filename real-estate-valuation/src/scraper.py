import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from models import db, ScrapedListing

class SahibindenScraper:
    def __init__(self):
        self.base_url = "https://www.sahibinden.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        return webdriver.Chrome(options=options)
    
    def parse_listing_details(self, url):
        """Parse individual listing details"""
        try:
            driver = self.setup_driver()
            driver.get(url)
            time.sleep(2)  # Allow JavaScript to load
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract basic information
            price = self._extract_price(soup)
            details = self._extract_property_details(soup)
            
            listing = ScrapedListing(
                listing_id=url.split('/')[-1],
                url=url,
                price=price,
                city=details.get('city', ''),
                district=details.get('district', ''),
                neighborhood=details.get('neighborhood', ''),
                property_type=details.get('property_type', ''),
                size_sqm=details.get('size_sqm', 0),
                room_count=details.get('room_count', 0),
                building_age=details.get('building_age', 0),
                floor_number=details.get('floor_number', 0)
            )
            
            return listing
            
        except Exception as e:
            print(f"Error parsing listing {url}: {str(e)}")
            return None
        finally:
            driver.quit()
    
    def _extract_price(self, soup):
        """Extract price from the listing"""
        try:
            price_element = soup.find('div', {'class': 'classifiedInfo'}).find('h3')
            price_text = price_element.text.strip()
            # Convert price text to float (remove currency and dots)
            price = float(price_text.replace('TL', '').replace('.', '').strip())
            return price
        except:
            return 0
    
    def _extract_property_details(self, soup):
        """Extract property details from the listing"""
        details = {}
        try:
            info_list = soup.find('div', {'class': 'classifiedInfo'}).find_all('li')
            
            for item in info_list:
                label = item.find('strong')
                value = item.find('span')
                
                if label and value:
                    label_text = label.text.strip().lower()
                    value_text = value.text.strip()
                    
                    if 'metrekare' in label_text:
                        details['size_sqm'] = float(value_text.replace('m²', '').strip())
                    elif 'oda sayısı' in label_text:
                        details['room_count'] = int(value_text.split('+')[0])
                    elif 'bina yaşı' in label_text:
                        details['building_age'] = int(value_text.split()[0])
                    elif 'bulunduğu kat' in label_text:
                        details['floor_number'] = self._parse_floor_number(value_text)
            
            # Extract location information
            location = soup.find('div', {'class': 'classifiedInfo'}).find('h2').text.strip()
            location_parts = location.split('/')
            if len(location_parts) >= 3:
                details['city'] = location_parts[-3].strip()
                details['district'] = location_parts[-2].strip()
                details['neighborhood'] = location_parts[-1].strip()
            
        except Exception as e:
            print(f"Error extracting details: {str(e)}")
        
        return details
    
    def _parse_floor_number(self, floor_text):
        """Convert floor text to number"""
        try:
            if 'zemin' in floor_text.lower():
                return 0
            elif 'bodrum' in floor_text.lower():
                return -1
            elif 'giriş' in floor_text.lower():
                return 0
            else:
                return int(floor_text.split('.')[0])
        except:
            return 0
    
    def scrape_listings(self, city, district=None, property_type="konut", page_limit=10):
        """Scrape multiple listings from search results"""
        listings = []
        
        try:
            driver = self.setup_driver()
            
            # Construct search URL
            search_url = f"{self.base_url}/satilik-{property_type}/{city}"
            if district:
                search_url += f"/{district}"
            
            for page in range(1, page_limit + 1):
                page_url = f"{search_url}?pagingOffset={(page-1)*20}"
                driver.get(page_url)
                time.sleep(2)
                
                # Extract listing URLs
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                listing_elements = soup.find_all('td', {'class': 'searchResultsLargeThumbnail'})
                
                for element in listing_elements:
                    link = element.find('a')
                    if link and 'href' in link.attrs:
                        listing_url = self.base_url + link['href']
                        listing = self.parse_listing_details(listing_url)
                        if listing:
                            listings.append(listing)
                
                print(f"Completed page {page}/{page_limit}")
                
            return listings
            
        except Exception as e:
            print(f"Error in scraping listings: {str(e)}")
            return listings
        finally:
            driver.quit()

    def save_listings_to_db(self, listings):
        """Save scraped listings to database"""
        try:
            for listing in listings:
                existing = ScrapedListing.query.filter_by(listing_id=listing.listing_id).first()
                if existing:
                    existing.is_active = True
                    existing.price = listing.price
                    existing.scrape_date = datetime.utcnow()
                else:
                    db.session.add(listing)
            
            db.session.commit()
            print(f"Successfully saved {len(listings)} listings to database")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving listings to database: {str(e)}") 