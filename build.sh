#!/bin/bash
# Basit bir veritabanı kontrolü yapıp yoksa oluşturalım

cd src
python - << EOL
from app import app, db
with app.app_context():
    db.create_all()
print("Veritabanı kontrol edildi ve hazırlandı.")
EOL
cd .. 