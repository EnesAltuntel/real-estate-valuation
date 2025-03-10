import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from datetime import datetime, timedelta, timezone
from models import db, ScrapedListing, Valuation
import random

# İstanbul saati için zaman dilimi (UTC+3)
ISTANBUL_TIMEZONE = timezone(timedelta(hours=3))

class PropertyValuator:
    def __init__(self):
        self.model = None
        self.preprocessor = None
        self.feature_columns = [
            'city', 'district', 'neighborhood',
            'property_type', 'size_sqm', 'room_count',
            'building_age', 'floor_number'
        ]
        # Basit tahmin için ortalama m² fiyatları
        self.default_sqm_prices = {
            'İstanbul': {
                'Kadıköy': 35000,
                'Beşiktaş': 40000,
                'Üsküdar': 30000,
                'Şişli': 35000,
                'Bakırköy': 32000,
                # Mahalle bazlı fiyatlar
                'mahalleler': {
                    'Kadıköy': {
                        'Caferağa': 74000,
                        'Erenköy': 125000,
                        'Fenerbahçe': 176000,
                        'Göztepe': 132000,
                        'Kozyatağı': 106000,
                        'Suadiye': 150000
                    },
                    'Üsküdar': {
                        'Acıbadem': 115570,
                        'Altunizade': 130000,
                        'Beylerbeyi': 84000,
                        'Kuzguncuk': 102000,
                        'Çengelköy': 83000
                    }
                }
            },
            'Ankara': {
                'Çankaya': 15000,
                'Yenimahalle': 12000,
                'Keçiören': 10000,
                'Mamak': 8000,
                'Altındağ': 9000
            },
            'İzmir': {
                'Konak': 18000,
                'Karşıyaka': 16000,
                'Bornova': 14000,
                'Buca': 12000,
                'Çiğli': 13000
            },
            'Bursa': {
                'Nilüfer': 12000,
                'Osmangazi': 10000,
                'Yıldırım': 8000
            },
            'Antalya': {
                'Muratpaşa': 15000,
                'Kepez': 10000,
                'Konyaaltı': 14000
            }
        }
    
    def prepare_data(self):
        """Prepare data for training"""
        # Get listings from last 6 months
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        listings = ScrapedListing.query.filter(
            ScrapedListing.scrape_date >= six_months_ago
        ).all()
        
        data = []
        for listing in listings:
            data.append({
                'price': listing.price,
                'city': listing.city,
                'district': listing.district,
                'neighborhood': listing.neighborhood,
                'property_type': listing.property_type,
                'size_sqm': listing.size_sqm,
                'room_count': listing.room_count,
                'building_age': listing.building_age,
                'floor_number': listing.floor_number
            })
        
        return pd.DataFrame(data)
    
    def train_model(self):
        """Train the valuation model"""
        df = self.prepare_data()
        
        if len(df) < 10:  # Yeterli veri yoksa
            print("Not enough data to train the model")
            return None, None
        
        # Separate features and target
        X = df[self.feature_columns]
        y = df['price']
        
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Create preprocessing steps
        numeric_features = ['size_sqm', 'room_count', 'building_age', 'floor_number']
        categorical_features = ['city', 'district', 'neighborhood', 'property_type']
        
        numeric_transformer = Pipeline(steps=[
            ('scaler', StandardScaler())
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('onehot', OneHotEncoder(handle_unknown='ignore'))
        ])
        
        # Combine preprocessing steps
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features),
                ('cat', categorical_transformer, categorical_features)
            ])
        
        # Create a pipeline with preprocessor and model
        self.model = Pipeline(steps=[
            ('preprocessor', self.preprocessor),
            ('regressor', RandomForestRegressor(
                n_estimators=100,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            ))
        ])
        
        # Fit the pipeline
        self.model.fit(X_train, y_train)
        
        # Evaluate the model
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"Model Performance:")
        print(f"Mean Squared Error: {mse:,.2f}")
        print(f"R² Score: {r2:.4f}")
        
        return mse, r2
    
    def estimate_value(self, property_data):
        """Estimate property value using trained model or simple heuristics"""
        try:
            if not self.model:
                mse, r2 = self.train_model()
            
            if self.model:
                # Model varsa, modeli kullan
                input_df = pd.DataFrame([property_data])
                estimated_value = self.model.predict(input_df)[0]
            else:
                # Model yoksa, basit tahmin yap
                city = property_data['city']
                district = property_data['district']
                neighborhood = property_data['neighborhood']
                size_sqm = property_data['size_sqm']
                
                # Mahalle bazlı fiyat kontrolü
                price_per_sqm = None
                if (city in self.default_sqm_prices and 
                    'mahalleler' in self.default_sqm_prices[city] and 
                    district in self.default_sqm_prices[city]['mahalleler'] and
                    neighborhood in self.default_sqm_prices[city]['mahalleler'][district]):
                    # Mahalle bazlı fiyat mevcut
                    price_per_sqm = self.default_sqm_prices[city]['mahalleler'][district][neighborhood]
                elif city in self.default_sqm_prices and district in self.default_sqm_prices[city]:
                    # İlçe bazlı fiyat mevcut
                    price_per_sqm = self.default_sqm_prices[city][district]
                else:
                    # Bilinmeyen şehir/ilçe için ortalama bir değer
                    price_per_sqm = 15000
                
                # Bina yaşına göre düzeltme
                age_factor = max(0.7, 1 - (property_data['building_age'] * 0.01))
                
                # Oda sayısına göre düzeltme (dropdown'dan gelen değerler)
                room_count = property_data['room_count']
                # room_count değerleri:
                # 1 => 1+0, 2 => 1+1, 3 => 2+1, 4 => 3+1, 5 => 4+1, 6 => 5+1, 7 => 6+1
                # 2+1 (değer 3) standart olarak kabul edilecek
                room_factor = 1 + (room_count - 3) * 0.1
                
                # Tahmini değeri hesapla
                estimated_value = size_sqm * price_per_sqm * age_factor * room_factor
            
            # Calculate confidence score and market trend
            confidence_score = self._calculate_confidence_score(property_data)
            market_trend = self._calculate_market_trend(property_data)
            
            return {
                'estimated_value': estimated_value,
                'confidence_score': confidence_score,
                'market_trend': market_trend
            }
            
        except Exception as e:
            print(f"Error in estimation: {str(e)}")
            # Hata durumunda çok basit bir tahmin yap
            return {
                'estimated_value': property_data['size_sqm'] * 15000,
                'confidence_score': 0.3,
                'market_trend': 0.0
            }
    
    def _calculate_confidence_score(self, property_data):
        """Calculate confidence score based on similar properties"""
        try:
            # Find similar properties in the same area
            similar_properties = ScrapedListing.query.filter(
                ScrapedListing.city == property_data['city'],
                ScrapedListing.district == property_data['district'],
                ScrapedListing.size_sqm.between(
                    property_data['size_sqm'] * 0.8,
                    property_data['size_sqm'] * 1.2
                )
            ).all()
            
            if not similar_properties:
                return 0.5
            
            # Calculate standard deviation of prices
            prices = [p.price for p in similar_properties]
            std_dev = np.std(prices)
            mean_price = np.mean(prices)
            
            # Calculate confidence score (inverse of coefficient of variation)
            confidence_score = 1 - (std_dev / mean_price)
            return max(min(confidence_score, 1.0), 0.0)
        except:
            return 0.5
    
    def _calculate_market_trend(self, property_data):
        """Calculate market trend percentage for the area"""
        try:
            three_months_ago = datetime.utcnow() - timedelta(days=90)
            
            # Get historical prices for similar properties
            historical_prices = db.session.query(
                ScrapedListing.price,
                ScrapedListing.scrape_date
            ).filter(
                ScrapedListing.city == property_data['city'],
                ScrapedListing.district == property_data['district'],
                ScrapedListing.scrape_date >= three_months_ago
            ).order_by(ScrapedListing.scrape_date).all()
            
            if len(historical_prices) < 2:
                return 0.0
            
            # Calculate average price for first and last month
            first_month = [p.price for p in historical_prices[:len(historical_prices)//3]]
            last_month = [p.price for p in historical_prices[-len(historical_prices)//3:]]
            
            if not first_month or not last_month:
                return 0.0
            
            avg_first = np.mean(first_month)
            avg_last = np.mean(last_month)
            
            # Calculate percentage change
            if avg_first == 0:
                return 0.0
                
            return ((avg_last - avg_first) / avg_first) * 100
        except:
            return 0.0
    
    def save_valuation(self, property_id, valuation_result):
        """Save valuation result to database"""
        try:
            # Değerleme sonucunu kontrol et
            if not isinstance(valuation_result, dict):
                print("Invalid valuation result format")
                return None
            
            # Gerekli alanların varlığını kontrol et
            required_fields = ['estimated_value', 'confidence_score', 'market_trend']
            if not all(field in valuation_result for field in required_fields):
                print("Missing required fields in valuation result")
                return None
            
            # Değerleri kontrol et
            if valuation_result['estimated_value'] <= 0:
                print("Invalid estimated value")
                return None
            
            # Yeni değerleme oluştur
            valuation = Valuation(
                property_id=property_id,
                estimated_value=float(valuation_result['estimated_value']),
                confidence_score=float(valuation_result['confidence_score']),
                market_trend=float(valuation_result['market_trend']),
                valuation_date=datetime.utcnow()
            )
            
            # Veritabanına kaydet
            db.session.add(valuation)
            db.session.commit()
            
            print(f"Valuation saved successfully: Property ID {property_id}, Value: {valuation_result['estimated_value']}")
            return valuation
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving valuation: {str(e)}")
            return None 