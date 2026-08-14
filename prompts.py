# -*- coding: utf-8 -*-

"""
E-Trink Global - Prompts & Agent Instructions
Sistem Prompt'ları, LLM Talimatları ve Dinamik Template'ler
"""

# ============================================================================
# SISTEM PROMPT (System Message)
# ============================================================================

SYSTEM_PROMPT = """
Siz, Alfiq Copper (bakır ürünleri uzmanlaşmış) e-commerce platformu için 
Expert AI Product Recommendation Agent'siniz.

GÖREV:
Müşteri taleplerini analiz edin, teknik filtreleme kriterlerini çıkarın 
(bütçe, stok, rating, anahtar kelimeler) ve katalogdan en uygun ürünleri seçin.

KURALLAR:
1. ✅ Yalnızca verilen aday ürünler listesinden seçim yapın.
2. ✅ Kullanıcının istediği ürün sayısını kesinlikle saygıyla karşılayın.
3. ✅ Her ürün için açık, doğal Türkçe gerekçe yazın.
4. ✅ Kesinlikle geçerli JSON döndürün: {"recommendations": [{"id": "...", "reason": "..."}]}
5. ❌ Kataloğa olmayan ürün uydurma
6. ❌ Ürün özelliklerini hayali olarak değiştirme
7. ❌ Stok durumu veya bütçe ile oynamama

YANIT FORMATI:
Sadece JSON, başka metin ekleme.
""".strip()

# ============================================================================
# ADIM 1: KRİTER AYIKLAMA PROMPT'U (Parse User Intent)
# ============================================================================

PARSE_INTENT_PROMPT = """
Kullanıcı Talebi:
"{user_query}"

GÖREV:
Bu talep üzerinden aşağıdaki kriterleri çıkar ve JSON olarak döndür.

Çıkacak JSON Şeması:
{{
    "max_total_budget": <sayı veya null>,
    "number_of_products": <1-10 sayısı>,
    "min_rating": <1-5 veya null>,
    "category_keywords": [<ürün tipi kelimeleri>]
}}

KURALLAR:

1. max_total_budget:
   - Kullanıcı parasal bir sınır belirtmişse o rakamı yaz.
   - Belirtmemişse null.
   - Ör: "100 dolar altında" → 100, "sınırsız" → null

2. number_of_products:
   - Kullanıcı kaç ürün istiyorsa o sayıyı yaz.
   - Belirtmemişse 1.
   - Ör: "2 ürün öner" → 2, "Bir ürün bul" → 1

3. min_rating:
   - "iyi puanlı", "yüksek rated" vs → 4 yaz
   - "orta", "makul" vs → 3 yaz
   - Belirtmemişse null
   - Ör: "iyi puanlı" → 4.0

4. category_keywords:
   - Ürün **tipi** veya **kullanım amacı** ile ilgili kelimeler
   - Sadece somut kategori kelimeleri, soyut sıfatlar DEĞİL
   
   ✅ DOĞRU ÖRNEKLER:
   - Hediye talesi → ["bakır", "el yapımı", "dekoratif"]
   - Spa için → ["spa", "masaj", "sauna", "terapi", "wellness"]
   - Kahve için → ["kahve", "cezve", "turk kahvesi", "coffee"]
   - Ev dekorasyon → ["pot", "bowl", "vase", "decor", "su şişesi"]
   
   ❌ YANLIŞ ÖRNEKLER:
   - "hediye" (çok soyut)
   - "gift" (çok genel)
   - "premium" (sadece sıfat)
   - "kaliteli" (nitelik, kategori değil)

ÇIKTI:
Sadece JSON döndür, başka yazı yazmama.
""".strip()

# ============================================================================
# ADIM 2: ÜRÜN SEÇİMİ & GEREKÇE PROMPT'U (Recommendations)
# ============================================================================

RECOMMENDATION_PROMPT = """
Kullanıcı Talebi:
"{user_query}"

Ekstakte Edilen Kriterler:
- Bütçe: ${budget} (null = sınırsız)
- İstenen Ürün Sayısı: {quantity} adet
- Minimum Rating: {min_rating} (null = sınır yok)
- Stokta Olması: {"Evet" if require_in_stock else "Hayır"}

Katalogdan Seçilmiş Aday Ürünler:
{candidates_json}

GÖREV:
1. Bu ürünler arasından kullanıcı talebine en uygun {quantity} tanesini seç.
2. Her seçim için kısa, açık Türkçe gerekçe yaz.
3. Ürün özelliklerini katalogda yazılı olandan başka şekilde anlatma.
4. Kullanıcının istediği sayıyı kesinlikle karşılayacak kadar ürün seç.

Kritik Kurallar:
✅ Sadece verilen ürünlerden seç.
✅ Şu kadarını seç: {quantity} adet (az veya fazla olmasın).
✅ Bütçe uygunluğunu göz önünde tut.
✅ Gerekçede katalogta yazılı olmayan özellikler yazma.
❌ Hallucination yapmama.

YANIT FORMATINI:
{{
    "recommendations": [
        {{
            "id": "PRODUCT_ID",
            "reason": "Kısa, anlaşılır Türkçe gerekçe..."
        }}
    ]
}}

Sadece JSON döndür.
""".strip()

# ============================================================================
# TEST EXAMPLES
# ============================================================================

TEST_EXAMPLES = {
    "test_1": {
        "query": "100 dolar altında, iyi puanlı, hediyelik bir ürün öner",
        "expected_criteria": {
            "max_total_budget": 100.0,
            "number_of_products": 1,
            "min_rating": 4.0,
            "category_keywords": ["handcrafted", "decorative", "copper", "gift"]
        }
    },
    "test_2": {
        "query": "Bir spa işletmesi için 300 dolar bütçeyle 2 ürün öner",
        "expected_criteria": {
            "max_total_budget": 300.0,
            "number_of_products": 2,
            "min_rating": None,
            "category_keywords": ["spa", "massage", "wellness", "sauna"]
        }
    },
    "test_3": {
        "query": "Türk kahvesi seven birine hediye arıyorum, stokta olsun",
        "expected_criteria": {
            "max_total_budget": None,
            "number_of_products": 1,
            "min_rating": None,
            "category_keywords": ["kahve", "cezve", "coffee", "turkish"]
        }
    }
}

# ============================================================================
# AGENT TALIMATLARI
# ============================================================================

AGENT_INSTRUCTIONS = """
Agent Eğitim Talimatları (Code Seviyesinde Uygulanacak)
=====================================================

1. OUTPUT VALIDATION (Çıktı Doğrulama)
   - LLM'den gelen JSON'u parse et
   - Dönen "id" değerleri aday listede mevcut mi kontrol et
   - Hallucination (uydurma) filtresi koy
   
2. QUANTITY CONTROL (Sayı Kontrolü)
   - LLM kaç ürün dönerse, istenen sayıyı aşmayacak şekilde kes
   - Ör: İstenen 2, LLM 3 dönerse → ilk 2'sini al
   
3. GUARDRAILS (İşletim Kuralları)
   - Stok kuralı: Kullanıcı stok istiyorsa, sadece "in_stock" olanları göster
   - Bütçe kuralı: Her ürün bütçeyi aşmayacak şekilde filtrele
   - Rating kuralı: Min rating belirtilmişse altındaki ürünleri reddet
   
4. ERROR HANDLING (Hata Yönetimi)
   - LLM parse hatası → fallback ürün listesinden seç
   - Aday yok → "Uygun ürün bulunamadı" mesajı dön
   - Geçersiz JSON → Tekrar sor veya manuel seçim yap
   
5. LOGGING & DEBUG (Hata Ayıklama)
   - Her aşamada neyin yapıldığını konsola yazdır
   - Aday sayısı
   - LLM'den gelen raw yanıt
   - Dönen final ürünler
"""
