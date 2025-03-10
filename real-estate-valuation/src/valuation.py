import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from datetime import datetime, timedelta
from models import db, ScrapedListing, Valuation

class PropertyValuator:
    def __init__(self):
        self.model = None
        self.preprocessor = None
        self.feature_columns = [
            'city', 'district', 'neighborhood',
            'property_type', 'size_sqm', 'room_count',
            'building_age', 'floor_number'
        ]
    
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
        """Estimate property value using trained model"""
        if not self.model:
            self.train_model()
        
        # Prepare input data
        input_df = pd.DataFrame([property_data])
        
        # Make prediction
        estimated_value = self.model.predict(input_df)[0]
        
        # Calculate confidence score based on similar properties
        confidence_score = self._calculate_confidence_score(property_data)
        
        # Calculate market trend
        market_trend = self._calculate_market_trend(property_data)
        
        return {
            'estimated_value': estimated_value,
            'confidence_score': confidence_score,
            'market_trend': market_trend
        }
    
    def _calculate_confidence_score(self, property_data):
        """Calculate confidence score based on similar properties"""
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
    
    def _calculate_market_trend(self, property_data):
        """Calculate market trend percentage for the area"""
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
    
    def save_valuation(self, property_id, valuation_result):
        """Save valuation result to database"""
        try:
            valuation = Valuation(
                property_id=property_id,
                estimated_value=valuation_result['estimated_value'],
                confidence_score=valuation_result['confidence_score'],
                market_trend=valuation_result['market_trend']
            )
            
            db.session.add(valuation)
            db.session.commit()
            
            return valuation
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving valuation: {str(e)}")
            return None 