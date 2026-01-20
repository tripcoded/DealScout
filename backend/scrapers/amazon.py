import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-IN,en;q=0.9",
}

def clean_price(text):
    if not text:
        return None
    m = re.findall(r"[\d,]+", text)
    if not m:
        return None
    return float(m[0].replace(",", ""))

def scrape_amazon(url: str) -> dict:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    title = (
        soup.select_one("#productTitle") or
        soup.find("meta", property="og:title")
    )
    title = title.get_text(strip=True) if title else "Amazon Product"

    price = None
    price_el = soup.select_one("span.a-price span.a-offscreen")
    if price_el:
        price = clean_price(price_el.text)

    img = soup.select_one("#landingImage")
    image = img["src"] if img else ""

    return {
        "platform": "Amazon",
        "url": url,
        "title": title,
        "price": price or 0,
        "image": image,
    }
