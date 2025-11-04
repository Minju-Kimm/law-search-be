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


## 라이선스

MIT

---

## 문의

이슈가 있으시면 GitHub Issues에 등록해주세요.
