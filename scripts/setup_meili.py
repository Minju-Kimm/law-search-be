"""
Meilisearch 검색 정확도 개선 설정 스크립트

이 스크립트는 다음을 수행합니다:
1. searchableAttributes 우선순위 설정 (heading > joCode > body > body_ngram)
2. rankingRules 최적화
3. typoTolerance 설정
4. 법률 용어 synonyms 설정

사용법:
    python scripts/setup_meili.py
"""
import os
import sys
import httpx
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

MEILI_HOST = os.getenv("MEILI_HOST")
MEILI_KEY = os.getenv("MEILI_KEY")
MEILI_INDEX_CIVIL = os.getenv("MEILI_INDEX_CIVIL", "civil-articles")
MEILI_INDEX_CRIMINAL = os.getenv("MEILI_INDEX_CRIMINAL", "criminal-articles")


def patch_index_settings(index_name: str) -> bool:
    """
    특정 인덱스의 설정을 패치합니다.

    Args:
        index_name: 인덱스명

    Returns:
        True if successful, False otherwise
    """
    headers = {"Authorization": f"Bearer {MEILI_KEY}"}

    # 검색 정확도 향상을 위한 설정
    settings = {
        # 검색 대상 필드 우선순위 (높을수록 가중치↑)
        "searchableAttributes": [
            "heading",      # 1순위: 조문 제목 (예: 제1조(목적))
            "joCode",       # 2순위: 조 코드 (예: 000100)
            "body",         # 3순위: 조문 본문
            "body_ngram"    # 4순위: 본문 n-gram (부분 매칭용)
        ],

        # 랭킹 규칙 (위에서 아래 순서로 적용)
        "rankingRules": [
            "words",           # 쿼리 단어 매치 수
            "typo",            # 오타 허용 정도 (적을수록 높은 점수)
            "proximity",       # 쿼리 단어 간 근접도
            "attribute",       # searchableAttributes 우선순위
            "sort",            # 정렬 필드
            "exactness"        # 정확한 매치 우선
        ],

        # 오타 허용 설정
        "typoTolerance": {
            "enabled": True,
            "minWordSizeForTypos": {
                "oneTypo": 4,      # 4글자부터 오타 1개 허용
                "twoTypos": 8      # 8글자부터 오타 2개 허용
            },
            "disableOnWords": [],
            "disableOnAttributes": ["joCode"]  # 조 코드는 정확히 매치
        },

        # 동의어 설정 (법률 용어)
        "synonyms": {
            "불법행위": ["불법행위", "위법행위", "부법행위"],
            "채무": ["채무", "빚", "부채"],
            "채권": ["채권", "청구권"],
            "계약": ["계약", "약정", "합의"],
            "손해배상": ["손해배상", "배상", "손해배상청구"],
            "소유권": ["소유권", "소유"],
            "점유": ["점유", "소지"],
            "선의": ["선의", "善意"],
            "악의": ["악의", "惡意"],
            "과실": ["과실", "過失", "실수"],
            "고의": ["고의", "故意"],
            "무효": ["무효", "효력없음"],
            "취소": ["취소", "철회"],
            "해제": ["해제", "계약해제"],
            "해지": ["해지", "계약해지"],
            "상속": ["상속", "유산상속"],
            "증여": ["증여", "기증"],
            "매매": ["매매", "매도매수", "거래"],
            "임대차": ["임대차", "임대", "차가"],
            "저당권": ["저당권", "담보권"],
            "질권": ["질권", "질물"],
            "유치권": ["유치권", "유치"],
            "지역권": ["지역권", "통행권"],
            "지상권": ["지상권", "토지이용권"]
        },

        # 필터링 가능 필드
        "filterableAttributes": [
            "lawCode",
            "articleNo",
            "joCode"
        ],

        # 정렬 가능 필드
        "sortableAttributes": [
            "articleNo",
            "articleSubNo"
        ],

        # 분리 문자 설정 (법률 특수 문자 고려)
        "separatorTokens": [
            " ", "\n", "\t", ",", ".", "!", "?", ";", ":",
            "(", ")", "[", "]", "{", "}", "'", "\"",
            "、", "。", "「", "」", "『", "』"
        ]
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.patch(
                f"{MEILI_HOST}/indexes/{index_name}/settings",
                headers=headers,
                json=settings
            )

            if response.status_code == 202:
                print(f"✓ [{index_name}] 설정 패치 요청 성공 (taskUid: {response.json().get('taskUid')})")
                return True
            else:
                print(f"✗ [{index_name}] 설정 패치 실패: HTTP {response.status_code}")
                print(f"  응답: {response.text}")
                return False

    except Exception as e:
        print(f"✗ [{index_name}] 연결 오류: {str(e)}")
        return False


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("Meilisearch 검색 정확도 개선 설정 스크립트")
    print("=" * 60)
    print()

    # 환경변수 확인
    if not MEILI_HOST or not MEILI_KEY:
        print("✗ 오류: MEILI_HOST 또는 MEILI_KEY 환경변수가 설정되지 않았습니다.")
        print("  .env 파일을 확인해주세요.")
        sys.exit(1)

    print(f"Meilisearch Host: {MEILI_HOST}")
    print(f"Target Indexes: {MEILI_INDEX_CIVIL}, {MEILI_INDEX_CRIMINAL}")
    print()

    # 각 인덱스에 설정 적용
    indexes = [MEILI_INDEX_CIVIL, MEILI_INDEX_CRIMINAL]
    results = []

    for idx in indexes:
        print(f"[{idx}] 설정 적용 중...")
        success = patch_index_settings(idx)
        results.append((idx, success))
        print()

    # 결과 요약
    print("=" * 60)
    print("설정 적용 완료")
    print("=" * 60)

    success_count = sum(1 for _, s in results if s)
    total_count = len(results)

    for idx, success in results:
        status = "✓ 성공" if success else "✗ 실패"
        print(f"  {idx}: {status}")

    print()
    print(f"결과: {success_count}/{total_count} 인덱스 설정 완료")

    if success_count < total_count:
        sys.exit(1)

    print()
    print("💡 참고: 설정 적용 후 검색 결과에 반영되기까지 몇 초 소요될 수 있습니다.")


if __name__ == "__main__":
    main()
