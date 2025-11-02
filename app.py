import os, re
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg
from psycopg.rows import dict_row
import httpx

load_dotenv()

PORT = int(os.getenv("PORT", "8080"))
DATABASE_URL = os.getenv("DATABASE_URL")
MEILI_HOST = os.getenv("MEILI_HOST")
MEILI_KEY = os.getenv("MEILI_KEY")
MEILI_INDEX = os.getenv("MEILI_INDEX", "civil-articles")

app = FastAPI(title="Civil Code Search API", version="1.0.0")

# CORS
origins = [o.strip() for o in os.getenv("CORS_ORIGINS","").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def pad_jo_code_from_article(article_no: int, sub_no: int = 0) -> str:
    return f"{int(article_no):04d}{int(sub_no):02d}"

def looks_numeric(s: str) -> bool:
    return bool(re.fullmatch(r"\d{1,4}$", s))

@app.get("/health")
async def health():
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1;").fetchone()
    except Exception as e:
        return {"ok": False, "db": str(e)}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{MEILI_HOST}/health")
            if r.status_code != 200:
                return {"ok": False, "meili": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "meili": str(e)}

    return {"ok": True}

@app.get("/articles/by-jo/{jo_code}")
def get_by_jo(jo_code: str):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT article_no, article_sub_no, jo_code, heading, body,
                   COALESCE(clauses_json, '[]'::jsonb) AS clauses
            FROM article WHERE jo_code = %s LIMIT 1;
            """,
            (jo_code,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        return row

@app.get("/articles/{article_no}")
def get_article(article_no: int, sub_no: int = 0):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT article_no, article_sub_no, jo_code, heading, body,
                   COALESCE(clauses_json, '[]'::jsonb) AS clauses
            FROM article WHERE article_no = %s AND article_sub_no = %s LIMIT 1;
            """,
            (article_no, sub_no)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        return row

@app.get("/search")
async def search(
    q: str = Query(..., description="검색어(숫자면 조번호, 아니면 키워드)"),
    limit: int = Query(10, ge=1, le=50)
):
    q = q.strip()
    if not q:
        raise HTTPException(400, "empty query")

    if looks_numeric(q):
        article_no = int(q)
        jo_exact = pad_jo_code_from_article(article_no, 0)

        with get_conn() as conn:
            exact = conn.execute(
                """
                SELECT article_no, article_sub_no, jo_code, heading,
                       LEFT(COALESCE(body,''), 500) AS snippet
                FROM article WHERE jo_code = %s LIMIT 1;
                """,
                (jo_exact,)
            ).fetchall()

            prefix = conn.execute(
                """
                SELECT article_no, article_sub_no, jo_code, heading,
                       LEFT(COALESCE(body,''), 500) AS snippet
                FROM article
                WHERE CAST(article_no AS TEXT) LIKE %s
                ORDER BY article_no ASC, article_sub_no ASC
                LIMIT %s;
                """,
                (f"{article_no}%", limit)
            ).fetchall()

        seen = set()
        merged = []
        for r in (exact + prefix):
            if r["jo_code"] in seen:
                continue
            seen.add(r["jo_code"])
            merged.append(r)

        return {
            "query": q,
            "mode": "numeric",
            "total": len(merged),
            "hits": merged[:limit]
        }

    payload = {"q": q, "limit": limit}
    headers = {"Authorization": f"Bearer {MEILI_KEY}"}

    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.post(
            f"{MEILI_HOST}/indexes/{MEILI_INDEX}/search", headers=headers, json=payload
        )
        if r.status_code != 200:
            raise HTTPException(502, f"Meili error {r.status_code}: {r.text}")
        data = r.json()

    hits = []
    for h in data.get("hits", []):
        hits.append({
            "article_no": h.get("articleNo"),
            "article_sub_no": h.get("articleSubNo"),
            "jo_code": h.get("joCode"),
            "heading": h.get("heading"),
            "snippet": (h.get("body") or "")[:500]
        })

    return {
        "query": q,
        "mode": "keyword",
        "estimatedTotalHits": data.get("estimatedTotalHits", len(hits)),
        "hits": hits
    }
