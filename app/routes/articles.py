"""
조문 상세 API 라우터
"""
from fastapi import APIRouter, HTTPException, Path
from app.models import ArticleOut
from app.database import get_article_by_law_code


router = APIRouter(prefix="", tags=["Articles"])


@router.get("/articles/{lawCode}/{articleNo}", response_model=ArticleOut)
def get_article_detail(
    lawCode: str = Path(..., description="법령 코드 (예: CIVIL_CODE, CRIMINAL_CODE)"),
    articleNo: int = Path(..., description="조 번호"),
    articleSubNo: int = 0
):
    """
    조문 상세 조회 (DB 정본)

    **경로 파라미터:**
    - `lawCode`: 법령 코드 (예: `CIVIL_CODE`, `CRIMINAL_CODE`)
    - `articleNo`: 조 번호
    - `articleSubNo`: 조의 번호 (기본값: 0)

    **응답:**
    - PostgreSQL에서 조회한 정본 데이터
    - 항/호/목 구조화 데이터(`clauses`), 개정이력(`notes`) 포함
    """
    row = get_article_by_law_code(lawCode, articleNo, articleSubNo)

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"조문을 찾을 수 없습니다: {lawCode} 제{articleNo}조"
        )

    # ISO 8601 포맷으로 변환
    updated_at = None
    if row.get("updated_at"):
        updated_at = row["updated_at"].isoformat()

    return ArticleOut(
        lawCode=row["law_code"],
        articleNo=row["article_no"],
        articleSubNo=row["article_sub_no"],
        joCode=row["jo_code"],
        heading=row.get("heading") or "",
        body=row["body"],
        notes=row.get("notes") or [],
        clauses=row.get("clauses_json"),
        updatedAt=updated_at
    )


@router.get("/articles/{lawCode}/{articleNo}/{articleSubNo}", response_model=ArticleOut)
def get_article_detail_with_sub(
    lawCode: str = Path(..., description="법령 코드"),
    articleNo: int = Path(..., description="조 번호"),
    articleSubNo: int = Path(..., description="조의 번호")
):
    """
    조문 상세 조회 (조의번호 명시)

    예: `/articles/CIVIL_CODE/103/2` → 민법 제103조의2
    """
    return get_article_detail(lawCode, articleNo, articleSubNo)
