# E-Trink Global - Agentic E-Commerce AI Automation

## Açıklama

LLM tabanlı ürün önerisi sistemi. Kullanıcı serbest metin talebini yapılandırılmış kriterlere dönüştürerek, katalogdan uygun ürünleri seçen ve finalize eden agentic pipeline.

## Mimarı

1. **Katalog Yükleme** - JSON kaynağından ürün verisi
2. **Normalizasyon** - Heterojen veri formatlarını (fiyat, rating, stok) standartlaştırma
3. **Doğrulama** - Zorunlu alanlar ve veri bütünlüğü kontrolü
4. **Talep Analizi (Step 1)** - LLM ile serbest metni JSON kriterlere çevirme
5. **Aday Seçimi (Step 2)** - Filtreleme ve skorlama ile ürün havuzu oluşturma
6. **Final Öneriler (Step 3)** - LLM ile adaylar arasından en uygunları seçme

## Teknolojiler

- Python 3.x
- pandas, NumPy
- OpenAI API (GPT-3.5-turbo)
- JSON, pathlib

## Kurulum

```bash
pip install pandas numpy openai
```

## Çalıştırma

```bash
# Ortam değişkeni ayarla
export OPENAI_API_KEY="your-key"

# Katalog dosyasını proje dizinine ekle
# alfiq_catalog_snapshot-etrink-global.json

# Çalıştır
python script.py
```

## Giriş

- `alfiq_catalog_snapshot-etrink-global.json` - 40 ürünlü bakır ürünleri kataloğu

## Çıktı

- `outputs/test_1.json` - Test sorgusu 1 sonuçları
- `outputs/test_2.json` - Test sorgusu 2 sonuçları
- `outputs/test_3.json` - Test sorgusu 3 sonuçları

Her çıktı: sorgu, çıkarılan kriterler, seçilen ürünler ve gerekçeleri içerir.

## Filtreleme Kriterleri

Sistem şu özellikleri otomatik çıkarır:
- Maksimum bütçe
- İstenen ürün sayısı
- Minimum rating (örn. "iyi puanlı" → 4.0)
- Kategori anahtar kelimeleri
- Stok gereksinimi


## Demo Video

[🎥 E-TRINK GLOBAL – Agentic E-Commerce Demo](https://drive.google.com/file/d/1gSgKiCaAgkj4SP4TcsAbML478k9eDAp8/view?usp=sharing)
