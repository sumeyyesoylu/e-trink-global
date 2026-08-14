# -*- coding: utf-8 -*-
"""
E-Trink Global - Agentic E-Commerce & AI Automation Case Study

Bu proje, LLM tabanlı ürün önerisi sistemi için aşağıdaki mimariyi kullanır:
1. Katalog yükleme ve veri normalizasyonu
2. Ürün doğrulama ve filtreleme
3. LLM ile talep analizi (Step 1)
4. Aday ürün seçimi (Step 2)
5. LLM ile final öneriler (Step 3)
"""

import json
import pandas as pd
import numpy as np
import os
import re
from datetime import datetime, timezone
from pathlib import Path

# ============================================================================
# API SETUP - Google Colab ve lokal ortamla uyumlu
# ============================================================================

try:
    from google.colab import userdata
    API_KEY = userdata.get("OPENAI_API_KEY")
except:
    API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise RuntimeError("HATA: OPENAI_API_KEY ortam değişkenine eklenmelidir.")

from openai import OpenAI
client = OpenAI(api_key=API_KEY)


# ============================================================================
# ADIM 1: KATALOG YÜKLEME VE VERİ HAZIRLIĞI
# ============================================================================

print("\n[ADIM 1] Katalog Yükleme ve Başlangıç\n")

with open(
    "alfiq_catalog_snapshot-etrink-global.json",
    "r",
    encoding="utf-8"
) as f:
    data = json.load(f)

df = pd.DataFrame(data["products"])
print(f"Katalog yüklendi: {df.shape[0]} ürün okundu")


# ============================================================================
# ADIM 2: NORMALİZASYON FONKSİYONLARI
# 
# Amaç: Heterojen veri kaynaklarından gelen fiyat, rating, stok bilgilerini
# standardize etmek. Farklı formatlardaki veriler (örn: "100.50 TL", "100,50")
# tek bir float değerine dönüştürülür.
# ============================================================================

def normalize_price(value):
    """Fiyat değerlerini float'a dönüştür. Virgül/nokta sorunlarını çöz."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        cleaned = re.sub(r"[^\d.,]", "", value.strip())

        if cleaned == "":
            return None

        has_dot = "." in cleaned
        has_comma = "," in cleaned

        if has_dot and has_comma:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif has_comma and not has_dot:
            after_comma = cleaned.split(",")[-1]
            if len(after_comma) == 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")

        try:
            return float(cleaned)
        except ValueError:
            return None

    return None


def normalize_price_max(value):
    """Maksimum fiyat normalizasyonu."""
    return normalize_price(value)


def normalize_stock_status(value):
    """Stok durumunu in_stock veya out_of_stock'a dönüştür."""
    if value is None:
        return None

    text = (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )

    in_values = {
        "in_stock", "instock", "available", "available_now",
        "yes", "true", "1"
    }

    out_values = {
        "out_of_stock", "outofstock", "unavailable",
        "no", "false", "0"
    }

    if text in in_values:
        return "in_stock"
    if text in out_values:
        return "out_of_stock"

    return None


def normalize_category(value):
    """Kategori adlarını küçük harfe ve standart formata dönüştür."""
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value).lower()).strip()
    return value


def normalize_rating(value):
    """Rating değerlerini float'a dönüştür."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def normalize_review_count(value):
    """İnceleme sayısını integer'a dönüştür. Eksikse 0 kullan."""
    if value is None:
        return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


# ============================================================================
# ADIM 3: ÜRÜN DOĞRULAMA
# 
# Her ürünün gerekli alanları kontrol edilir:
# - id, name, url (zorunlu)
# - price (geçerli olmalı, negatif olmamalı)
# - rating (1.0-5.0 arasında olmalı)
# - stock_status (in_stock veya out_of_stock)
# ============================================================================

def validate_product(product):
    """Ürünü doğrula ve hata listesi döndür."""
    errors = []

    if not product.get("id"):
        errors.append("missing_id")
    if not product.get("name"):
        errors.append("missing_name")
    if not product.get("url"):
        errors.append("missing_url")

    price = product.get("price")
    if price is None:
        errors.append("invalid_price")
    elif price < 0:
        errors.append("negative_price")

    price_max = product.get("price_max")
    if (price_max is not None and price is not None and price_max < price):
        errors.append("price_max_below_price")

    rating = product.get("rating")
    if rating is not None:
        if rating < 1.0 or rating > 5.0:
            errors.append("rating_out_of_range")

    if product.get("stock_status") is None:
        errors.append("invalid_stock_status")

    return errors


# ============================================================================
# ADIM 4: NORMALİZASYON VE DOĞRULAMA İŞLEMİ
# 
# Tüm ürünler normalizasyon fonksiyonlarından geçer ve geçerli ürünler
# için bir effective_max_price hesaplanır (price_max veya price).
# ============================================================================

print("[ADIM 2] Veri Normalizasyonu ve Doğrulama\n")

df_normalized = pd.DataFrame()

df_normalized["id"] = df["id"]
df_normalized["name"] = df["name"]
df_normalized["url"] = df["url"]
df_normalized["price"] = df["price"].apply(normalize_price)
df_normalized["price_max"] = df["price_max"].apply(normalize_price_max)
df_normalized["currency"] = df["currency"]
df_normalized["stock_status"] = df["stock_status"].apply(normalize_stock_status)
df_normalized["category"] = df["category"].apply(normalize_category)
df_normalized["rating"] = df["rating"].apply(normalize_rating)
df_normalized["review_count"] = df["review_count"].apply(normalize_review_count)

# Effective max price: price_max varsa kullan, yoksa price kullan
df_normalized["effective_max_price"] = df_normalized.apply(
    lambda row: row["price_max"] if pd.notna(row["price_max"]) else row["price"],
    axis=1
)

# Doğrulama işlemi
validation_results = []
for idx, row in df_normalized.iterrows():
    product_dict = row.to_dict()
    errors = validate_product(product_dict)
    if errors:
        validation_results.append({
            "idx": idx,
            "id": row["id"],
            "errors": errors
        })

invalid_ids = [result["id"] for result in validation_results]
df_valid = df_normalized[~df_normalized["id"].isin(invalid_ids)].copy()
products = df_valid.to_dict("records")

print(f"Doğrulanan ürün sayısı: {len(products)}")
print(f"Hatalı ürün sayısı: {len(validation_results)}\n")


# ============================================================================
# ADIM 5: YARDIMCI FONKSİYONLAR - ADAY SEÇİMİ VE SKORLAMA
# ============================================================================

def text_matches(product, keywords):
    """Ürün adı veya kategorisinde anahtar kelime var mı kontrol et."""
    if not keywords:
        return False

    haystack = " ".join([
        str(product.get("name", "")),
        str(product.get("category", ""))
    ]).lower()

    return any(
        keyword.lower() in haystack
        for keyword in keywords
    )


def relevance_score(product, criteria):
    """
    Ürün ile kullanıcı kriterlerinin uyumunu skorla.
    
    Puanlama mantığı:
    - Rating: 0-50 puan (5.0 rating = 50 puan)
    - Review count: 0-5 puan (1000+ yorum = 5 puan)
    - Keyword match: +35 puan (eğer kategori kelimesi varsa)
    - In stock: +15 puan (eğer stokta olma şartı varsa)
    """
    score = 0.0

    rating = product.get("rating")
    reviews = product.get("review_count") or 0

    if rating is not None:
        score += rating * 10
        score += (min(reviews, 1000) / 1000) * 5

    keywords = criteria.get("category_keywords", [])
    if keywords and text_matches(product, keywords):
        score += 35

    if (criteria.get("require_in_stock") and 
        product.get("stock_status") == "in_stock"):
        score += 15

    return score


def select_candidates(products_list, criteria):
    """
    Kullanıcı kriterlerine uygun aday ürünleri seç.
    
    Filtreleme aşamaları:
    1. Bütçe kontrolü: effective_max_price <= max_total_budget
    2. Rating kontrolü: rating >= min_rating
    3. Stok kontrolü: stock_status == "in_stock" (eğer gerekiyorsa)
    4. Skorlama ve sıralama
    5. Önem sırası: relevance_score, rating, review_count, fiyat
    """
    candidates = []

    max_budget = criteria.get("max_total_budget")
    min_rating = criteria.get("min_rating")
    require_in_stock = criteria.get("require_in_stock", False)
    keywords = criteria.get("category_keywords", [])
    number_of_products = criteria.get("number_of_products", 1)

    # Filtreleme aşaması
    for product in products_list:
        effective_price = product.get("effective_max_price")

        if effective_price is None:
            continue

        if max_budget is not None and effective_price > max_budget:
            continue

        if min_rating is not None:
            if product.get("rating") is None or product["rating"] < min_rating:
                continue

        if require_in_stock:
            if product.get("stock_status") != "in_stock":
                continue

        product["_relevance_score"] = relevance_score(product, criteria)
        candidates.append(product)

    if not candidates:
        return []

    # Anahtar kelimeler varsa, önce kelime eşleşenleri seç
    if keywords:
        keyword_matches = [p for p in candidates if text_matches(p, keywords)]
        pool = keyword_matches if keyword_matches else candidates
    else:
        pool = candidates

    # Sıralama: relevance_score, rating, review_count, price
    pool.sort(
        key=lambda p: (
            p.get("_relevance_score", 0),
            p.get("rating") or 0,
            p.get("review_count") or 0,
            -(p.get("effective_max_price") or 0)
        ),
        reverse=True
    )

    return pool[:number_of_products]


# ============================================================================
# ADIM 6: LLM TABANLI ÜRÜN ÖNERİ SİSTEMİ
# 
# Bu sistem iki adımlı LLM çağrısı kullanır:
#
# Adım 3 (Talep Analizi):
#   Kullanıcı serbest metin talebini yapılandırılmış JSON'a dönüştür.
#   LLM burada: bütçe, ürün sayısı, minimum rating, kategori anahtar kelimelerini çıkarır.
#
# Adım 4 (Aday Seçimi):
#   Filtreleme algoritması ile kriterlere uygun ürünleri bul.
#
# Adım 5 (Final Öneriler):
#   Aday ürünler arasından LLM en uygun olanları seçer ve gerekçe sunar.
# ============================================================================

print("[ADIM 3-5] LLM Tabanlı Ürün Önerisi Sistemi\n")

Path("outputs").mkdir(exist_ok=True)

# Test sorguları
QUERIES = [
    "100 dolar altında, iyi puanlı, hediyelik bir ürün öner",
    "Bir spa işletmesi için 300 dolar bütçeyle 2 ürün öner",
    "Türk kahvesi seven birine hediye arıyorum, stokta olsun"
]

all_results = []

for i, query in enumerate(QUERIES, 1):
    print(f"[TEST {i}/3] {query}")
    print("-" * 80)

    try:
        # =====================================================================
        # STEP 3: Kullanıcı talebini yorumla ve JSON kriterlere dönüştür
        # =====================================================================

        parse_prompt = f"""
Kullanıcı talebi:

{query}


Kullanıcı talebini analiz et ve aşağıdaki JSON formatında döndür.

SADECE JSON döndür:

{{
    "max_total_budget": sayı veya null,
    "number_of_products": 1-10,
    "min_rating": 1-5 veya null,
    "category_keywords": [kelimeler]
}}

Kurallar:

- max_total_budget: Belirtilen maksimum bütçe. Yok ise null.
- number_of_products: İstenen ürün sayısı (default: 1)
- min_rating: "iyi puanlı" → 4, "yüksek puanlı" → 4.5. Yok ise null.
- category_keywords: Ürün türünü tanımlayan anahtar kelimeler.

Örnekler:

Türk kahvesi: ["kahve", "türk kahvesi", "turkish coffee", "cezve"]
Spa: ["spa", "massage", "wellness", "sauna"]
Hediye: ["hediye", "gift", "premium"]
"""

        resp1 = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": parse_prompt}],
            temperature=0,
            max_tokens=300
        )

        criteria_text = resp1.choices[0].message.content.strip()

        if "```" in criteria_text:
            criteria_text = (
                criteria_text
                .split("```")[1]
                .replace("json", "")
                .strip()
            )

        criteria = json.loads(criteria_text)

        # Stok şartı kontrolü
        query_lower = query.lower()
        stock_phrases = [
            "stokta olsun", "stokta olmalı", "stokta bulunan",
            "stokta mevcut", "in stock", "available"
        ]
        require_in_stock = any(phrase in query_lower for phrase in stock_phrases)
        criteria["require_in_stock"] = require_in_stock

        # Tür dönüştürmeleri ve validasyon
        try:
            criteria["number_of_products"] = int(criteria.get("number_of_products", 1))
        except:
            criteria["number_of_products"] = 1

        if criteria["number_of_products"] < 1 or criteria["number_of_products"] > 10:
            criteria["number_of_products"] = 1

        if criteria.get("min_rating") is not None:
            try:
                criteria["min_rating"] = float(criteria["min_rating"])
            except:
                criteria["min_rating"] = None

        if criteria.get("max_total_budget") is not None:
            try:
                criteria["max_total_budget"] = float(criteria["max_total_budget"])
            except:
                criteria["max_total_budget"] = None

        if not isinstance(criteria.get("category_keywords"), list):
            criteria["category_keywords"] = []

        # Çıkarılan kriterler ekrana yazdır
        print("Çıkarılan Kriterler:")
        print(f"   Bütçe: ${criteria.get('max_total_budget') or 'Sınırsız'}")
        print(f"   Ürün Sayısı: {criteria.get('number_of_products', 1)}")
        print(f"   Min Rating: {criteria.get('min_rating') or 'Yok'}")
        print(f"   Stokta Olması: {'Evet' if criteria.get('require_in_stock') else 'Hayır'}")
        print(f"   Anahtar Kelimeler: {criteria.get('category_keywords', [])}\n")

        # =====================================================================
        # STEP 4: Kriterlere uygun aday ürünleri seç
        # =====================================================================

        candidates = select_candidates(products, criteria)
        print(f"{len(candidates)} aday ürün seçildi")
        
        if candidates:
            print("   Adaylar:")
            for j, c in enumerate(candidates, 1):
                print(f"   {j}. [{c['id']}] {c['name']} (${c['price']:.2f})")
            print()

        # =====================================================================
        # Sonuç objesi oluştur
        # =====================================================================

        result = {
            "user_query": query,
            "criteria": criteria,
            "recommendations": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # =====================================================================
        # STEP 5: Aday ürünler arasından LLM ile final seçim yap
        # =====================================================================

        if candidates:
            safe_candidates = [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "price": p["price"],
                    "price_max": p["price_max"],
                    "currency": p["currency"],
                    "stock_status": p["stock_status"],
                    "category": p["category"],
                    "rating": p["rating"],
                    "review_count": p["review_count"],
                    "url": p["url"]
                }
                for p in candidates
            ]

            rec_prompt = f"""
Kullanıcı talebi:

{query}

ÖNEMLİ: Kullanıcı {criteria['number_of_products']} ADET ürün istiyor.

Aşağıdaki ürünler katalogdan seçilmiş aday ürünlerdir:

{json.dumps(safe_candidates, ensure_ascii=False, indent=2)}

Görev:

Bu aday ürünler arasından kullanıcı talebine en uygun {criteria['number_of_products']} ürünü seç.

Kurallar:

1. Tam olarak {criteria['number_of_products']} ürün öner.
2. Her ürün için kısa seçim gerekçesi yaz.
3. Sadece verilen aday ürünler arasından seç.
4. Katalogda bulunmayan ürün oluşturma.
5. Kullanıcının bütçesine uy.
6. Aynı ürünü iki kez önerme.

SADECE JSON döndür:

{{
    "recommendations": [
        {{
            "id": "...",
            "reason": "..."
        }}
    ]
}}
"""

            resp2 = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": rec_prompt}],
                temperature=0.2,
                max_tokens=400
            )

            recs_text = resp2.choices[0].message.content.strip()
            print(f"LLM Yanıtı (İlk 300 karakter):")
            print(recs_text[:300] + "...\n")

            if "```" in recs_text:
                recs_text = (
                    recs_text
                    .split("```")[1]
                    .replace("json", "")
                    .strip()
                )

            recs = json.loads(recs_text)
            print(f"Parse edilen öneriler: {len(recs.get('recommendations', []))}\n")

            candidate_map = {c["id"]: c for c in candidates}
            selected_ids = set()

            for rec in recs.get("recommendations", []):
                pid = rec.get("id")

                if pid not in candidate_map:
                    print(f"Uyarı: Ürün bulunamadı - {pid}")
                    continue

                if pid in selected_ids:
                    print(f"Uyarı: Duplikat - {pid} (zaten seçilmiş)")
                    continue

                if len(result["recommendations"]) >= criteria["number_of_products"]:
                    print(f"Uyarı: İstenen {criteria['number_of_products']} ürün seçildi")
                    break

                selected_ids.add(pid)
                p = candidate_map[pid]

                result["recommendations"].append({
                    "id": p["id"],
                    "name": p["name"],
                    "price": float(p["price"]),
                    "url": p["url"],
                    "reason": rec.get("reason", "")
                })

        all_results.append(result)

        # Sonuçları dosyaya kaydet
        output_path = Path(f"outputs/test_{i}.json")
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # Önerileri ekrana yazdır
        print("Öneriler:")
        if not result["recommendations"]:
            print("   Uygun ürün bulunamadı.")
        else:
            for j, rec in enumerate(result["recommendations"], 1):
                print(f"  {j}. [{rec['id']}] {rec['name']} - ${rec['price']:.2f}")
                print(f"     URL: {rec['url']}")
                print(f"     Gerekçe: {rec['reason']}")

        print(f"Kaydedildi: outputs/test_{i}.json\n")

    except Exception as e:
        print(f"Hata oluştu: {e}\n")

        result = {
            "user_query": query,
            "recommendations": [],
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        all_results.append(result)

        output_path = Path(f"outputs/test_{i}.json")
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


# ============================================================================
# ADIM 7: ÖZET SONUÇLAR
# ============================================================================

print("\n" + "=" * 80)
print("ÖZET SONUÇLAR")
print("=" * 80)

for result in all_results:
    print(f"\nTalep: {result['user_query']}")
    print(f"Zaman: {result['timestamp']}")

    if result.get("error"):
        print(f"Hata: {result['error']}")
    else:
        print(f"Önerilen ürün sayısı: {len(result['recommendations'])}")

        for rec in result["recommendations"]:
            print(f"   - [{rec['id']}] {rec['name']} (${rec['price']:.2f})")
            print(f"     URL: {rec['url']}")
