"""
Pydantic models for API request/response validation
"""
from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from enum import Enum


# ============================================
# Enums
# ============================================

class SearchScope(str, Enum):
    """검색 범위"""
    ALL = "all"
    CIVIL = "civil"
    CRIMINAL = "criminal"
    CIVIL_PROCEDURE = "civil_procedure"
    CRIMINAL_PROCEDURE = "criminal_procedure"


# ============================================
# Response Models
# ============================================

class LawOut(BaseModel):
    """법령 정보 (응답용)"""
    code: str = Field(..., description="법령 코드 (예: CIVIL_CODE)")
    nameKo: str = Field(..., description="법령명 (예: 민법)")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "CIVIL_CODE",
                "nameKo": "민법"
            }
        }


class SearchHit(BaseModel):
    """검색 결과 단일 항목"""
    model_config = ConfigDict(
        populate_by_name=True,  # Allow both field name and alias
        json_schema_extra={
            "example": {
                "lawCode": "CIVIL_CODE",
                "index": "civil-articles",
                "articleNo": 1,
                "articleSubNo": 0,
                "joCode": "000100",
                "heading": "제1조(목적)",
                "body": "이 법은 개인의 존엄과 양성의 평등을 기초로...",
                "_rankingScore": 12.5
            }
        }
    )

    lawCode: str = Field(..., description="법령 코드")
    index: str = Field(..., description="검색된 Meilisearch 인덱스명")
    articleNo: int = Field(..., description="조 번호")
    articleSubNo: int = Field(..., description="조의 번호")
    joCode: str = Field(..., description="6자리 조 코드 (예: 000100)")
    heading: str = Field(..., description="조문 제목 (예: 제1조(목적))")
    body: str = Field(..., description="조문 본문")
    rankingScore: Optional[float] = Field(None, alias="_rankingScore", description="Meilisearch 랭킹 점수")


class SearchResponse(BaseModel):
    """검색 결과 응답"""
    query: str = Field(..., description="검색어")
    scope: str = Field(..., description="검색 범위 (all/civil/criminal)")
    limit: int = Field(..., description="결과 제한 수")
    offset: int = Field(..., description="오프셋")
    hits: List[SearchHit] = Field(default_factory=list, description="검색 결과 목록")
    count: int = Field(..., description="반환된 결과 수")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "불법행위",
                "scope": "all",
                "limit": 10,
                "offset": 0,
                "hits": [],
                "count": 0
            }
        }


class ArticleOut(BaseModel):
    """조문 상세 정보 (응답용)"""
    lawCode: str = Field(..., description="법령 코드")
    articleNo: int = Field(..., description="조 번호")
    articleSubNo: int = Field(..., description="조의 번호")
    joCode: str = Field(..., description="6자리 조 코드")
    heading: str = Field(..., description="조문 제목")
    body: str = Field(..., description="조문 본문")
    notes: List[str] = Field(default_factory=list, description="비고 (예: [전문개정 2023.03.14])")
    clauses: Any = Field(None, description="항/호/목 구조화 데이터 (JSONB)")
    updatedAt: Optional[str] = Field(None, description="최종 수정 시각 (ISO 8601)")

    class Config:
        json_schema_extra = {
            "example": {
                "lawCode": "CIVIL_CODE",
                "articleNo": 1,
                "articleSubNo": 0,
                "joCode": "000100",
                "heading": "제1조(목적)",
                "body": "이 법은 개인의 존엄과 양성의 평등을 기초로...",
                "notes": ["[전문개정 2023.03.14]"],
                "clauses": [],
                "updatedAt": "2025-11-04T12:34:56Z"
            }
        }


class HealthResponse(BaseModel):
    """헬스체크 응답"""
    ok: bool = Field(..., description="서비스 정상 여부")
    db: Optional[str] = Field(None, description="DB 상태 (에러 메시지)")
    meili: Optional[str] = Field(None, description="Meilisearch 상태 (에러 메시지)")

    class Config:
        json_schema_extra = {
            "example": {
                "ok": True
            }
        }


# ============================================
# User & Auth Models
# ============================================

class UserOut(BaseModel):
    """User response model"""
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User name")
    provider: str = Field(..., description="OAuth provider (google/naver)")
    created_at: datetime = Field(..., description="Account creation timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "name": "홍길동",
                "provider": "google",
                "created_at": "2025-11-07T00:00:00Z"
            }
        }


# ============================================
# Bookmark Models
# ============================================

class BookmarkCreate(BaseModel):
    """Bookmark creation request - supports multiple input formats"""
    # Primary fields
    lawCode: Optional[str] = Field(None, description="법령 코드 (예: CIVIL_CODE)")
    articleNo: Optional[str] = Field(None, description="조 번호 (예: '760')")
    memo: Optional[str] = Field(None, description="메모")

    # Alternative input fields for flexibility
    joCode: Optional[str] = Field(None, description="조 코드 (예: '076000')")
    heading: Optional[str] = Field(None, description="조문 제목 (예: '제760조')")
    lawType: Optional[str] = Field(None, description="법령 타입 (예: 'civil')")

    class Config:
        json_schema_extra = {
            "example": {
                "lawCode": "CIVIL_CODE",
                "articleNo": "760",
                "memo": "불법행위 책임"
            }
        }


class BookmarkOut(BaseModel):
    """Bookmark response model"""
    id: int = Field(..., description="Bookmark ID")
    lawCode: str = Field(..., description="법령 코드")
    articleNo: str = Field(..., description="조 번호")
    memo: Optional[str] = Field(None, description="메모")
    createdAt: datetime = Field(..., description="북마크 생성 시각")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "lawCode": "CIVIL_CODE",
                "articleNo": "760",
                "memo": "불법행위 책임",
                "createdAt": "2025-11-07T00:00:00Z"
            }
        }
