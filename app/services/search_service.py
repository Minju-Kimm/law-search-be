"""
Meilisearch 통합 검색 서비스 (검색 정확도 개선 버전)
"""
import os
from typing import List, Dict, Any, Optional
import httpx
from fastapi import HTTPException
from app.services.textproc import boost_query_numbers, extract_numbers


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
    strict_mode: bool = True
) -> Dict[str, Any]:
    """
    단일 Meilisearch 인덱스에서 검색 (정확도 개선 버전)

    Args:
        index_name: 인덱스명 (예: "civil-articles")
        query: 검색어
        limit: 결과 제한 수
        offset: 오프셋
        strict_mode: 엄격 모드 (matchingStrategy="all", 기본값: True)

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

    # 쿼리 분석: 숫자 포함 여부 확인
    query_info = boost_query_numbers(query)

    # 검색 페이로드 구성
    payload = {
        "q": query,
        "limit": limit,
        "offset": offset,
        "showRankingScore": True,  # _rankingScore 필드 포함
        "matchingStrategy": "all" if strict_mode else "last"  # strict 모드: 모든 단어 매치 필수
    }

    # 숫자가 포함된 경우 특정 필드 우선 검색 (조 번호 매칭 강화)
    if query_info["has_numbers"]:
        payload["attributesToSearchOn"] = ["joCode", "heading", "body"]

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

            result = r.json()

            # rescore: 숫자 쿼리인 경우 joCode 정확 매칭에 가중치 부여
            if query_info["has_numbers"]:
                result = _rescore_number_query(result, query_info)

            return result

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Meilisearch connection error: {str(e)}"
        )


def _rescore_number_query(result: Dict[str, Any], query_info: dict) -> Dict[str, Any]:
    """
    숫자 쿼리에 대한 재점수화 (rescore)

    joCode나 heading에 쿼리 숫자가 정확히 포함된 경우 랭킹 점수를 부스트합니다.

    Args:
        result: Meilisearch 검색 결과
        query_info: boost_query_numbers()의 반환값

    Returns:
        재점수화된 검색 결과
    """
    numbers = query_info.get("numbers", [])
    boost_factor = query_info.get("boost_factor", 1.0)

    if not numbers or boost_factor <= 1.0:
        return result

    hits = result.get("hits", [])

    for hit in hits:
        jo_code = hit.get("joCode", "")
        heading = hit.get("heading", "")
        base_score = hit.get("_rankingScore", 0.0)

        # joCode나 heading에 쿼리 숫자가 정확히 포함되면 점수 부스트
        boost_applied = False

        for num in numbers:
            # joCode에 숫자가 포함되거나 (예: "000750" in joCode for "750")
            # heading에 숫자가 포함되면 (예: "제750조" in heading)
            if num in jo_code or num in heading:
                hit["_rankingScore"] = base_score * boost_factor
                boost_applied = True
                break

    return result


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
