# E-Trink Global - Kurulum Rehberi

## 📋 Gerekli Yazılımlar

- Python 3.8+
- pip (Python paket yöneticisi)
- Git

---

## 🚀 Adım 1: Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

---

## 🔑 Adım 2: OpenAI API Key Ayarla

### Seçenek A: .env Dosyası Kullan

```bash
# .env dosyası oluştur
cat > .env << EOF
OPENAI_API_KEY=sk-your-api-key-here
EOF
```

### Seçenek B: Ortam Değişkeni Olarak Ayarla

```bash
# Linux/Mac
export OPENAI_API_KEY="sk-your-api-key-here"

# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-api-key-here"
```

---

## 📁 Adım 3: Klasör Yapısını Kontrol Et

```bash
# Klasör yapısı şu şekilde olmalı:
etrink-global/
├── .env
├── .gitignore
├── .env.example
├── README.md
├── SETUP.md
├── requirements.txt
├── etrink_agent.py
├── prompts.py
├── sheets_export.py
├── alfiq_catalog_snapshot-etrink-global.json
└── outputs/
    ├── test_1.json
    ├── test_2.json
    └── test_3.json
```

---

## ▶️ Adım 4: Kodu Çalıştır

```bash
python etrink_agent.py
```

**Beklenen çıktı:**

```
[ADIM 1] Katalog Yükleme

✅ Katalog yüklendi: 40 ürün
[ADIM 2] Normalizasyon ve Doğrulama

✅ Doğrulanan ürün sayısı: 40
❌ Hatalı ürün sayısı: 0

[ADIM 3-5] LLM Tabanlı Ürün Önerisi

[TEST 1/3] 100 dolar altında, iyi puanlı, hediyelik bir ürün öner
✅ 1 aday seçildi
📊 Öneriler:
1. [ALF-0015] Handcrafted Hammered Copper Incense Burner - $79.00
```

---

## 📊 Adım 5: Çıktıları Kontrol Et

```bash
# Dosyaları listele
ls -la outputs/

# Sonuçları görüntüle
cat outputs/test_1.json | python -m json.tool
```

---

## 🐛 Sorun Çözme

### "OPENAI_API_KEY not found" Hatası

```bash
# API key'in ayarlandığını kontrol et
echo $OPENAI_API_KEY

# Veya .env dosyasını kontrol et
cat .env
```

### "Katalog dosyası bulunamadı" Hatası

```bash
# Dosyanın adını kontrol et
ls alfiq_catalog_snapshot-etrink-global.json
```

### JSON Parse Hatası

```bash
# JSON dosyasının valid olup olmadığını kontrol et
python -c "import json; json.load(open('outputs/test_1.json'))"
```

---

## ✅ Başarılı Kurulum

Hepsi tamamlandıysa:

```
✅ Katalog 40 ürün ile yüklendi
✅ Normalizasyon başarılı (0 hata)
✅ 3 test sorgusu çalıştırıldı
✅ outputs/ klasöründe 3 JSON dosyası var
```

Tebrikler! 🎉
