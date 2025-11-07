"""
법령 검색 시스템 API 서버 (멀티-법령 지원)

민법 + 형법 통합 검색 시스템
- PostgreSQL: 정본 저장소
- Meilisearch: 전문 검색 엔진 (2개 인덱스)
- OAuth: Google, Naver 로그인
- JWT: 인증 토큰
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.routers import laws, search, articles, auth, users, bookmarks
from app.database import health_check_db
from app.services.search_service import health_check_meili
from app.models import HealthResponse

load_dotenv()

# ============================================
# FastAPI 앱 생성
# ============================================

app = FastAPI(
    title="Law Search API",
    description="민법 + 형법 통합 검색 시스템 with OAuth",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================
# Session Middleware (required for OAuth)
# ============================================
SESSION_SECRET = os.getenv("SESSION_SECRET", os.getenv("JWT_SECRET", "your-secret-key-change-in-production"))
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# ============================================
# CORS 설정
# ============================================
def parse_origins(env_value: str):
    """
    'a,b , c/' 같은 입력을
    - 공백 제거
    - 끝의 슬래시 제거
    - http/https 스킴 필수
    로 정리해서 리스트로 반환
    """
    origins = []
    for raw in (env_value or "").split(","):
        o = raw.strip()
        if not o:
            continue
        if o.endswith("/"):
            o = o[:-1]
        if not (o.startswith("http://") or o.startswith("https://")):
            raise ValueError(f"CORS_ORIGINS 값에 스킴이 없어요: {o}")
        origins.append(o)
    return origins

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

origins = parse_origins(CORS_ORIGINS)

# 개발 편의: DEBUG면 로컬 자동 허용
if DEBUG:
    origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])

# 안전장치 1) 비어있을 때 와일드카드 금지(실수 방지)
if not origins:
    raise RuntimeError("CORS_ORIGINS가 비어있어요. 운영에서는 반드시 명시해 주세요.")

# 안전장치 2) credentials=True + '*' 조합 금지
if ALLOW_CREDENTIALS and any(o == "*" for o in origins):
    raise RuntimeError("allow_credentials=True에서는 '*'를 사용할 수 없습니다.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # 환경변수 기반
    allow_credentials=True,           # OAuth와 쿠키를 위해 필수
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # 모든 필요 메서드
    allow_headers=["*"],
)
# ============================================
# 라우터 등록
# ============================================

# Authentication & User routes
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(bookmarks.router)

# Law search routes
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
        "version": "3.0.0",
        "description": "민법 + 형법 통합 검색 시스템 with OAuth",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "auth": {
                "login": "/api/auth/login/{provider}",
                "logout": "/api/auth/logout"
            },
            "users": {
                "me": "/api/users/me"
            },
            "bookmarks": {
                "list": "/api/bookmarks",
                "create": "/api/bookmarks",
                "delete": "/api/bookmarks/{id}"
            },
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
