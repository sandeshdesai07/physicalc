# backend/app/main.py
import os
import re
import ast
from datetime import datetime

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
    allow_origins=["http://localhost:3000"],
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
    vars_found = extract_vars(payload.text)
    doc["parsed"] = vars_found

    # ---------- Lookup (token-by-token) ----------
    match = None
    raw = (payload.text or "").lower()

    # remove numbers and common units to keep keywords
    clean = re.sub(r'[-+]?\d*\.?\d+\s*(kg|kilograms|m/s|m s-1|m s\^-1|m|s|meters|meter|seconds|sec)\b', ' ', raw)
    clean = re.sub(r'[^a-z\s]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    search_text = clean if clean else raw
    #print("DEBUG search_text:", repr(search_text))

    tokens = [t for t in search_text.split() if len(t) > 2]
    if not tokens:
        tokens = [t for t in raw.split() if len(t) > 2]

    try:
        with pg_engine.connect() as conn:
            # Try whole cleaned phrase first
            if search_text:
                q = text(
                    "SELECT id, name, expression, units, description FROM formulas "
                    "WHERE name ILIKE :q OR description ILIKE :q LIMIT 1"
                )
                res = conn.execute(q, {"q": f"%{search_text}%"}).fetchone()
                if res:
                    match = {"id": res[0], "name": res[1], "expression": res[2], "units": res[3], "description": res[4]}
                    print("DEBUG matched phrase:", match["name"])
            # If not found, try tokens one-by-one
            if not match and tokens:
                for tok in tokens:
                    q = text(
                        "SELECT id, name, expression, units, description FROM formulas "
                        "WHERE name ILIKE :tok OR description ILIKE :tok LIMIT 1"
                    )
                    res = conn.execute(q, {"tok": f"%{tok}%"}).fetchone()
                    if res:
                        match = {"id": res[0], "name": res[1], "expression": res[2], "units": res[3], "description": res[4]}
                        print("DEBUG matched token:", tok, "->", match["name"])
                        break
    except Exception as e:
        print("Postgres lookup error:", e)

    # ---------- Compute / result ----------
    answer = None
    source = None

    if match:
        expr = match.get("expression")
        try:
            parsed_ast = ast.parse(expr, mode="eval")
            varnames = {n.id for n in ast.walk(parsed_ast) if isinstance(n, ast.Name)}

            if varnames and varnames.issubset(set(vars_found.keys())):
                val = safe_eval(expr, vars_found)
                answer = float(val)
                source = {
                    "title": match.get("name"),
                    "description": match.get("description"),
                    "url": None,
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
