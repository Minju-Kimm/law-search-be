"""
법령 검색 시스템 API 서버 (멀티-법령 지원)

민법 + 형법 통합 검색 시스템
- PostgreSQL: 정본 저장소
- Meilisearch: 전문 검색 엔진 (2개 인덱스)
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import laws, search, articles
from app.database import health_check_db
from app.services.search_service import health_check_meili
from app.models import HealthResponse

load_dotenv()

# ============================================
# FastAPI 앱 생성
# ============================================

app = FastAPI(
    title="Law Search API",
    description="민법 + 형법 통합 검색 시스템",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================
# CORS 설정
# ============================================

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

# ============================================
# 라우터 등록
# ============================================

app.include_router(laws.router)
app.include_router(search.router)
app.include_router(articles.router)


# ============================================
# 헬스체크 엔드포인트
# ============================================

@app.get("/health", response_model=HealthResponse)
async def health():
    """
    서비스 헬스체크

    - PostgreSQL 연결 상태
    - Meilisearch 연결 상태
    """
    errors = {}

    # DB 체크
    try:
        health_check_db()
    except Exception as e:
        errors["db"] = str(e)

    # Meilisearch 체크
    try:
        await health_check_meili()
    except Exception as e:
        errors["meili"] = str(e)

    if errors:
        return HealthResponse(ok=False, **errors)

    return HealthResponse(ok=True)


# ============================================
# 루트 엔드포인트
# ============================================

@app.get("/")
def root():
    """
    API 루트 엔드포인트
    """
    return {
        "service": "Law Search API",
        "version": "2.0.0",
        "description": "민법 + 형법 통합 검색 시스템",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "laws": "/laws",
            "search": "/search?q={query}&scope={all|civil|criminal}",
            "article": "/articles/{lawCode}/{articleNo}[/{articleSubNo}]"
        }
    }


# ============================================
# 서버 실행 (개발 모드)
# ============================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
