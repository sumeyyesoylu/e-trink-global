# -*- coding: utf-8 -*-

"""
E-Trink Global - Google Sheets Eksport Modülü
Testlerin sonuçlarını Google Sheets'e yazma
"""

import json
from pathlib import Path
import os

def export_to_sheets(results_dir="outputs", sheet_id=None):
    """
    outputs/ klasöründeki JSON sonuçlarını Google Sheets'e yazır.
    
    Args:
        results_dir (str): Sonuçları içeren klasör
        sheet_id (str): Google Sheet ID
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        print("❌ Google API kütüphaneleri yüklü değil. Kurulum:")
        print("pip install google-auth-httplib2 google-auth-oauthlib")
        return

    if not sheet_id:
        print("⚠️ Sheet ID belirtilmedi. Kullanım:")
        print("python sheets_export.py --sheet-id=YOUR_SHEET_ID")
        return

    # Servis hesabı JSON'ı
    SERVICE_ACCOUNT_FILE = "service-account.json"
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ {SERVICE_ACCOUNT_FILE} bulunamadı!")
        print("1. Google Cloud Console'da Service Account oluştur")
        print("2. JSON anahtarını indir")
        print("3. Dosyayı proje root'una koy")
        return

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)

    # Test JSON'larını oku
    results_path = Path(results_dir)
    test_files = sorted(results_path.glob("test_*.json"))

    all_data = []
    for test_file in test_files:
        with open(test_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_data.append(data)

    # Google Sheets'e yazacak satırları hazırla
    rows = [
        ["Talep", "Bütçe", "İstenen Ürün", "Bütçe Kaldı", "Ürün ID", "Ürün Adı", "Fiyat", "URL", "Gerekçe"]
    ]

    for test_result in all_data:
        query = test_result.get("query", "")
        criteria = test_result.get("extracted_criteria", {})
        budget = criteria.get("budget") or "-"
        quantity = criteria.get("quantity", "-")

        recommendations = test_result.get("recommendations", [])

        if not recommendations:
            rows.append([query, budget, quantity, "-", "-", "-", "-", "-", "Ürün bulunamadı"])
        else:
            for i, rec in enumerate(recommendations):
                budget_remaining = test_result.get("budget_remaining", "-")
                if i > 0:
                    query = ""  # İlk satırdan sonra talep boş bırak
                    budget = ""
                    quantity = ""

                rows.append([
                    query,
                    budget,
                    quantity,
                    budget_remaining,
                    rec.get("id", ""),
                    rec.get("title", ""),
                    rec.get("price", ""),
                    rec.get("url", ""),
                    rec.get("reason", "")
                ])

    # Sheets API'sine gönder
    body = {"values": rows}
    result = service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Sheet1!A1",
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

    print(f"✅ {len(rows)} satır Google Sheets'e yazıldı!")
    print(f"Sheet Link: https://docs.google.com/spreadsheets/d/{sheet_id}")


if __name__ == "__main__":
    import sys

    sheet_id = None
    for arg in sys.argv[1:]:
        if arg.startswith("--sheet-id="):
            sheet_id = arg.split("=")[1]

    export_to_sheets(sheet_id=sheet_id)
