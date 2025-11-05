"""
Meilisearch 통합 검색 서비스 + 재스코어링
"""
import os
import re
from typing import List, Dict, Any, Optional
import httpx
from fastapi import HTTPException
from app.services.textproc import normalize_article_query


MEILI_HOST = os.getenv("MEILI_HOST")
MEILI_KEY = os.getenv("MEILI_KEY")
MEILI_INDEX_CIVIL = os.getenv("MEILI_INDEX_CIVIL", "civil-articles")
MEILI_INDEX_CRIMINAL = os.getenv("MEILI_INDEX_CRIMINAL", "criminal-articles")


def get_indexes_by_scope(scope: str) -> List[str]:
    """
    검색 범위에 따른 인덱스 목록 반환

    Args:
        scope: "all" | "civil" | "criminal"

    Returns:
        인덱스명 리스트
    """
    if scope == "all":
        return [MEILI_INDEX_CIVIL, MEILI_INDEX_CRIMINAL]
    elif scope == "civil":
        return [MEILI_INDEX_CIVIL]
    elif scope == "criminal":
        return [MEILI_INDEX_CRIMINAL]
    else:
        return []


async def search_in_index(
    index_name: str,
    query: str,
    limit: int = 10,
    offset: int = 0,
    strict: bool = False,
    filter_expr: Optional[str] = None
) -> Dict[str, Any]:
    """
    단일 Meilisearch 인덱스에서 검색

    Args:
        index_name: 인덱스명 (예: "civil-articles")
        query: 검색어
        limit: 결과 제한 수
        offset: 오프셋
        strict: True이면 matchingStrategy="all" (모든 단어 필수)
        filter_expr: Meilisearch 필터 표현식 (예: "lawCode = CIVIL_CODE")

    Returns:
        {
            "hits": [...],
            "estimatedTotalHits": int,
            ...
        }

    Raises:
        HTTPException: Meilisearch 통신 실패 시
    """
    headers = {"Authorization": f"Bearer {MEILI_KEY}"}
    payload = {
        "q": query,
        "limit": limit,
        "offset": offset,
        "showRankingScore": True  # _rankingScore 필드 포함
    }

    # strict 모드: 모든 단어 필수 매칭
    if strict:
        payload["matchingStrategy"] = "all"

    # 필터 적용
    if filter_expr:
        payload["filter"] = filter_expr

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(
                f"{MEILI_HOST}/indexes/{index_name}/search",
                headers=headers,
                json=payload
            )

            if r.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Meilisearch error [{index_name}] {r.status_code}: {r.text}"
                )

            return r.json()

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Meilisearch connection error: {str(e)}"
        )


def rescore(hit: Dict[str, Any], query: str) -> float:
    """
    검색 결과에 대한 재스코어링 (서버 단)

    Meilisearch의 _rankingScore를 기반으로 조문 번호 매칭, 제목 매칭 등을
    고려하여 추가 점수를 부여합니다.

    Args:
        hit: Meilisearch hit (정규화된 형태)
        query: 검색어

    Returns:
        최종 애플리케이션 점수 (_appScore)

    스코어링 규칙:
        - 기본: Meilisearch _rankingScore
        - 조문 번호 정확 매칭: +900
        - joCode에 "제{q}조" 포함: +1000
        - heading에 검색어 포함: +50
    """
    base_score = hit.get("_rankingScore", 0.0)
    bonus = 0.0

    # 조문 번호 검색어 파싱
    article_info = normalize_article_query(query)

    if article_info["is_article_query"]:
        # 조문 번호로 검색한 경우
        target_article_no = article_info["article_no"]
        target_article_sub_no = article_info["article_sub_no"]

        hit_article_no = hit.get("articleNo", 0)
        hit_article_sub_no = hit.get("articleSubNo", 0)

        # 정확 매칭
        if hit_article_no == target_article_no:
            if target_article_sub_no is None or hit_article_sub_no == target_article_sub_no:
                bonus += 900  # 조문 번호 정확 매칭

        # joCode 매칭 (예: "제218조")
        jo_code = hit.get("joCode", "")
        if target_article_sub_no is None:
            if f"제{target_article_no}조" in jo_code or jo_code == f"{target_article_no:06d}":
                bonus += 1000
        else:
            if f"제{target_article_no}조의{target_article_sub_no}" in jo_code:
                bonus += 1000

    # heading 매칭 (키워드 검색)
    heading = hit.get("heading", "")
    query_lower = query.lower()
    if query_lower in heading.lower():
        bonus += 50

    # 최종 점수 = 기본 점수 + 보너스
    return base_score + bonus


def normalize_hit(hit: Dict[str, Any], index_name: str) -> Dict[str, Any]:
    """
    Meilisearch hit를 표준 포맷으로 정규화

    Args:
        hit: Meilisearch 원본 hit
        index_name: 소속 인덱스명

    Returns:
        {
            "lawCode": str,
            "index": str,
            "articleNo": int,
            "articleSubNo": int,
            "joCode": str,
            "heading": str,
            "body": str,
            "_rankingScore": float | None
        }
    """
    # 민법 인덱스는 lawCode 필드가 없으므로 보정
    law_code = hit.get("lawCode")
    if not law_code:
        if index_name == MEILI_INDEX_CIVIL:
            law_code = "CIVIL_CODE"
        elif index_name == MEILI_INDEX_CRIMINAL:
            law_code = "CRIMINAL_CODE"
        else:
            law_code = "UNKNOWN"

    return {
        "lawCode": law_code,
        "index": index_name,
        "articleNo": hit.get("articleNo", 0),
        "articleSubNo": hit.get("articleSubNo", 0),
        "joCode": hit.get("joCode", ""),
        "heading": hit.get("heading", ""),
        "body": hit.get("body", ""),
        "_rankingScore": hit.get("_rankingScore"),
        "_appScore": None  # 재스코어링 후 설정됨
    }


async def multi_index_search(
    scope: str,
    query: str,
    limit: int = 10,
    offset: int = 0,
    strict: bool = False
) -> List[Dict[str, Any]]:
    """
    멀티 인덱스 통합 검색 + 재스코어링

    Args:
        scope: "all" | "civil" | "criminal"
        query: 검색어
        limit: 최종 반환 개수
        offset: 각 인덱스에 적용할 오프셋
        strict: True이면 모든 단어 필수 매칭

    Returns:
        정규화 및 재스코어링된 hit 리스트 (_appScore 기준 정렬)
    """
    indexes = get_indexes_by_scope(scope)
    if not indexes:
        return []

    # scope별 필터 생성
    filter_expr = None
    if scope == "civil":
        filter_expr = "lawCode = CIVIL_CODE"
    elif scope == "criminal":
        filter_expr = "lawCode = CRIMINAL_CODE"

    # 각 인덱스에서 검색
    all_hits = []
    for idx in indexes:
        try:
            # limit * 2를 가져와서 재스코어링 후 상위 선택
            fetch_limit = limit * 2
            result = await search_in_index(
                idx, query, fetch_limit, offset, strict=strict, filter_expr=filter_expr
            )
            hits = result.get("hits", [])

            # 정규화 및 인덱스명 주입
            for h in hits:
                normalized = normalize_hit(h, idx)
                all_hits.append(normalized)

        except HTTPException as e:
            # 개별 인덱스 실패 시 로깅만 하고 계속 진행
            print(f"[WARNING] Index '{idx}' search failed: {e.detail}")
            continue

    # 재스코어링 적용
    for hit in all_hits:
        hit["_appScore"] = rescore(hit, query)

    # _appScore 기준 정렬 (높은 순)
    all_hits.sort(key=lambda x: x.get("_appScore", 0.0), reverse=True)

    # 상위 limit개 반환
    return all_hits[:limit]


async def health_check_meili() -> bool:
    """
    Meilisearch 헬스체크

    Returns:
        True if OK, raises Exception otherwise
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{MEILI_HOST}/health")
        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}")
    return True
