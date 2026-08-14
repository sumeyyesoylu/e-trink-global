# E-Trink Global - LLM Prompts ve Agent Talimatları

## STEP 3: Talep Analizi Prompt'ı

```
Kullanıcı talebi:

{USER_QUERY}

Kullanıcı talebini analiz et ve aşağıdaki JSON formatında döndür.

SADECE JSON döndür:

{
    "max_total_budget": sayı veya null,
    "number_of_products": 1-10,
    "min_rating": 1-5 veya null,
    "category_keywords": [kelimeler]
}

Kurallar:

- max_total_budget: Belirtilen maksimum bütçe. Yok ise null.
- number_of_products: İstenen ürün sayısı (default: 1)
- min_rating: "iyi puanlı" → 4, "yüksek puanlı" → 4.5. Yok ise null.
- category_keywords: Ürün türünü tanımlayan anahtar kelimeler.

Örnekler:

Türk kahvesi: ["kahve", "türk kahvesi", "turkish coffee", "cezve"]
Spa: ["spa", "massage", "wellness", "sauna"]
Hediye: ["hediye", "gift", "premium"]
```

## STEP 5: Final Öneriler Prompt'ı

```
Kullanıcı talebi:

{USER_QUERY}

ÖNEMLİ: Kullanıcı {NUMBER_OF_PRODUCTS} ADET ürün istiyor.

Aşağıdaki ürünler katalogdan seçilmiş aday ürünlerdir:

{CANDIDATE_PRODUCTS_JSON}

Görev:

Bu aday ürünler arasından kullanıcı talebine en uygun {NUMBER_OF_PRODUCTS} ürünü seç.

Kurallar:

1. Tam olarak {NUMBER_OF_PRODUCTS} ürün öner.
2. Her ürün için kısa seçim gerekçesi yaz.
3. Sadece verilen aday ürünler arasından seç.
4. Katalogda bulunmayan ürün oluşturma.
5. Kullanıcının bütçesine uy.
6. Aynı ürünü iki kez önerme.

SADECE JSON döndür:

{
    "recommendations": [
        {
            "id": "...",
            "reason": "..."
        }
    ]
}
```

## Agent Talimatları - Adım Adım Akış

### ADIM 1: Katalog Yükleme
- JSON dosyasından ürün kataloğu yükle
- DataFrame formatına dönüştür
- Toplam ürün sayısını kontrol et

### ADIM 2: Veri Normalizasyonu
- Fiyat normalizasyonu: Farklı formatları (100.50, 100,50, "100 TL") float'a çevir
- Stok durumu: "in_stock" veya "out_of_stock" olarak standartlaştır
- Kategori: Küçük harfe ve boşlukları normalize et
- Rating: 1.0-5.0 aralığında float'a çevir
- İnceleme sayısı: Integer'a çevir, eksikse 0 kullan
- Effective max price: price_max varsa onu, yoksa price kullan

### ADIM 3: Ürün Doğrulama
Her ürün için kontrol et:
- id, name, url: Zorunlu (varsa devam et)
- price: Geçerli sayı ve negatif olmamalı
- price_max: price'dan küçük olmamalı
- rating: 1.0-5.0 aralığında olmalı
- stock_status: in_stock veya out_of_stock olmalı

### ADIM 4: LLM Talep Analizi (STEP 3)
- Serbest metin sorguyu LLM'e gönder
- Dönen JSON'ı parse et
- Bütçe, ürün sayısı, minimum rating, anahtar kelimeleri çıkar
- Stok şartı kontrolü: Sorgu "stokta olsun" içeriyorsa require_in_stock = true

### ADIM 5: Aday Seçimi (STEP 4)
Sıralı filtreleme:
1. Bütçe kontrolü: effective_max_price <= max_total_budget
2. Rating kontrolü: rating >= min_rating
3. Stok kontrolü: stock_status == "in_stock" (gerekiyorsa)
4. Relevance score hesabı:
   - Rating: rating * 10 (max 50 puan)
   - Review count: min(reviews, 1000) / 1000 * 5 (max 5 puan)
   - Keyword match: +35 puan
   - In stock: +15 puan
5. Sıralama: relevance_score, rating, review_count, fiyat (descending)
6. İlk N ürünü seç

### ADIM 6: LLM Final Öneriler (STEP 5)
- Seçilen aday ürünleri JSON formatında hazırla
- LLM'e istenen sayıda önerisi ver
- Dönen JSON'dan ürün ID'lerini ve gerekçeleri çıkar
- Katalog üzerinde kontrol et ve duplikat var mı kontrol et
- Sonuç objesine ekle

### ADIM 7: Çıktı ve Kayıt
- Sonuçları JSON dosyasına kaydet: outputs/test_{i}.json
- Konsola özet sonuçları yazdır
