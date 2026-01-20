# AI Coding Agent Instructions - DealScout

## Project Overview
DealScout is a hackathon demo application that compares product deals across Indian e-commerce platforms (Amazon, Flipkart, Meesho). It combines visual product search (image embeddings via ResNet18) with web scraping.

**Architecture**: FastAPI backend (port 8000) + Vite React frontend (port 5173). Backend returns `SearchResponse` with `ProductResult` objects containing normalized price/offer data across platforms.

## Critical Development Workflows

### Backend Setup & Execution
```bash
cd backend
python -m venv venv; .\venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
Backend auto-loads product embeddings on startup (10-15s). API docs at `http://localhost:8000/docs`.

### Frontend Setup & Execution
```bash
cd frontend
npm install
npm run dev  # Runs on http://localhost:5173
```
Frontend is environment-agnostic but hardcoded to call `http://localhost:8000` (see [App.jsx](frontend/src/App.jsx#L2)).

### Debugging Common Issues
- **Embedding load failures**: Individual product image fetch errors are caught and replaced with random embeddings. Check [app.py](backend/app.py#L103-L113).
- **CORS errors**: Currently permissive (`allow_origins=["*"]`); lock down to `["http://localhost:5173"]` before deployment.
- **Render deployment**: Uses [render.yaml](backend/render.yaml) (backend only). Frontend requires separate hosting.

## Key Architectural Patterns

### Image Search Pipeline
1. **Upload image** → `POST /search/image` (FormData with `file` + `session_id`)
2. **Embed query**: ResNet18 preprocesses (resize 224×224, normalize) → 512-dim vector (L2 normalized)
3. **Similarity search**: Cosine similarity against precomputed `PRODUCT_EMBS` (numpy array)
4. **Return top-4**: `enrich_products()` adds pricing aggregation (min/max/best platform)

See [app.py lines 70-150](backend/app.py#L70-L150) for embedding initialization and search logic.

### Link Scraping Flow
1. **Parse URL** → `detect_platform()` identifies Amazon/Flipkart/Meesho
2. **Call scraper**: Synchronous calls to `scrape_amazon()`, `scrape_flipkart()`, `scrape_meesho()`
3. **Normalize output**: All scrapers return `{platform, title, price, image, url}`
4. **Format response**: Single-offer `ProductResult` wrapped in `SearchResponse`

**Important**: Scrapers are demo stubs returning hardcoded data (e.g., [scrapers/amazon.py](backend/scrapers/amazon.py)). Upgrade with real Playwright scraping for production.

### Data Models
- `ProductResult`: product_id, title, image_url, offers (list), lowest_price, highest_price, best_platform
- `Offer`: platform, price, url
- Session history stored in-memory dict `HISTORY[session_id]` (capped at 10 entries)

See [app.py lines 50-62](backend/app.py#L50-L62) for Pydantic models.

## Project-Specific Conventions

### File Organization
- **[catalog.py](backend/catalog.py)**: Hardcoded product list (5 items). Add new products here with `offers` array spanning multiple platforms.
- **[scrapers/](backend/scrapers/)**: Each platform (amazon, flipkart, meesho) gets its own module. Follow stub pattern.
- **Frontend entry**: [main.jsx](frontend/src/main.jsx) → [App.jsx](frontend/src/App.jsx) (no routing; single-page demo).

### Code Patterns
- **Error handling**: Silently fallback (e.g., bad image fetch → random embedding). Log via `print()`.
- **Threading**: Scrapers run sync; no async/await in scraper code (wrap with `ThreadPoolExecutor` if parallelizing).
- **Testing**: None. This is demo-grade; unit tests are aspirational.

## Integration Points & Dependencies

### Backend Dependencies
- **torch + torchvision**: Image embeddings (ResNet18, ~200MB model)
- **FastAPI + uvicorn**: Web server
- **requests**: Fetch catalog images at startup + eventual scraping
- **Pillow**: Image preprocessing

### Frontend Dependencies
- **React 19.2**: UI framework (minimal, no state management)
- **Vite 7.2**: Build tool; config is standard ([vite.config.js](frontend/vite.config.js))

### API Contract
| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/search/image` | POST | FormData: file, session_id | `SearchResponse(query_type="image", results=[...])` |
| `/search/link` | POST | JSON: {url, session_id} | `SearchResponse(query_type="link", results=[...])` |
| `/history` | GET | Query: session_id | `HistoryResponse(session_id, history=[])` |
| `/` | GET | — | `{status, message}` |

## Common Modifications

**Add a new platform scraper**: 
1. Create [scrapers/newplatform.py](backend/scrapers/) with `scrape_newplatform(url: str) -> dict` returning `{platform, title, price, image, url}`
2. Import in [app.py](backend/app.py#L18)
3. Add platform name to `detect_platform()` and `/search/link` logic

**Update catalog**: Edit [catalog.py](backend/catalog.py) PRODUCTS list. Ensure each product has `id`, `title`, `category`, `image_url`, `offers` (with platform, price, url).

**Change embedding model**: Replace ResNet18 with another torchvision model in [app.py lines 74-76](backend/app.py#L74-L76). Adjust preprocessing if needed.

**Frontend API endpoint**: Update `API_BASE` in [App.jsx line 2](frontend/src/App.jsx#L2).
