import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup

# ============ AYARLAR ============
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Takip etmek istedigin urunler (burayi duzenle)
TAKIP_LISTESI = [
    "iphone 16 128gb",
    "dyson v15",
    "playstation 5 slim",
    "philips airfryer",
]

MAX_FIRSAT = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile Safari/604.1",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# ============ AKAKCE ARAMA ============
def akakce_ara(query):
    url = "https://www.akakce.com/arama/?q=" + requests.utils.quote(query)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"[!] {query} icin baglanti hatasi: {e}")
        return []

    urunler = []
    for li in soup.select("li.p_w")[:3]:
        try:
            baslik = li.select_one("h3").get_text(strip=True)
            fiyat_txt = li.select_one(".pt_v8").get_text(strip=True)
            fiyat = float(
                fiyat_txt.replace("TL", "").replace(".", "").replace(",", ".").strip()
            )
            link = li.select_one("a")["href"]
            if link.startswith("/"):
                link = "https://www.akakce.com" + link
            urunler.append({"baslik": baslik, "fiyat": fiyat, "link": link})
        except Exception:
            continue
    return urunler

# ============ SINIFLANDIRMA ============
def siniflandir(fiyat, gecmis):
    if not gecmis:
        return "🟡 Normal Indirim", 0.0

    ort = sum(gecmis) / len(gecmis)
    min_g = min(gecmis)
    sapma = ((fiyat - ort) / ort) * 100

    if fiyat <= min_g * 1.02 or sapma <= -25:
        return "🔥 Gercek Firsat", sapma
    if sapma <= -15:
        return "🟢 Iyi Fiyat", sapma
    if sapma <= -5:
        return "🟡 Normal Indirim", sapma
    return "🔴 Dikkat", sapma

# ============ TELEGRAM GONDERIM ============
def telegram_gonder(metin):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Telegram bilgileri eksik!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": metin,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }, timeout=20)
    print(f"[+] Telegram gonderim durumu: {r.status_code}")

# ============ ANA DONGU ============
def main():
    tum_firsatlar = []

    for sorgu in TAKIP_LISTESI:
        print(f"[+] Taraniyor: {sorgu}")
        urunler = akakce_ara(sorgu)

        for u in urunler:
            # Simdilik fiyat gecmisi bos; ileride eklenecek
            etiket, sapma = siniflandir(u["fiyat"], [])
            tum_firsatlar.append({
                "baslik": u["baslik"],
                "fiyat": u["fiyat"],
                "link": u["link"],
                "etiket": etiket,
                "sapma": round(sapma, 1),
            })

        time.sleep(2)

    # Oncelik sirasina gore sirala
    oncelik = {
        "🔥 Gercek Firsat": 0,
        "🟢 Iyi Fiyat": 1,
        "🟡 Normal Indirim": 2,
        "🔴 Dikkat": 3,
    }
    tum_firsatlar.sort(key=lambda x: oncelik.get(x["etiket"], 9))

    secilenler = tum_firsatlar[:MAX_FIRSAT]

    if not secilenler:
        telegram_gonder("Bugun guclu firsat bulunamadi.")
        return

    satirlar = ["<b>🛒 Gunun Firsatlari</b>\n"]
    for i, f in enumerate(secilenler, 1):
        satirlar.append(
            f"{i}. {f['etiket']} <b>{f['baslik'][:70]}</b>\n"
            f"   Fiyat: {f['fiyat']} TL\n"
            f"   {f['link']}\n"
        )

    rapor = "\n".join(satirlar)
    print(rapor)
    telegram_gonder(rapor)

if __name__ == "__main__":
    main()
