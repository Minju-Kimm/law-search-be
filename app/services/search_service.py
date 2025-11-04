"""
Meilisearch 통합 검색 서비스
"""
import os
from typing import List, Dict, Any, Optional
import httpx
from fastapi import HTTPException


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
    offset: int = 0
) -> Dict[str, Any]:
    """
    단일 Meilisearch 인덱스에서 검색

    Args:
        index_name: 인덱스명 (예: "civil-articles")
        query: 검색어
        limit: 결과 제한 수
        offset: 오프셋

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
        "_rankingScore": hit.get("_rankingScore")
    }


async def multi_index_search(
    scope: str,
    query: str,
    limit: int = 10,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    멀티 인덱스 통합 검색

    Args:
        scope: "all" | "civil" | "criminal"
        query: 검색어
        limit: 최종 반환 개수
        offset: 각 인덱스에 적용할 오프셋

    Returns:
        정규화된 hit 리스트 (랭킹 점수 기준 정렬)
    """
    indexes = get_indexes_by_scope(scope)
    if not indexes:
        return []

    # 각 인덱스에서 검색 (병렬)
    all_hits = []
    for idx in indexes:
        try:
            result = await search_in_index(idx, query, limit, offset)
            hits = result.get("hits", [])

            # 정규화 및 인덱스명 주입
            for h in hits:
                normalized = normalize_hit(h, idx)
                all_hits.append(normalized)

        except HTTPException as e:
            # 개별 인덱스 실패 시 로깅만 하고 계속 진행
            print(f"[WARNING] Index '{idx}' search failed: {e.detail}")
            continue

    # _rankingScore 기준 정렬 (None은 마지막으로)
    all_hits.sort(key=lambda x: x.get("_rankingScore") or 0.0, reverse=True)

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
