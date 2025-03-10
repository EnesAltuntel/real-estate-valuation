import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db

with app.app_context():
    db.create_all()
    print("Veritabanı tabloları başarıyla oluşturuldu!") 