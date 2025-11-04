# 법령 검색 시스템 API (Law Search API)

민법 + 형법 통합 검색 시스템 백엔드

## 📋 목차

- [개요](#개요)
- [기술 스택](#기술-스택)
- [프로젝트 구조](#프로젝트-구조)
- [환경 설정](#환경-설정)
- [API 명세](#api-명세)
- [개발 가이드](#개발-가이드)

---

## 개요

**민법**과 **형법** 조문을 통합 검색할 수 있는 RESTful API 서버입니다.

### 주요 기능

- ✅ **통합/법령별 검색**: 민법+형법 통합 검색 또는 개별 법령 검색
- ✅ **조문 상세 조회**: PostgreSQL 정본 데이터 제공 (항/호/목 구조화)
- ✅ **법령 목록 조회**: 지원하는 법령 코드 목록 제공
- ✅ **헬스체크**: DB + Meilisearch 연결 상태 확인

### 아키텍처

```
PostgreSQL (정본 저장소)
    ↓
FastAPI 서버 ←→ Meilisearch (전문 검색)
    ↓              - civil-articles (민법)
  API             - criminal-articles (형법)
```

---

## 기술 스택

| 분류 | 기술 |
|-----|------|
| **언어** | Python 3.12 |
| **웹 프레임워크** | FastAPI 0.115.2 |
| **서버** | Uvicorn 0.30.6 |
| **데이터베이스** | PostgreSQL 16 |
| **검색 엔진** | Meilisearch v1.8 |
| **DB 어댑터** | psycopg 3.2.3 |
| **HTTP 클라이언트** | httpx 0.27.2 |
| **데이터 검증** | Pydantic 2.9.2 |
| **인프라** | Docker, Docker Compose, Caddy 2 |

---

## 프로젝트 구조

```
law-search-be/
├── app/
│   ├── main.py              # FastAPI 앱 진입점
│   ├── models.py            # Pydantic 모델 (요청/응답)
│   ├── database.py          # PostgreSQL 접근 레이어
│   ├── routes/              # API 라우터
│   │   ├── laws.py          # 법령 목록 API
│   │   ├── search.py        # 검색 API
│   │   └── articles.py      # 조문 상세 API
│   └── services/
│       └── search_service.py # Meilisearch 통합 검색 서비스
├── db/
│   └── init/
│       └── 01_schema.sql    # DB 스키마 (자동 실행)
├── docker-compose.yml       # 멀티 서비스 구성
├── Dockerfile               # API 서버 이미지
├── requirements.txt         # Python 패키지
├── .env.example             # 환경변수 예시
└── README.md
```

---

## 환경 설정

### 1️⃣ 필수 환경변수

서버 배포 환경에 다음 변수를 설정하세요:

```bash
# 서버 포트
PORT=8080

# PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/law_rs56

# Meilisearch
MEILI_HOST=https://your-meili-host.meilisearch.io
MEILI_KEY=your_api_key
MEILI_MASTER_KEY=your_master_key
MEILI_INDEX_CIVIL=civil-articles        # 민법 인덱스
MEILI_INDEX_CRIMINAL=criminal-articles  # 형법 인덱스

# CORS (쉼표로 구분)
CORS_ORIGINS=https://your-frontend.vercel.app

# Docker용 (로컬 개발)
POSTGRES_PASSWORD=your_postgres_password
```

### 2️⃣ 로컬 개발 환경

```bash
# 1. 환경변수 파일 생성
cp .env.example .env
# .env 파일을 수정하여 실제 값 입력

# 2. Docker Compose 실행 (PostgreSQL + Meilisearch + API)
docker-compose up -d

# 3. API 문서 확인
open http://localhost/docs
```

### 3️⃣ Python 직접 실행

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 서버 실행
python -m app.main
# 또는
uvicorn app.main:app --reload --port 8080
```

---

## API 명세

### 기본 정보

- **Base URL**: `https://your-api-domain.com`
- **Content-Type**: `application/json`

---

### 1️⃣ 헬스체크

```http
GET /health
```

**응답 예시:**
```json
{
  "ok": true
}
```

---

### 2️⃣ 법령 목록 조회

```http
GET /laws
```

**응답 예시:**
```json
[
  {"code": "CIVIL_CODE", "nameKo": "민법"},
  {"code": "CRIMINAL_CODE", "nameKo": "형법"}
]
```

---

### 3️⃣ 통합/법령별 검색

```http
GET /search?q={검색어}&scope={all|civil|criminal}&limit=10&offset=0
```

**쿼리 파라미터:**
| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `q` | string | ✅ | - | 검색어 |
| `scope` | enum | ❌ | `all` | `all` (통합), `civil` (민법만), `criminal` (형법만) |
| `limit` | int | ❌ | 10 | 결과 제한 (최대 50) |
| `offset` | int | ❌ | 0 | 오프셋 |

**응답 예시:**
```json
{
  "query": "불법행위",
  "scope": "all",
  "limit": 10,
  "offset": 0,
  "hits": [
    {
      "lawCode": "CIVIL_CODE",
      "index": "civil-articles",
      "articleNo": 750,
      "articleSubNo": 0,
      "joCode": "075000",
      "heading": "제750조(불법행위의 일반요건)",
      "body": "고의 또는 과실로 인한 위법행위로...",
      "_rankingScore": 12.5
    }
  ],
  "count": 1
}
```

---

### 4️⃣ 조문 상세 조회

```http
GET /articles/{lawCode}/{articleNo}[/{articleSubNo}]
```

**경로 파라미터:**
- `lawCode`: 법령 코드 (`CIVIL_CODE`, `CRIMINAL_CODE`)
- `articleNo`: 조 번호
- `articleSubNo`: 조의 번호 (생략 시 0)

**예시:**
- `/articles/CIVIL_CODE/750` → 민법 제750조
- `/articles/CRIMINAL_CODE/250/1` → 형법 제250조의1

**응답 예시:**
```json
{
  "lawCode": "CIVIL_CODE",
  "articleNo": 750,
  "articleSubNo": 0,
  "joCode": "075000",
  "heading": "제750조(불법행위의 일반요건)",
  "body": "고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는...",
  "notes": ["[전문개정 2023.03.14]"],
  "clauses": [...],
  "updatedAt": "2025-11-04T12:34:56Z"
}
```

---

## 개발 가이드

### DB 스키마

**테이블: `law`**
| 컬럼 | 타입 | 설명 |
|-----|------|------|
| id | BIGSERIAL | PK |
| code | TEXT | 법령 코드 (UNIQUE) |
| name_ko | TEXT | 법령명 |

**테이블: `article`**
| 컬럼 | 타입 | 설명 |
|-----|------|------|
| id | BIGSERIAL | PK |
| law_id | BIGINT | FK → law(id) |
| article_no | INT | 조 번호 |
| article_sub_no | INT | 조의 번호 |
| jo_code | CHAR(6) | 정렬용 조 코드 |
| heading | TEXT | 조문 제목 |
| body | TEXT | 조문 본문 |
| notes | TEXT[] | 개정이력 |
| clauses_json | JSONB | 항/호/목 구조 |
| search_text | TEXT | 검색용 텍스트 |

### Meilisearch 인덱스

**민법 (`civil-articles`)**
- 기존 포맷 유지 (`lawCode` 필드 없음)
- 서버에서 응답 시 `lawCode: "CIVIL_CODE"` 자동 보정

**형법 (`criminal-articles`)**
- `lawCode: "CRIMINAL_CODE"` 필드 포함
- `id: "CRIMINAL_CODE-{joCode}"` 형식

---

## 배포

### Docker 배포

```bash
docker build -t law-search-api .
docker run -p 8080:8080 --env-file .env law-search-api
```

### Render.com 배포

1. 환경변수 설정 (위 "필수 환경변수" 참고)
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 8080`

---

## 라이선스

MIT

---

## 문의

이슈가 있으시면 GitHub Issues에 등록해주세요.
