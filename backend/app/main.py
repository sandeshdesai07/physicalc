# backend/app/main.py
import os
import re
import ast
import asyncio
from datetime import datetime
from urllib.parse import quote_plus
from typing import Optional, Dict, Any

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine, text

from app.utils.safe_eval import safe_eval
from app.utils.parser import extract_vars

# ----- App init -----
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-vercel-domain.vercel.app", "http://localhost:3000"],  # during testing; replace with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Config -----
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
POSTGRES_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://physic_user:physic_pass@postgres:5432/physic_db"
)

# ----- DB clients -----
mongo_client = AsyncIOMotorClient(MONGO_URI)
mongo_db = mongo_client["physicalc"]

pg_engine = create_engine(POSTGRES_URI, echo=False, future=True)

# ----- Models -----
class AskIn(BaseModel):
    user_id: int = 0
    text: str

# ----- Helpers -----
def _tokenize_and_ngrams(text: str):
    # keep only letters and spaces, lowercase
    toks = [t for t in re.findall(r"[a-zA-Z]+", text.lower()) if len(t) > 1]
    ngrams = []
    for n in (3, 2, 1):
        for i in range(max(0, len(toks) - n + 1)):
            ngrams.append(" ".join(toks[i : i + n]))
    # dedupe preserve order
    seen = set()
    out = []
    for g in ngrams:
        if g not in seen:
            seen.add(g)
            out.append(g)
    return out

def _pg_lookup_sync(search_text: str) -> Optional[Dict[str, Any]]:
    """
    Synchronous Postgres lookup. Intended to run in a thread via asyncio.to_thread.
    Tries whole phrase first, then n-grams.
    """
    try:
        with pg_engine.connect() as conn:
            if search_text:
                q = text(
                    "SELECT id, name, expression, units, description FROM formulas "
                    "WHERE name ILIKE :q OR description ILIKE :q LIMIT 1"
                )
                res = conn.execute(q, {"q": f"%{search_text}%"}).fetchone()
                if res:
                    return {"id": res[0], "name": res[1], "expression": res[2], "units": res[3], "description": res[4]}

            # fallback via ngrams
            ngrams = _tokenize_and_ngrams(search_text)
            for g in ngrams:
                q2 = text(
                    "SELECT id, name, expression, units, description FROM formulas "
                    "WHERE name ILIKE :q OR description ILIKE :q LIMIT 1"
                )
                res2 = conn.execute(q2, {"q": f"%{g}%"}).fetchone()
                if res2:
                    return {"id": res2[0], "name": res2[1], "expression": res2[2], "units": res2[3], "description": res2[4]}
    except Exception as e:
        print("Postgres lookup error:", e)
    return None

def _crossref_lookup_sync(query: str, rows: int = 3) -> Optional[Dict[str, str]]:
    """
    Synchronous CrossRef lookup (safe to run in a thread). Returns dict with title, doi, url.
    """
    try:
        if not query:
            return None
        safe_q = quote_plus(query)
        url = f"https://api.crossref.org/works?query.title={safe_q}&rows={rows}"
        r = requests.get(url, timeout=6)
        if r.status_code != 200:
            url2 = f"https://api.crossref.org/works?query={safe_q}&rows={rows}"
            r = requests.get(url2, timeout=6)
            if r.status_code != 200:
                return None
        data = r.json().get("message", {}).get("items", [])
        if not data:
            return None
        it = data[0]
        title = " ".join(it.get("title", [])) if it.get("title") else None
        doi = it.get("DOI")
        link = it.get("URL") or (f"https://doi.org/{doi}" if doi else None)
        return {"title": title, "doi": doi, "url": link}
    except Exception as e:
        print("CrossRef lookup error:", e)
        return None

async def crossref_lookup(query: str) -> Optional[Dict[str, str]]:
    return await asyncio.to_thread(_crossref_lookup_sync, query)

# ----- Health -----
@app.get("/health")
def health():
    try:
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        return {"status": "db_error", "error": str(e)}
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# ----- Ask handler -----
@app.post("/api/ask")
async def ask(payload: AskIn):
    # Base doc
    doc = {
        "user_id": payload.user_id,
        "text": payload.text,
        "parsed": None,
        "answer": None,
        "source": None,
        "timestamp": datetime.utcnow()
    }

    # Parse variables
    vars_found = extract_vars(payload.text or "")
    doc["parsed"] = vars_found

    # Prepare cleaned search text (strip numbers/units to focus on keywords)
    raw = (payload.text or "").lower()
    clean = re.sub(r'[-+]?\d*\.?\d+\s*(kg|kilograms|m/s|m s-1|m s\^-1|m|s|meters|meter|seconds|sec)\b', ' ', raw)
    clean = re.sub(r'[^a-z\s]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    search_text = clean if clean else raw

    # Run Postgres lookup in a thread (non-blocking)
    match = await asyncio.to_thread(_pg_lookup_sync, search_text)

    # Compute/answer
    answer = None
    source = None

    if match:
        expr = match.get("expression")
        try:
            parsed_ast = ast.parse(expr, mode="eval")
            varnames = {n.id for n in ast.walk(parsed_ast) if isinstance(n, ast.Name)}

            if varnames and varnames.issubset(set(vars_found.keys())):
                # evaluate in a thread-safe way
                val = await asyncio.to_thread(safe_eval, expr, vars_found)
                answer = float(val)
                # try CrossRef to attach a source (in background)
                src = await crossref_lookup(match.get("name") or match.get("description") or "")
                source = {
                    "title": src.get("title") if src else match.get("name"),
                    "description": match.get("description"),
                    "url": src.get("url") if src else None,
                    "doi": src.get("doi") if src else None,
                    "formula_id": int(match.get("id"))
                }
            else:
                answer = "need_more_vars"
        except Exception as exc:
            print("Evaluation error:", exc)
            answer = "error"
    else:
        answer = "no_formula_found"

    # store and return
    doc["answer"] = answer if not isinstance(answer, float) else {"value": answer}
    doc["source"] = source

    insert_res = await mongo_db.queries.insert_one(doc)
    return {"query_id": str(insert_res.inserted_id), "answer": doc["answer"], "source": source}
