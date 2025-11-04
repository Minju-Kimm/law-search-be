"""
Database access layer
"""
import os
from typing import Optional, List, Dict, Any
import psycopg
from psycopg.rows import dict_row


DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    """DB 연결 생성 (sync)"""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


# ============================================
# Law (법령) 관련 쿼리
# ============================================

def get_all_laws() -> List[Dict[str, Any]]:
    """
    모든 법령 목록 조회
    Returns: [{"code": "CIVIL_CODE", "name_ko": "민법"}, ...]
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT code, name_ko
            FROM law
            ORDER BY id ASC;
            """
        ).fetchall()
        return rows


def get_law_id_by_code(code: str) -> Optional[int]:
    """
    법령 코드로 law_id 조회
    Args:
        code: 법령 코드 (예: "CIVIL_CODE")
    Returns: law_id (int) or None
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM law WHERE code = %s LIMIT 1;",
            (code,)
        ).fetchone()
        return row["id"] if row else None


# ============================================
# Article (조문) 관련 쿼리
# ============================================

def get_article_by_law_code(
    law_code: str,
    article_no: int,
    article_sub_no: int = 0
) -> Optional[Dict[str, Any]]:
    """
    법령 코드 + 조번호로 조문 상세 조회 (DB 정본)

    Args:
        law_code: 법령 코드 (예: "CIVIL_CODE")
        article_no: 조 번호
        article_sub_no: 조의 번호 (기본값 0)

    Returns:
        {
            "law_code": str,
            "article_no": int,
            "article_sub_no": int,
            "jo_code": str,
            "heading": str,
            "body": str,
            "notes": List[str],
            "clauses_json": Any,
            "updated_at": datetime
        }
        or None (해당 조문 없음)
    """
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                l.code AS law_code,
                a.article_no,
                a.article_sub_no,
                a.jo_code,
                a.heading,
                a.body,
                a.notes,
                a.clauses_json,
                a.updated_at
            FROM article a
            JOIN law l ON l.id = a.law_id
            WHERE l.code = %s
              AND a.article_no = %s
              AND a.article_sub_no = %s
            LIMIT 1;
            """,
            (law_code, article_no, article_sub_no)
        ).fetchone()
        return row


def health_check_db() -> bool:
    """
    DB 헬스체크
    Returns: True if OK, raises Exception otherwise
    """
    with get_conn() as conn:
        conn.execute("SELECT 1;").fetchone()
    return True
