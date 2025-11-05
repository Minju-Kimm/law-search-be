"""
한글 텍스트 전처리 모듈

법령 검색 최적화를 위한 n-gram 생성 등
"""
import re
from typing import Tuple, List


def ko_ngram(text: str, n: Tuple[int, int] = (2, 3)) -> str:
    """
    한글 텍스트를 n-gram으로 분해하여 공백으로 구분된 문자열 반환

    부분 문자열 매칭을 개선하기 위해 사용됩니다.
    예: "불법행위" -> "불법 법행 행위 불법행 법행위"

    Args:
        text: 원본 텍스트
        n: n-gram 범위 (min, max) 튜플. 기본값 (2, 3)

    Returns:
        n-gram 토큰들을 공백으로 구분한 문자열

    Examples:
        >>> ko_ngram("불법행위", n=(2, 3))
        "불법 법행 행위 불법행 법행위"

        >>> ko_ngram("제218조", n=(2, 3))
        "제2 21 18 8조 제21 218 18조"
    """
    if not text:
        return ""

    # 공백과 개행 제거
    text = re.sub(r'\s+', '', text.strip())

    if len(text) < n[0]:
        return text

    ngrams = []
    min_n, max_n = n

    # n-gram 생성 (min_n부터 max_n까지)
    for gram_size in range(min_n, max_n + 1):
        for i in range(len(text) - gram_size + 1):
            ngram = text[i:i + gram_size]
            ngrams.append(ngram)

    # 중복 제거 (순서 유지)
    seen = set()
    unique_ngrams = []
    for ngram in ngrams:
        if ngram not in seen:
            seen.add(ngram)
            unique_ngrams.append(ngram)

    return " ".join(unique_ngrams)


def extract_keywords(text: str) -> List[str]:
    """
    법령 텍스트에서 주요 키워드 추출

    주로 한글, 숫자, 일부 특수문자만 추출하여 검색 품질 향상에 사용

    Args:
        text: 원본 텍스트

    Returns:
        키워드 리스트

    Examples:
        >>> extract_keywords("제218조(불법행위)")
        ["제218조", "불법행위"]
    """
    if not text:
        return []

    # 한글, 숫자, 일부 특수문자(조문 관련)만 유지
    pattern = r'[가-힣0-9제조항호목\(\)]+[가-힣0-9제조항호목\(\)\s]*'
    matches = re.findall(pattern, text)

    # 공백 정규화 및 빈 문자열 제거
    keywords = []
    for match in matches:
        cleaned = re.sub(r'\s+', ' ', match.strip())
        if cleaned and len(cleaned) >= 2:  # 최소 2자 이상
            keywords.append(cleaned)

    return keywords


def normalize_article_query(query: str) -> dict:
    """
    조문 번호 검색어를 파싱하여 정규화

    Args:
        query: 검색어 (예: "218", "제218조", "218조의2")

    Returns:
        {
            "is_article_query": bool,
            "article_no": int | None,
            "article_sub_no": int | None,
            "original": str
        }

    Examples:
        >>> normalize_article_query("218")
        {"is_article_query": True, "article_no": 218, "article_sub_no": None, "original": "218"}

        >>> normalize_article_query("제218조의2")
        {"is_article_query": True, "article_no": 218, "article_sub_no": 2, "original": "제218조의2"}
    """
    query = query.strip()

    # 패턴 1: 순수 숫자 (예: "218")
    match = re.match(r'^(\d+)$', query)
    if match:
        return {
            "is_article_query": True,
            "article_no": int(match.group(1)),
            "article_sub_no": None,
            "original": query
        }

    # 패턴 2: 제N조 (예: "제218조")
    match = re.match(r'^제\s*(\d+)\s*조$', query)
    if match:
        return {
            "is_article_query": True,
            "article_no": int(match.group(1)),
            "article_sub_no": None,
            "original": query
        }

    # 패턴 3: 제N조의M (예: "제218조의2")
    match = re.match(r'^제\s*(\d+)\s*조의\s*(\d+)$', query)
    if match:
        return {
            "is_article_query": True,
            "article_no": int(match.group(1)),
            "article_sub_no": int(match.group(2)),
            "original": query
        }

    # 패턴 4: N조 (예: "218조")
    match = re.match(r'^(\d+)\s*조$', query)
    if match:
        return {
            "is_article_query": True,
            "article_no": int(match.group(1)),
            "article_sub_no": None,
            "original": query
        }

    # 패턴 5: N조의M (예: "218조의2")
    match = re.match(r'^(\d+)\s*조의\s*(\d+)$', query)
    if match:
        return {
            "is_article_query": True,
            "article_no": int(match.group(1)),
            "article_sub_no": int(match.group(2)),
            "original": query
        }

    # 조문 번호 패턴이 아님
    return {
        "is_article_query": False,
        "article_no": None,
        "article_sub_no": None,
        "original": query
    }


def prepare_document_for_indexing(doc: dict) -> dict:
    """
    문서를 Meilisearch 색인용으로 전처리

    body 필드에서 body_ngram 필드를 생성합니다.

    Args:
        doc: 원본 문서 (articleNo, body 등 포함)

    Returns:
        body_ngram 필드가 추가된 문서

    Examples:
        >>> doc = {"articleNo": 218, "body": "불법행위"}
        >>> prepare_document_for_indexing(doc)
        {"articleNo": 218, "body": "불법행위", "body_ngram": "불법 법행 행위 ..."}
    """
    doc = doc.copy()

    # body 필드에서 n-gram 생성
    body = doc.get("body", "")
    if body:
        doc["body_ngram"] = ko_ngram(body, n=(2, 3))
    else:
        doc["body_ngram"] = ""

    return doc


def batch_prepare_documents(docs: List[dict]) -> List[dict]:
    """
    여러 문서를 일괄 전처리

    Args:
        docs: 문서 리스트

    Returns:
        전처리된 문서 리스트
    """
    return [prepare_document_for_indexing(doc) for doc in docs]


# ============================================
# 예제 실행 (테스트용)
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("한글 n-gram 전처리 테스트")
    print("=" * 60)

    # 테스트 1: n-gram 생성
    test_texts = [
        "불법행위",
        "악의 또는 중대한 과실",
        "제218조",
        "점유"
    ]

    print("\n[테스트 1] n-gram 생성")
    for text in test_texts:
        ngram = ko_ngram(text, n=(2, 3))
        print(f"원문: {text}")
        print(f"n-gram: {ngram}")
        print()

    # 테스트 2: 조문 번호 파싱
    test_queries = [
        "218",
        "제218조",
        "제218조의2",
        "악의 또는 중대한 과실"
    ]

    print("\n[테스트 2] 조문 번호 파싱")
    for query in test_queries:
        result = normalize_article_query(query)
        print(f"검색어: {query}")
        print(f"결과: {result}")
        print()

    # 테스트 3: 문서 전처리
    test_doc = {
        "articleNo": 218,
        "heading": "제218조(불법행위)",
        "body": "악의 또는 중대한 과실로 타인의 권리를 침해한 자는 손해를 배상할 책임이 있다."
    }

    print("\n[테스트 3] 문서 전처리")
    prepared = prepare_document_for_indexing(test_doc)
    print(f"원본 body: {test_doc['body']}")
    print(f"body_ngram: {prepared['body_ngram'][:100]}...")
