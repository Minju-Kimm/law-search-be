"""
검색 API 라우터
"""
from typing import List
from fastapi import APIRouter, Query, HTTPException
from app.models import SearchScope, SearchResponse, SearchHit
from app.services.search_service import multi_index_search


router = APIRouter(prefix="", tags=["Search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="검색어"),
    scope: SearchScope = Query(SearchScope.ALL, description="검색 범위 (all/civil/criminal/civil_procedure/criminal_procedure)"),
    limit: int = Query(10, ge=1, le=50, description="결과 제한 수"),
    offset: int = Query(0, ge=0, description="오프셋")
):
    """
    통합/법령별 검색 API

    **검색 범위 (scope):**
    - `all`: 전체 법령 통합 검색 (민법 + 형법 + 민사소송법 + 형사소송법) (기본값)
    - `civil`: 민법만 검색
    - `criminal`: 형법만 검색
    - `civil_procedure`: 민사소송법만 검색
    - `criminal_procedure`: 형사소송법만 검색

    **응답:**
    - 모든 인덱스에서 검색한 결과를 `_rankingScore` 기준으로 정렬하여 반환
    - 각 결과에 `lawCode`, `articleNo`, `heading`, `body` 필드 포함
    - 인덱스별로 `lawCode`가 자동 매핑됨 (CIVIL_CODE, CRIMINAL_CODE, CIVIL_PROCEDURE_CODE, CRIMINAL_PROCEDURE_CODE)
    """
    q = q.strip()
    if not q:
        raise HTTPException(status_code=400, detail="검색어가 비어있습니다")

    # 멀티 인덱스 검색 실행
    hits_data = await multi_index_search(
        scope=scope.value,
        query=q,
        limit=limit,
        offset=offset
    )

    # Pydantic 모델로 변환
    hits = [SearchHit(**h) for h in hits_data]

    return SearchResponse(
        query=q,
        scope=scope.value,
        limit=limit,
        offset=offset,
        hits=hits,
        count=len(hits)
    )
