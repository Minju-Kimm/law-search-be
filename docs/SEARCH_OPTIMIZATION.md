# 한글 법령 검색 최적화 가이드

한글 법령 검색 시스템의 검색 품질 개선을 위한 설정 및 운영 가이드

## 📋 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [설정 적용](#설정-적용)
4. [색인 전처리](#색인-전처리)
5. [검색 테스트](#검색-테스트)
6. [문제 해결](#문제-해결)

---

## 개요

### 주요 개선사항

✅ **Meilisearch 인덱스 설정 튜닝**
- searchableAttributes 순서 최적화 (heading > joCode > body > body_ngram)
- typoTolerance 한글 법령 용어 최적화
- 법령 동의어 사전 (60+ 동의어 쌍)
- 조문 번호 정확 매칭을 위한 ranking rules

✅ **색인 전처리 (body_ngram)**
- 한글 2-gram, 3-gram 생성
- 부분 문자열 매칭 정확도 향상

✅ **서버단 재스코어링**
- 조문 번호 검색 시 정확도 우선 (+900점)
- joCode 정확 매칭 (+1000점)
- heading 키워드 매칭 (+50점)

✅ **CORS 보안 강화**
- 환경변수 기반 origin 관리
- credentials + wildcard 조합 금지
- 필요한 메서드만 허용 (GET, OPTIONS)

---

## 아키텍처

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │ HTTP GET /search?q=...&scope=...&strict=...
       ↓
┌─────────────────────────────────────┐
│       FastAPI Server                │
│  ┌────────────────────────────┐    │
│  │  app/routes/search.py      │    │
│  └───────────┬────────────────┘    │
│              ↓                      │
│  ┌────────────────────────────┐    │
│  │ app/services/search_service│    │
│  │ - multi_index_search()     │    │
│  │ - rescore()                │    │
│  └───────────┬────────────────┘    │
│              ↓                      │
│  ┌────────────────────────────┐    │
│  │ app/services/textproc.py   │    │
│  │ - normalize_article_query()│    │
│  └────────────────────────────┘    │
└──────────────┬──────────────────────┘
               ↓
        ┌──────────────┐
        │ Meilisearch  │
        │ - civil-articles    │
        │ - criminal-articles │
        └──────────────┘
```

---

## 설정 적용

### 1. 환경변수 설정

`.env` 파일에 다음 변수를 설정하세요:

```bash
# Meilisearch 연결 정보
MEILI_HOST=http://localhost:7700
MEILI_KEY=your-master-key-here
MEILI_INDEX_CIVIL=civil-articles
MEILI_INDEX_CRIMINAL=criminal-articles

# CORS 설정
CORS_ORIGINS=https://your-frontend.com,https://your-frontend-staging.com
CORS_ALLOW_CREDENTIALS=false
DEBUG=false

# PostgreSQL (정본 저장소)
DATABASE_URL=postgresql://user:password@localhost:5432/lawdb
```

### 2. Meilisearch 인덱스 설정 적용

```bash
# 의존성 설치 (없는 경우)
pip install -r requirements.txt

# 인덱스 설정 스크립트 실행
python scripts/setup_meili.py
```

**실행 결과 예시:**

```
============================================================
🚀 Meilisearch 인덱스 설정 스크립트
============================================================
📍 호스트: http://localhost:7700
📋 대상 인덱스:
   - civil-articles
   - criminal-articles

✅ Meilisearch 서버 연결 성공

============================================================
📋 인덱스: civil-articles
🔧 설정 적용 중... (시도 1/3)
✅ 설정 적용 요청 성공 (Task UID: 123)
⏳ 태스크 완료 대기 중...
✅ 태스크 완료

📊 적용된 설정 확인:
   - searchableAttributes: ['heading', 'joCode']...
   - filterableAttributes: ['lawCode', 'articleNo', 'articleSubNo']
   - rankingRules: 8개
   - synonyms: 60개
   - typoTolerance: enabled=True

============================================================
📊 최종 결과
============================================================
✅ 성공 - civil-articles
✅ 성공 - criminal-articles

🎉 모든 인덱스 설정이 완료되었습니다!
```

### 3. 설정 확인

```bash
# curl로 설정 확인
curl -X GET "http://localhost:7700/indexes/civil-articles/settings" \
  -H "Authorization: Bearer your-master-key"
```

---

## 색인 전처리

### 신규 문서 색인 시

문서를 Meilisearch에 색인하기 전에 `body_ngram` 필드를 추가하세요:

```python
from app.services.textproc import prepare_document_for_indexing

# 원본 문서
doc = {
    "articleNo": 218,
    "heading": "제218조(불법행위)",
    "body": "악의 또는 중대한 과실로 타인의 권리를 침해한 자는..."
}

# 전처리 (body_ngram 추가)
prepared = prepare_document_for_indexing(doc)

# Meilisearch에 색인
# prepared["body_ngram"] = "악의 의 또 또는 는 중 중대 대한 ..."
```

### 기존 문서 재색인

기존에 색인된 문서에 `body_ngram` 필드를 추가하려면 재색인 스크립트를 사용하세요:

```bash
# 재색인 스크립트 실행
python scripts/reindex_with_ngram.py
```

**재색인 스크립트 예시:**

```python
#!/usr/bin/env python3
"""
기존 문서에 body_ngram 필드 추가 (재색인)

PostgreSQL에서 데이터를 읽어 body_ngram을 생성하고
Meilisearch에 재색인합니다.
"""
import os
import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from app.services.textproc import prepare_document_for_indexing

load_dotenv()

MEILI_HOST = os.getenv("MEILI_HOST")
MEILI_KEY = os.getenv("MEILI_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

INDEXES = {
    "CIVIL_CODE": "civil-articles",
    "CRIMINAL_CODE": "criminal-articles"
}

def fetch_documents_from_db(law_code: str):
    """PostgreSQL에서 문서 가져오기"""
    engine = create_engine(DATABASE_URL)

    query = text("""
        SELECT
            law_code as "lawCode",
            article_no as "articleNo",
            article_sub_no as "articleSubNo",
            jo_code as "joCode",
            heading,
            body
        FROM articles
        WHERE law_code = :law_code
        ORDER BY article_no, article_sub_no
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"law_code": law_code})
        docs = [dict(row._mapping) for row in result]

    return docs

def reindex_to_meilisearch(index_name: str, docs: list):
    """Meilisearch에 재색인"""
    # body_ngram 추가
    prepared_docs = [prepare_document_for_indexing(doc) for doc in docs]

    # 배치 색인
    url = f"{MEILI_HOST}/indexes/{index_name}/documents"
    headers = {"Authorization": f"Bearer {MEILI_KEY}"}

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, json=prepared_docs)

        if response.status_code == 202:
            task_data = response.json()
            print(f"✅ 재색인 요청 성공 (Task UID: {task_data.get('taskUid')})")
        else:
            print(f"❌ 재색인 실패: {response.status_code} - {response.text}")

def main():
    for law_code, index_name in INDEXES.items():
        print(f"\n{'='*60}")
        print(f"📋 {law_code} → {index_name}")

        # DB에서 가져오기
        docs = fetch_documents_from_db(law_code)
        print(f"📄 문서 {len(docs)}개 가져옴")

        # 재색인
        reindex_to_meilisearch(index_name, docs)
        print(f"✅ 재색인 완료")

    print(f"\n{'='*60}")
    print("🎉 모든 재색인 완료!")

if __name__ == "__main__":
    main()
```

**재색인 스크립트 저장 및 실행:**

```bash
# 스크립트 저장
# (위 코드를 scripts/reindex_with_ngram.py에 저장)

# 실행
python scripts/reindex_with_ngram.py
```

---

## 검색 테스트

### 1. 기본 검색

```bash
# 전체 검색
curl "http://localhost:8080/search?q=불법행위&scope=all"

# 민법만 검색
curl "http://localhost:8080/search?q=불법행위&scope=civil"

# 형법만 검색
curl "http://localhost:8080/search?q=절도&scope=criminal"
```

### 2. 조문 번호 검색 (AC 테스트)

**테스트 1: q="218" → 218조 최상단**

```bash
curl "http://localhost:8080/search?q=218&scope=civil&limit=20"
```

**기대 결과:**
- 첫 번째 결과: `articleNo: 218`, `_appScore: 900+`
- 나머지 결과: `_appScore < 900`

**테스트 2: q="제218조" → 정확 매칭**

```bash
curl "http://localhost:8080/search?q=제218조&scope=civil&limit=20"
```

**기대 결과:**
- 첫 번째 결과: `articleNo: 218`, `joCode: "제218조"`, `_appScore: 1000+`

### 3. 키워드 검색 (AC 테스트)

**테스트 3: q="악의 또는 중대한 과실" → 정확 문구 매칭**

```bash
curl "http://localhost:8080/search?q=악의+또는+중대한+과실&scope=all&limit=20"
```

**기대 결과:**
- 상위 결과에 해당 문구가 포함된 조문들
- `body`에 "악의 또는 중대한 과실" 포함

**테스트 4: q="점유" → heading/joCode 우선**

```bash
curl "http://localhost:8080/search?q=점유&scope=civil&limit=20"
```

**기대 결과:**
- 상위 결과: `heading`에 "점유" 포함 (+50점)
- 하위 결과: `body`에만 "점유" 포함

### 4. strict 모드 테스트

```bash
# 부분 매칭 (기본)
curl "http://localhost:8080/search?q=악의+과실&scope=all"

# 엄격 모드 (모든 단어 필수)
curl "http://localhost:8080/search?q=악의+과실&scope=all&strict=true"
```

**기대 결과:**
- `strict=false`: "악의" 또는 "과실" 포함 문서 반환
- `strict=true`: "악의" **AND** "과실" 모두 포함 문서만 반환

### 5. 동의어 테스트

```bash
# "무효" 검색 → "취소", "효력없음" 등도 매칭
curl "http://localhost:8080/search?q=무효&scope=all&limit=20"

# "담보" 검색 → "보증", "저당" 등도 매칭
curl "http://localhost:8080/search?q=담보&scope=civil&limit=20"
```

### 6. 응답 포맷 확인

```json
{
  "query": "218",
  "scope": "civil",
  "limit": 10,
  "offset": 0,
  "hits": [
    {
      "lawCode": "CIVIL_CODE",
      "index": "civil-articles",
      "articleNo": 218,
      "articleSubNo": 0,
      "joCode": "제218조",
      "heading": "제218조(불법행위의 요건)",
      "body": "악의 또는 중대한 과실로...",
      "rankingScore": 12.5,      // Meilisearch 원본 점수
      "appScore": 912.5          // 재스코어링 점수 (기본 + 보너스)
    }
  ],
  "count": 1
}
```

---

## CORS 테스트

### 프리플라이트 요청 테스트

```bash
# OPTIONS 요청 (프리플라이트)
curl -X OPTIONS http://localhost:8080/search \
  -H "Origin: https://your-frontend.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

**기대 응답 헤더:**

```
HTTP/1.1 200 OK
access-control-allow-origin: https://your-frontend.com
access-control-allow-methods: GET, OPTIONS
access-control-allow-headers: Content-Type
vary: Origin
```

### 실제 요청 테스트

```bash
curl -X GET "http://localhost:8080/search?q=불법행위" \
  -H "Origin: https://your-frontend.com" \
  -v
```

**기대 응답 헤더:**

```
HTTP/1.1 200 OK
access-control-allow-origin: https://your-frontend.com
vary: Origin
content-type: application/json
```

---

## 문제 해결

### 1. 인덱스가 없다는 오류

**증상:**
```
❌ 인덱스 'civil-articles'를 찾을 수 없습니다.
💡 먼저 인덱스에 문서를 색인해야 합니다.
```

**해결:**
1. PostgreSQL에서 데이터를 Meilisearch로 색인
2. 인덱스가 생성된 후 `scripts/setup_meili.py` 재실행

### 2. 동의어가 작동하지 않음

**원인:**
- 인덱스 설정이 적용되지 않았거나
- 문서 재색인이 필요함

**해결:**
```bash
# 설정 재적용
python scripts/setup_meili.py

# 문서 재색인 (필요시)
python scripts/reindex_with_ngram.py
```

### 3. body_ngram 필드가 없음

**원인:**
- 문서 색인 시 `prepare_document_for_indexing()` 미사용

**해결:**
```bash
# 재색인 스크립트 실행
python scripts/reindex_with_ngram.py
```

### 4. 조문 번호 검색이 부정확함

**원인:**
- 재스코어링 로직이 적용되지 않았거나
- `articleNo`, `joCode` 필드가 없음

**해결:**
1. `app/services/search_service.py`의 `rescore()` 함수 확인
2. 문서에 `articleNo`, `joCode` 필드 존재 확인
3. 서버 재시작

### 5. CORS 오류

**증상:**
```
Access to fetch at 'http://localhost:8080/search' from origin 'https://...'
has been blocked by CORS policy
```

**해결:**
```bash
# .env 파일 확인
CORS_ORIGINS=https://your-frontend.com

# 서버 재시작
python -m uvicorn app.main:app --reload
```

### 6. Meilisearch 연결 실패

**증상:**
```
❌ Meilisearch 서버 연결 실패: Connection refused
```

**해결:**
```bash
# Meilisearch가 실행 중인지 확인
docker ps | grep meilisearch

# 실행되지 않은 경우
docker-compose up -d meilisearch

# 헬스체크
curl http://localhost:7700/health
```

---

## 롤백 방법

설정을 이전 상태로 되돌리려면:

### 1. Meilisearch 설정 초기화

```bash
# 설정 초기화 (기본값으로 복원)
curl -X DELETE "http://localhost:7700/indexes/civil-articles/settings" \
  -H "Authorization: Bearer your-master-key"

curl -X DELETE "http://localhost:7700/indexes/criminal-articles/settings" \
  -H "Authorization: Bearer your-master-key"
```

### 2. 코드 롤백

```bash
# Git으로 이전 커밋으로 되돌리기
git log --oneline  # 커밋 이력 확인
git checkout <commit-hash>
```

### 3. 인덱스 재생성

```bash
# 인덱스 삭제
curl -X DELETE "http://localhost:7700/indexes/civil-articles" \
  -H "Authorization: Bearer your-master-key"

# 문서 재색인 (기존 방식)
# ...
```

---

## 참고 자료

- [Meilisearch 공식 문서](https://docs.meilisearch.com/)
- [FastAPI CORS 가이드](https://fastapi.tiangolo.com/tutorial/cors/)
- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/)

---

**작성일:** 2025-11-05
**버전:** 1.0.0
