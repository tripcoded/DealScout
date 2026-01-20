import requests
from bs4 import BeautifulSoup
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_meesho(url: str) -> dict:
    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.find("h1")
    title = title.get_text(strip=True) if title else "Meesho Product"

    price_el = soup.find("h4")
    price = re.sub(r"[^\d]", "", price_el.text) if price_el else "0"

    img = soup.find("img")
    image = img["src"] if img else ""

    return {
        "platform": "Meesho",
        "url": url,
        "title": title,
        "price": float(price),
        "image": image,
    }
