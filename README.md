# E-Trink Global - Agentic E-Commerce AI Automation

## 📋 Proje Tanımı

**E-Trink Global**, OpenAI LLM ve kural tabanlı Python algoritmasını birleştiren agentic bir e-commerce ürün önerme sistemidir.

Sistem, müşteri taleplerini serbest metin olarak alır, yapılandırılmış kriterler haline çevirir, katalogdan en uygun ürünleri seçer ve detaylı seçim gerekçesiyle JSON çıktı üretir.

### 🎯 Kullanım Senaryoları

1. **100 dolar altında, iyi puanlı, hediyelik bir ürün öner**
   - Bütçe kısıtı + Rating filtresi + Kategori eşleşmesi

2. **Bir spa işletmesi için 300 dolar bütçeyle 2 ürün öner**
   - Çoklu ürün seçimi + Sepet bütçe kontrolü

3. **Türk kahvesi seven birine hediye arıyorum, stokta olsun**
   - Stok garantisi + Anlamsal eşleşme

---

## 🏗️ Mimari Yapı

```
┌─────────────────────────┐
│  Serbest Metin Talep    │  "100$ altında, iyi puanlı hediye öner"
│  (JSON)                 │
└──────────┬──────────────┘
           │
           ▼
┌──────────────────────────┐
│  ADIM 1: LLM Prompt      │  OpenAI gpt-3.5-turbo
│  Talep Analizi           │  → Kriterleri ayıkla
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────────┐
│  ADIM 2: Kural Tabanlı Filter│  Python
│  (select_candidates)        │  → Adayları seç
│  - Bütçe                    │  → Stok durumu
│  - Rating                   │  → Kategori
│  - Anahtar Kelimeler       │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  ADIM 3: LLM Seçim Gerekçesi │  OpenAI gpt-3.5-turbo
│  (Adaylar Arasından Seçim)   │  → "Neden bu ürün?"
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  ADIM 4: Çıktı Validasyon    │  Python
│  (Output Validation)         │  → ID kontrol
│  - Hallucination Guard       │  → Sahte ürün filtresi
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  JSON Çıktı + Dosya Kayıt    │  outputs/test_X.json
└──────────────────────────────┘
```

---

## 📦 Teknoloji Stack

| Bileşen | Teknoloji | Versiyon |
|---------|-----------|----------|
| **Dil** | Python | 3.8+ |
| **LLM** | OpenAI GPT-3.5-turbo | Latest |
| **Veri İşleme** | Pandas | 1.x+ |
| **Dosya Format** | JSON | UTF-8 |
| **API** | OpenAI SDK | Latest |

---

## 🚀 Kurulum & Çalıştırma

### 1️⃣ Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

### 2️⃣ OpenAI API Key Ayarla

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

### 3️⃣ Kodu Çalıştır

```bash
python etrink_agent.py
```

### 4️⃣ Çıktıları Kontrol Et

```bash
ls outputs/
# outputs/test_1.json
# outputs/test_2.json
# outputs/test_3.json
```

---

## 📊 Çıktı Formatı

Her test için JSON çıktı:

```json
{
  "query": "Kullanıcı talebi",
  "timestamp": "2026-08-14T00:27:51.600486+00:00",
  "extracted_criteria": {
    "budget": 100.0,
    "quantity": 1,
    "min_rating": 4.0,
    "in_stock_only": false,
    "keywords": ["hediye", "gift", "premium"]
  },
  "recommendations": [
    {
      "id": "ALF-0015",
      "title": "Ürün Adı",
      "price": 79.0,
      "url": "https://...",
      "reason": "Seçim gerekçesi (Türkçe)"
    }
  ]
}
```

---

## ✅ Test Sonuçları

| Test | Sorgu | Beklenen | Elde Edilen | Durum |
|------|-------|----------|-------------|-------|
| 1 | Hediye, $100 altı | 1 ürün | 1 ürün | ✅ PASS |
| 2 | Spa, $300, 2 ürün | 2 ürün | 2 ürün | ✅ PASS |
| 3 | Kahve, stokta | 1 ürün | 1 ürün | ✅ PASS |

---

## 📝 Lisans

Bu proje eğitim ve araştırma amaçlıdır.
