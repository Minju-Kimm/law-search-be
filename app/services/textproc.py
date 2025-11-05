"""
텍스트 전처리 유틸리티

한국어 법률 문서 검색을 위한 텍스트 처리 함수들을 제공합니다.
"""
from typing import List


def ko_ngram(text: str, min_n: int = 2, max_n: int = 3) -> str:
    """
    한국어 텍스트를 N-gram으로 분할합니다.

    검색 정확도 향상을 위해 2-gram과 3-gram을 생성하여
    부분 매칭을 가능하게 합니다.

    Args:
        text: 입력 텍스트
        min_n: 최소 n-gram 크기 (기본값: 2)
        max_n: 최대 n-gram 크기 (기본값: 3)

    Returns:
        공백으로 구분된 n-gram 문자열

    Examples:
        >>> ko_ngram("불법행위", 2, 3)
        "불법 법행 행위 불법행 법행위"

        >>> ko_ngram("손해배상", 2, 3)
        "손해 해배 배상 손해배 해배상"

        >>> ko_ngram("제1조", 2, 3)
        "제1 1조 제1조"
    """
    if not text:
        return ""

    # 공백 제거
    text = text.strip()

    if len(text) < min_n:
        return text

    ngrams = []

    # n-gram 생성
    for n in range(min_n, max_n + 1):
        for i in range(len(text) - n + 1):
            gram = text[i:i + n]
            ngrams.append(gram)

    # 중복 제거 및 공백으로 결합
    return " ".join(sorted(set(ngrams)))


def extract_numbers(text: str) -> List[str]:
    """
    텍스트에서 숫자를 추출합니다.

    법률 조문 번호나 코드 검색에 유용합니다.

    Args:
        text: 입력 텍스트

    Returns:
        추출된 숫자 리스트

    Examples:
        >>> extract_numbers("제103조의2")
        ['103', '2']

        >>> extract_numbers("민법 750조")
        ['750']
    """
    import re
    numbers = re.findall(r'\d+', text)
    return numbers


def normalize_legal_term(text: str) -> str:
    """
    법률 용어를 정규화합니다.

    Args:
        text: 입력 텍스트

    Returns:
        정규화된 텍스트

    Examples:
        >>> normalize_legal_term("제 1 조 ( 목적 )")
        "제1조(목적)"

        >>> normalize_legal_term("제１조")  # 전각 숫자
        "제1조"
    """
    # 전각 숫자를 반각으로 변환
    text = text.translate(str.maketrans(
        '０１２３４５６７８９',
        '0123456789'
    ))

    # 불필요한 공백 제거
    import re
    text = re.sub(r'\s+', '', text)

    return text


def boost_query_numbers(query: str, boost_factor: float = 2.0) -> dict:
    """
    쿼리에서 숫자가 포함된 경우 가중치를 부여합니다.

    Args:
        query: 검색 쿼리
        boost_factor: 숫자 가중치 배수 (기본값: 2.0)

    Returns:
        {
            "has_numbers": bool,
            "numbers": List[str],
            "boost_factor": float
        }

    Examples:
        >>> boost_query_numbers("민법 750조")
        {"has_numbers": True, "numbers": ["750"], "boost_factor": 2.0}

        >>> boost_query_numbers("불법행위")
        {"has_numbers": False, "numbers": [], "boost_factor": 1.0}
    """
    numbers = extract_numbers(query)
    has_numbers = len(numbers) > 0

    return {
        "has_numbers": has_numbers,
        "numbers": numbers,
        "boost_factor": boost_factor if has_numbers else 1.0
    }
