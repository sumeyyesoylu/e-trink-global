# -*- coding: utf-8 -*-

"""
E-Trink Global - Agentic E-Commerce AI Automation Case Study
Ana Program
"""

import json
import pandas as pd
import os
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from google.colab import userdata
    API_KEY = userdata.get("OPENAI_API_KEY")
except:
    API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise RuntimeError("HATA: OPENAI_API_KEY ortam değişkenine eklenmelidir!")

from openai import OpenAI
client = OpenAI(api_key=API_KEY)

DEBUG = True
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

print("\n[ADIM 1] Katalog Yükleme\n")

with open("alfiq_catalog_snapshot-etrink-global.json", "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data["products"])
print(f"✅ Katalog yüklendi: {df.shape[0]} ürün")

def normalize_price(value):
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

def normalize_stock_status(value):
    if value is None:
        return None
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    in_values = {"in_stock", "instock", "available", "yes", "true", "1"}
    out_values = {"out_of_stock", "outofstock", "unavailable", "no", "false", "0"}
    if text in in_values:
        return "in_stock"
    if text in out_values:
        return "out_of_stock"
    return None

def normalize_category(value):
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value).lower()).strip()
    return value

def normalize_rating(value):
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
    if value is None:
        return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0

print("[ADIM 2] Normalizasyon ve Doğrulama\n")

df_normalized = pd.DataFrame()
df_normalized["id"] = df["id"]
df_normalized["name"] = df["name"]
df_normalized["url"] = df["url"]
df_normalized["price"] = df["price"].apply(normalize_price)
df_normalized["price_max"] = df["price_max"].apply(normalize_price)
df_normalized["currency"] = df["currency"]
df_normalized["stock_status"] = df["stock_status"].apply(normalize_stock_status)
df_normalized["category"] = df["category"].apply(normalize_category)
df_normalized["rating"] = df["rating"].apply(normalize_rating)
df_normalized["review_count"] = df["review_count"].apply(normalize_review_count)

df_normalized["effective_max_price"] = df_normalized.apply(
    lambda row: row["price_max"] if pd.notna(row["price_max"]) else row["price"],
    axis=1
)

def validate_product(product):
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
    if price_max is not None and price is not None and price_max < price:
        errors.append("price_max_below_price")
    rating = product.get("rating")
    if rating is not None:
        if rating < 1.0 or rating > 5.0:
            errors.append("rating_out_of_range")
    if product.get("stock_status") is None:
        errors.append("invalid_stock_status")
    return errors

validation_results = []
for idx, row in df_normalized.iterrows():
    product_dict = row.to_dict()
    errors = validate_product(product_dict)
    if errors:
        validation_results.append({"idx": idx, "id": row["id"], "errors": errors})

invalid_ids = [result["id"] for result in validation_results]
df_valid = df_normalized[~df_normalized["id"].isin(invalid_ids)].copy()
products = df_valid.to_dict("records")

print(f"✅ Doğrulanan ürün sayısı: {len(products)}")
print(f"❌ Hatalı ürün sayısı: {len(validation_results)}\n")

def text_matches(product, keywords):
    if not keywords:
        return False
    haystack = " ".join([
        str(product.get("name", "")),
        str(product.get("category", ""))
    ]).lower()
    return any(keyword.lower() in haystack for keyword in keywords)

def relevance_score(product, criteria):
    score = 0.0
    rating = product.get("rating")
    reviews = product.get("review_count") or 0
    if rating is not None:
        score += rating * 10
        score += min(reviews, 1000) / 1000 * 5
    keywords = criteria.get("category_keywords", [])
    if keywords and text_matches(product, keywords):
        score += 35
    if criteria.get("require_in_stock") and product.get("stock_status") == "in_stock":
        score += 15
    return score

def select_candidates(products_list, criteria):
    candidates = []
    max_budget = criteria.get("max_total_budget")
    min_rating = criteria.get("min_rating")
    require_in_stock = criteria.get("require_in_stock", False)
    keywords = criteria.get("category_keywords", [])
    number_of_products = criteria.get("number_of_products", 1)

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
        if keywords:
            if not text_matches(product, keywords):
                continue

        product["_relevance_score"] = relevance_score(product, criteria)
        candidates.append(product)

    if not candidates:
        return []

    candidates.sort(
        key=lambda p: (
            p.get("_relevance_score", 0),
            p.get("rating") or 0,
            p.get("review_count") or 0,
            -(p.get("effective_max_price") or 0)
        ),
        reverse=True
    )

    return candidates[:number_of_products]

print("[ADIM 3-5] LLM Tabanlı Ürün Önerisi\n")

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
- max_total_budget: Kullanıcının belirttiği maksimum bütçe. Yoksa null.
- number_of_products: İstenen ürün sayısı. Yoksa 1.
- min_rating: "iyi puanlı" → 4, yoksa null.
- category_keywords: Ürün TİPİ kelimeleri (sadece somut kategorieler)
"""

        resp1 = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": parse_prompt}],
            temperature=0,
            max_tokens=300
        )

        criteria_text = resp1.choices[0].message.content.strip()

        if "```" in criteria_text:
            criteria_text = criteria_text.split("```")[1].replace("json", "").strip()

        criteria = json.loads(criteria_text)

        query_lower = query.lower()
        stock_phrases = ["stokta olsun", "stokta olmalı", "stokta bulunan", "in stock"]
        require_in_stock = any(phrase in query_lower for phrase in stock_phrases)
        criteria["require_in_stock"] = require_in_stock

        criteria["number_of_products"] = int(criteria.get("number_of_products", 1))
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

        print("📋 Çıkarılan Kriterler:")
        print(f"   • Bütçe: ${criteria.get('max_total_budget') or 'Sınırsız'}")
        print(f"   • Ürün Sayısı: {criteria.get('number_of_products', 1)}")
        print(f"   • Min Rating: {criteria.get('min_rating') or 'Yok'}")
        print(f"   • Stokta Olması: {'Evet' if criteria.get('require_in_stock') else 'Hayır'}")
        print(f"   • Anahtar Kelimeler: {criteria.get('category_keywords', [])}\n")

        candidates = select_candidates(products, criteria)
        print(f"✅ {len(candidates)} aday seçildi\n")

        result = {
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "extracted_criteria": criteria,
            "candidates_evaluated": len(candidates),
            "recommendations": []
        }

        if candidates:
            safe_candidates = [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "price": p["price"],
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

İstenen ürün sayısı: {criteria['number_of_products']} adet

Aday ürünler:
{json.dumps(safe_candidates, ensure_ascii=False, indent=2)}

GÖREV:
Bu ürünler içinden tam olarak {criteria['number_of_products']} tanesini seç.
Her biri için kısa Türkçe gerekçe yaz.

YANIT (sadece JSON):
{{"recommendations": [{{"id": "...", "reason": "..."}}]}}
"""

            resp2 = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": rec_prompt}],
                temperature=0.2,
                max_tokens=400
            )

            recs_text = resp2.choices[0].message.content.strip()

            if "```" in recs_text:
                recs_text = recs_text.split("```")[1].replace("json", "").strip()

            recs = json.loads(recs_text)
            candidate_map = {c["id"]: c for c in candidates}

            selected_ids = set()
            for rec in recs.get("recommendations", []):
                pid = rec.get("id")
                if pid not in candidate_map:
                    continue
                if pid in selected_ids:
                    continue
                if len(result["recommendations"]) >= criteria["number_of_products"]:
                    break
                selected_ids.add(pid)
                p = candidate_map[pid]

                result["recommendations"].append({
                    "id": p["id"],
                    "title": p["name"],
                    "price": float(p["price"]),
                    "currency": p["currency"],
                    "url": p["url"],
                    "stock_status": p["stock_status"],
                    "rating": p["rating"],
                    "review_count": p["review_count"],
                    "reason": rec.get("reason", "")
                })

            if len(result["recommendations"]) > 1:
                total_price = sum(r["price"] for r in result["recommendations"])
                result["total_basket_price"] = total_price
                if criteria.get("max_total_budget"):
                    result["budget_remaining"] = criteria["max_total_budget"] - total_price

        all_results.append(result)

        output_path = OUTPUT_DIR / f"test_{i}.json"
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        print("📊 Öneriler:")
        if not result["recommendations"]:
            print("   ⚠️ Uygun ürün bulunamadı.")
        for j, rec in enumerate(result["recommendations"], 1):
            print(f"  {j}. [{rec['id']}] {rec['title']} - ${rec['price']:.2f}")
            print(f"     URL: {rec['url']}")
            print(f"     Gerekçe: {rec['reason']}")

        print(f"✅ Kaydedildi: {output_path}\n")

    except Exception as e:
        print(f"❌ Hata: {e}\n")
        result = {
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recommendations": [],
            "error": str(e)
        }
        all_results.append(result)
        output_path = OUTPUT_DIR / f"test_{i}.json"
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print("\n" + "=" * 80)
print("ÖZET SONUÇLAR")
print("=" * 80)

for result in all_results:
    print(f"\n📝 Talep: {result['query']}")
    print(f"⏰ Zaman: {result['timestamp']}")
    if result.get("error"):
        print(f"❌ Hata: {result['error']}")
    else:
        print(f"✅ Önerilen ürün sayısı: {len(result['recommendations'])}")
        for rec in result["recommendations"]:
            print(f"   - [{rec['id']}] {rec['title']} (${rec['price']:.2f})")
