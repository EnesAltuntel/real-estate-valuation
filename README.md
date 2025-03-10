# Gayrimenkul Değerleme Sistemi

Bu proje, Sahibinden.com'dan emlak verilerini toplayarak gayrimenkul değerleme yapan bir web uygulamasıdır. Yapay zeka ve makine öğrenmesi algoritmaları kullanarak mülklerin değerini tahmin eder ve piyasa analizleri sunar.

## Özellikler

- Sahibinden.com'dan otomatik veri toplama
- Makine öğrenmesi tabanlı değerleme
- Detaylı piyasa analizi ve raporlama
- Kullanıcı hesap yönetimi
- Mülk portföyü yönetimi
- Değerleme geçmişi takibi
- Bölgesel fiyat trendleri
- Benzer mülk karşılaştırması

## Kurulum

### Gereksinimler

- Python 3.8+
- pip (Python paket yöneticisi)
- Chrome WebDriver (web scraping için)

### Adımlar

1. Projeyi klonlayın:
```bash
git clone https://github.com/yourusername/real-estate-valuation.git
cd real-estate-valuation
```

2. Sanal ortam oluşturun ve aktifleştirin:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

4. Veritabanını oluşturun:
```bash
flask db upgrade
```

5. Uygulamayı çalıştırın:
```bash
python src/app.py
```

Uygulama varsayılan olarak http://localhost:5000 adresinde çalışacaktır.

## Kullanım

1. Hesap Oluşturma
   - Ana sayfadan "Kayıt Ol" butonuna tıklayın
   - E-posta ve şifrenizi girin
   - Hesabınızı oluşturun

2. Mülk Ekleme
   - Dashboard'dan "Yeni Mülk Ekle" butonuna tıklayın
   - Mülk bilgilerini girin
   - Sistem otomatik olarak değerleme yapacaktır

3. Değerleme Güncelleme
   - Mülk detay sayfasından "Değerlemeyi Güncelle" butonuna tıklayın
   - Sistem güncel piyasa verilerini toplayarak yeni bir değerleme yapacaktır

4. Piyasa Analizi
   - Dashboard'da genel piyasa trendlerini görüntüleyin
   - Mülk detay sayfasında benzer mülkleri ve fiyat değişimlerini inceleyin

## Güvenlik

- Kullanıcı şifreleri hash'lenerek saklanır
- Oturum yönetimi güvenli bir şekilde yapılır
- Web scraping için rate limiting uygulanır
- API istekleri için güvenlik kontrolleri yapılır

## Katkıda Bulunma

1. Bu repository'yi fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Bir Pull Request oluşturun

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## İletişim

Proje Sahibi - enessaltuntel@gmail.com

Proje Linki: [https://github.com/yourusername/real-estate-valuation](https://github.com/yourusername/real-estate-valuation) 
