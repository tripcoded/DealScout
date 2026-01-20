import requests
from bs4 import BeautifulSoup
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_flipkart(url: str) -> dict:
    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.select_one("span.B_NuCI")
    title = title.get_text(strip=True) if title else "Flipkart Product"

    price_el = soup.select_one("div._30jeq3")
    price = re.sub(r"[^\d]", "", price_el.text) if price_el else "0"

    img = soup.select_one("img._396cs4")
    image = img["src"] if img else ""

    return {
        "platform": "Flipkart",
        "url": url,
        "title": title,
        "price": float(price),
        "image": image,
    }
