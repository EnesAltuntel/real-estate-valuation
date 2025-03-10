// Türkiye'deki şehir, ilçe ve mahalle verileri
const locationData = {
    "İstanbul": {
        "Kadıköy": ["Caferağa", "Fenerbahçe", "Göztepe", "Kozyatağı"],
        "Beşiktaş": ["Levent", "Etiler", "Bebek", "Arnavutköy"],
        "Üsküdar": ["Acıbadem", "Altunizade", "Beylerbeyi", "Çengelköy"]
    },
    "Ankara": {
        "Çankaya": ["Bahçelievler", "Çayyolu", "Oran", "Gaziosmanpaşa"],
        "Yenimahalle": ["Batıkent", "Demetevler", "Karşıyaka", "Ostim"],
        "Keçiören": ["Aktepe", "Esertepe", "Etlik", "Kalaba"]
    },
    "İzmir": {
        "Konak": ["Alsancak", "Göztepe", "Güzelyalı", "Karataş"],
        "Karşıyaka": ["Bostanlı", "Mavişehir", "Atakent", "Çarşı"],
        "Bornova": ["Evka", "Özkanlar", "Kazımdirik", "Erzene"]
    }
};

document.addEventListener('DOMContentLoaded', async function() {
    const citySelect = document.getElementById('city');
    const districtSelect = document.getElementById('district');
    const neighborhoodSelect = document.getElementById('neighborhood');

    console.log('DOM loaded, elements found:', {
        citySelect: !!citySelect,
        districtSelect: !!districtSelect,
        neighborhoodSelect: !!neighborhoodSelect
    });

    // Şehirleri yükle
    async function loadCities() {
        console.log('Loading cities...');
        setLoading(citySelect, true);
        try {
            const response = await fetch('/api/locations/cities');
            console.log('Cities API response:', response);
            
            if (!response.ok) {
                throw new Error(`Şehirler yüklenemedi: ${response.status}`);
            }
            
            const cities = await response.json();
            console.log('Loaded cities:', cities);
            
            // Mevcut seçenekleri temizle
            citySelect.innerHTML = '<option value="">Seçiniz</option>';
            
            // Yeni seçenekleri ekle
            cities.forEach(city => {
                const option = new Option(city, city);
                citySelect.add(option);
            });
            
            console.log('Cities loaded successfully');
        } catch (error) {
            console.error('Şehirler yüklenirken hata oluştu:', error);
            // Hata mesajını göster
            const errorOption = new Option('Hata oluştu', '');
            errorOption.disabled = true;
            citySelect.innerHTML = '';
            citySelect.add(errorOption);
        } finally {
            setLoading(citySelect, false);
        }
    }

    // Şehir seçildiğinde ilçeleri güncelle
    async function loadDistricts(selectedCity) {
        console.log('Loading districts for city:', selectedCity);
        setLoading(districtSelect, true);
        
        // İlçe ve mahalle seçimlerini sıfırla
        districtSelect.innerHTML = '<option value="">Seçiniz</option>';
        neighborhoodSelect.innerHTML = '<option value="">Seçiniz</option>';
        
        if (selectedCity) {
            try {
                const response = await fetch(`/api/locations/districts/${encodeURIComponent(selectedCity)}`);
                console.log('Districts API response:', response);
                
                if (!response.ok) {
                    throw new Error(`İlçeler yüklenemedi: ${response.status}`);
                }
                
                const districts = await response.json();
                console.log('Loaded districts:', districts);
                
                districts.forEach(district => {
                    const option = new Option(district, district);
                    districtSelect.add(option);
                });
                
                districtSelect.disabled = false;
                console.log('Districts loaded successfully');
            } catch (error) {
                console.error('İlçeler yüklenirken hata oluştu:', error);
                const errorOption = new Option('Hata oluştu', '');
                errorOption.disabled = true;
                districtSelect.innerHTML = '';
                districtSelect.add(errorOption);
                districtSelect.disabled = true;
            } finally {
                setLoading(districtSelect, false);
            }
        } else {
            districtSelect.disabled = true;
            neighborhoodSelect.disabled = true;
        }
    }

    // İlçe seçildiğinde mahalleleri güncelle
    async function loadNeighborhoods(selectedCity, selectedDistrict) {
        console.log('Loading neighborhoods for:', { city: selectedCity, district: selectedDistrict });
        setLoading(neighborhoodSelect, true);
        
        // Mahalle seçimini sıfırla
        neighborhoodSelect.innerHTML = '<option value="">Seçiniz</option>';
        
        if (selectedCity && selectedDistrict) {
            try {
                const response = await fetch(`/api/locations/neighborhoods/${encodeURIComponent(selectedCity)}/${encodeURIComponent(selectedDistrict)}`);
                console.log('Neighborhoods API response:', response);
                
                if (!response.ok) {
                    throw new Error(`Mahalleler yüklenemedi: ${response.status}`);
                }
                
                const neighborhoods = await response.json();
                console.log('Loaded neighborhoods:', neighborhoods);
                
                neighborhoods.forEach(neighborhood => {
                    const option = new Option(neighborhood, neighborhood);
                    neighborhoodSelect.add(option);
                });
                
                neighborhoodSelect.disabled = false;
                console.log('Neighborhoods loaded successfully');
            } catch (error) {
                console.error('Mahalleler yüklenirken hata oluştu:', error);
                const errorOption = new Option('Hata oluştu', '');
                errorOption.disabled = true;
                neighborhoodSelect.innerHTML = '';
                neighborhoodSelect.add(errorOption);
                neighborhoodSelect.disabled = true;
            } finally {
                setLoading(neighborhoodSelect, false);
            }
        } else {
            neighborhoodSelect.disabled = true;
        }
    }

    // Event listeners
    citySelect.addEventListener('change', function() {
        console.log('City selected:', this.value);
        loadDistricts(this.value);
    });

    districtSelect.addEventListener('change', function() {
        console.log('District selected:', this.value);
        loadNeighborhoods(citySelect.value, this.value);
    });

    // Yükleme durumunda UI feedback
    function setLoading(select, loading) {
        select.disabled = loading;
        const parent = select.parentElement;
        if (loading) {
            parent.classList.add('is-loading');
        } else {
            parent.classList.remove('is-loading');
        }
    }

    // İlk yükleme
    console.log('Starting initial load...');
    await loadCities();
}); 