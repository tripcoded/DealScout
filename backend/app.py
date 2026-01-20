# backend/app.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from io import BytesIO
from collections import defaultdict

from PIL import Image
import numpy as np
import torch
from torchvision import models, transforms
import requests

from catalog import PRODUCTS
from scrapers.amazon import scrape_amazon
from scrapers.flipkart import scrape_flipkart
from scrapers.meesho import scrape_meesho

# ---------------- APP ----------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MODELS ----------------

class Offer(BaseModel):
    platform: str
    price: float
    url: str

class ProductResult(BaseModel):
    product_id: str
    title: str
    image_url: str
    offers: List[Offer]
    lowest_price: float
    highest_price: float
    best_platform: str

class SearchResponse(BaseModel):
    query_type: str
    results: List[ProductResult]

class LinkSearchRequest(BaseModel):
    url: str
    session_id: str = "anonymous"

class HistoryEntry(BaseModel):
    type: str
    url: str | None = None
    first_product_title: str
    timestamp_index: int

class HistoryResponse(BaseModel):
    session_id: str
    history: List[HistoryEntry]

# ---------------- HISTORY ----------------

HISTORY = defaultdict(list)

# ---------------- IMAGE MODEL ----------------

device = torch.device("cpu")

model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
model.fc = torch.nn.Identity()
model.eval()
model.to(device)

preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

def embed_image(pil_img: Image.Image) -> np.ndarray:
    img_tensor = preprocess(pil_img).unsqueeze(0).to(device)
    with torch.no_grad():
        feats = model(img_tensor).cpu().numpy()[0]
    return feats / (np.linalg.norm(feats) + 1e-8)

def load_product_embeddings():
    embs = []
    for p in PRODUCTS:
        try:
            r = requests.get(p["image_url"], timeout=10)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).convert("RGB")
            embs.append(embed_image(img))
        except Exception:
            embs.append(np.random.randn(512))
    return np.stack(embs, axis=0)

print("Loading product embeddings...")
PRODUCT_EMBS = load_product_embeddings()
print("Loaded", PRODUCT_EMBS.shape[0], "product embeddings.")

def similarity_search(img_bytes: bytes, top_k: int = 4):
    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    q_emb = embed_image(img)
    sims = PRODUCT_EMBS @ q_emb
    idxs = np.argsort(-sims)[:top_k]
    return [PRODUCTS[i] for i in idxs]

def enrich_products(prod_list: List[Dict[str, Any]]) -> List[ProductResult]:
    results = []
    for p in prod_list:
        offers = [Offer(**o) for o in p["offers"]]
        prices = [o.price for o in offers]
        lowest = min(prices)
        highest = max(prices)
        best = min(offers, key=lambda o: o.price).platform
        results.append(ProductResult(
            product_id=p["id"],
            title=p["title"],
            image_url=p["image_url"],
            offers=offers,
            lowest_price=lowest,
            highest_price=highest,
            best_platform=best,
        ))
    return results

# ---------------- HELPERS ----------------

def detect_platform(url: str):
    url = url.lower()
    if "amazon" in url:
        return "amazon"
    if "flipkart" in url:
        return "flipkart"
    if "meesho" in url:
        return "meesho"
    return None

# ---------------- API ----------------

@app.post("/search/image", response_model=SearchResponse)
async def search_image(
    file: UploadFile = File(...),
    session_id: str = Form("anonymous"),
):
    img_bytes = await file.read()
    products = similarity_search(img_bytes)
    enriched = enrich_products(products)

    HISTORY[session_id].append({"type": "image", "products": enriched})
    HISTORY[session_id] = HISTORY[session_id][-10:]

    return SearchResponse(query_type="image", results=enriched)

@app.post("/search/link")
async def search_link(payload: LinkSearchRequest):
    platform = detect_platform(payload.url)

    if platform == "amazon":
        data = scrape_amazon(payload.url)
    elif platform == "flipkart":
        data = scrape_flipkart(payload.url)
    elif platform == "meesho":
        data = scrape_meesho(payload.url)
    else:
        return {"error": "Platform not supported"}

    prod = {
        "product_id": data["url"],
        "title": data.get("title") or "Product",
        "image_url": data.get("image") or "",
        "offers": [{
            "platform": data["platform"],
            "price": float(data.get("price") or 0),
            "url": data["url"],
        }],
        "lowest_price": float(data.get("price") or 0),
        "highest_price": float(data.get("price") or 0),
        "best_platform": data["platform"],
    }

    return {"query_type": "link", "results": [prod]}

@app.get("/history", response_model=HistoryResponse)
async def get_history(session_id: str = "anonymous"):
    items = HISTORY[session_id]
    history = []
    for i, it in enumerate(items):
        title = it["products"][0].title if it["products"] else "Unknown"
        history.append(HistoryEntry(
            type=it["type"],
            url=it.get("url"),
            first_product_title=title,
            timestamp_index=i,
        ))
    return HistoryResponse(session_id=session_id, history=history)

@app.get("/")
async def root():
    return {"status": "ok", "message": "DealScout backend running"}
