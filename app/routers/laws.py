"""
법령 관련 API 라우터
"""
from typing import List
from fastapi import APIRouter
from app.models import LawOut
from app.database import get_all_laws


router = APIRouter(prefix="", tags=["Laws"])


@router.get("/laws", response_model=List[LawOut])
def get_laws():
    """
    법령 목록 조회

    Returns:
        [
            {"code": "CIVIL_CODE", "nameKo": "민법"},
            {"code": "CRIMINAL_CODE", "nameKo": "형법"}
        ]
    """
    rows = get_all_laws()

    return [
        LawOut(code=row["code"], nameKo=row["name_ko"])
        for row in rows
    ]
