# backend/app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import os
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo.physicalc

class AskIn(BaseModel):
    user_id: int = 0
    text: str

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.post("/api/ask")
async def ask(payload: AskIn):
    q = {
        "user_id": payload.user_id,
        "text": payload.text,
        "parsed": None,
        "timestamp": datetime.utcnow()
    }
    res = await db.queries.insert_one(q)
    return {
        "query_id": str(res.inserted_id),
        "answer": "Placeholder: next step is NLP + lookup."
    }
