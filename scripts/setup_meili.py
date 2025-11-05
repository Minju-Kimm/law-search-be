#!/usr/bin/env python3
"""
Meilisearch 인덱스 설정 스크립트

한글 법령 검색에 최적화된 설정 적용:
- searchableAttributes 순서 지정
- typoTolerance 설정
- 동의어(synonyms) 등록
- filterableAttributes, sortableAttributes 설정

실행 방법:
    python scripts/setup_meili.py

환경변수 필요:
    MEILI_HOST, MEILI_KEY, MEILI_INDEX_CIVIL, MEILI_INDEX_CRIMINAL
"""
import os
import sys
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

# Meilisearch 연결 정보
MEILI_HOST = os.getenv("MEILI_HOST")
MEILI_KEY = os.getenv("MEILI_KEY")
MEILI_INDEX_CIVIL = os.getenv("MEILI_INDEX_CIVIL", "civil-articles")
MEILI_INDEX_CRIMINAL = os.getenv("MEILI_INDEX_CRIMINAL", "criminal-articles")

if not MEILI_HOST or not MEILI_KEY:
    print("❌ 환경변수 MEILI_HOST, MEILI_KEY가 설정되지 않았습니다.")
    sys.exit(1)


# ============================================
# 인덱스 설정 (한글 법령 검색 최적화)
# ============================================

INDEX_SETTINGS = {
    # 검색 대상 필드 (순서가 중요: 앞쪽 필드가 더 높은 가중치)
    "searchableAttributes": [
        "heading",      # 조문 제목 (최우선)
        "joCode",       # 조 코드 (숫자 검색에 중요)
        "body",         # 조문 본문
        "body_ngram"    # 본문 n-gram (부분 매칭)
    ],

    # 필터링 가능 필드
    "filterableAttributes": [
        "lawCode",
        "articleNo",
        "articleSubNo"
    ],

    # 정렬 가능 필드
    "sortableAttributes": [
        "articleNo",
        "articleSubNo"
    ],

    # 랭킹 규칙 (순서대로 적용)
    "rankingRules": [
        "words",                    # 검색어 단어 매칭 수
        "typo",                     # 오타 허용도
        "proximity",                # 검색어 단어 간 근접도
        "attribute",                # 필드 우선순위 (searchableAttributes 순서)
        "exactness",                # 정확도
        "desc(exact_article)",      # 조문 번호 정확 매칭 (커스텀 필드)
        "desc(score_boost)",        # 스코어 부스트 (커스텀 필드)
        "sort"                      # 사용자 지정 정렬
    ],

    # 오타 허용 설정
    "typoTolerance": {
        "enabled": True,
        "minWordSizeForTypos": {
            "oneTypo": 5,   # 5자 이상: 1개 오타 허용
            "twoTypos": 9   # 9자 이상: 2개 오타 허용
        },
        # 법령 용어는 오타 허용 제외
        "disableOnWords": [
            "제", "조", "항", "호", "목",
            "법", "률", "령", "규칙", "조례",
            "단서", "본문", "각호"
        ],
        # joCode는 정확한 매칭 필요
        "disableOnAttributes": ["joCode"]
    },

    # 동의어 사전 (법령 용어)
    "synonyms": {
        # 무효/취소 관련
        "무효": ["취소", "효력없음", "실효", "폐지"],
        "취소": ["무효", "해제", "철회", "파기"],
        "해제": ["취소", "철회", "종료", "폐기"],

        # 금전/채무 관련
        "상환": ["변제", "갚다", "지급", "반환"],
        "변제": ["상환", "갚다", "지급", "완납"],
        "담보": ["보증", "저당", "질권", "근저당"],
        "보증": ["담보", "보장", "연대보증", "물적담보"],

        # 계약 관련
        "계약": ["약정", "협약", "합의", "체결"],
        "약정": ["계약", "합의", "협의", "특약"],
        "합의": ["계약", "약정", "협의", "동의"],

        # 소유/점유 관련
        "소유": ["소유권", "보유", "소지", "점유"],
        "점유": ["소유", "보유", "소지", "관리"],
        "소유권": ["소유", "물권", "재산권", "점유권"],

        # 손해/배상 관련
        "손해": ["손실", "피해", "불이익", "침해"],
        "배상": ["보상", "변상", "손해배상", "금전배상"],
        "보상": ["배상", "변상", "보전", "전보"],

        # 권리/의무 관련
        "권리": ["권한", "자격", "청구권", "행사"],
        "의무": ["책임", "채무", "부담", "이행"],
        "책임": ["의무", "부담", "배상책임", "귀책"],

        # 동의/승낙 관련
        "동의": ["승낙", "합의", "허락", "동의서"],
        "승낙": ["동의", "허락", "허가", "인정"],

        # 상속/유증 관련
        "상속": ["승계", "유산", "상속인", "피상속인"],
        "유증": ["증여", "유언", "상속", "기증"],
        "증여": ["기증", "유증", "증여계약", "무상양도"],

        # 시효/기간 관련
        "시효": ["소멸시효", "취득시효", "제척기간", "기간"],
        "기간": ["기일", "시한", "기한", "만료"],

        # 하자/흠결 관련
        "하자": ["결함", "흠결", "하자담보", "무하자"],
        "결함": ["하자", "흠결", "불량", "결점"],

        # 형법 관련
        "범죄": ["범행", "위법", "불법행위", "형사사건"],
        "형": ["형벌", "처벌", "징역", "벌금"],
        "처벌": ["형벌", "형", "제재", "처분"],
        "징역": ["금고", "구금", "형", "실형"],

        # 고의/과실 관련
        "고의": ["의도적", "유의적", "의사", "범의"],
        "과실": ["부주의", "태만", "과실치상", "과실치사"],
        "악의": ["악의적", "고의", "해할의사", "해의"],

        # 절도/사기 관련
        "절도": ["절취", "도둑질", "훔침", "절도죄"],
        "사기": ["기망", "기만", "사취", "사기죄"],
        "횡령": ["배임", "착복", "유용", "횡령죄"],

        # 폭행/상해 관련
        "폭행": ["구타", "때림", "폭력", "폭행죄"],
        "상해": ["부상", "치상", "상처", "상해죄"],

        # 오타 커버 (자주 발생하는 오타)
        "소유관": ["소유권"],
        "계악": ["계약"],
        "변재": ["변제"],
        "담보ㅗ": ["담보"],
        "쉬소": ["취소"],
        "무효ㅗ": ["무효"],
        "악이": ["악의"],
        "과쉴": ["과실"]
    },

    # 디스플레이 필드 (모든 필드 반환)
    "displayedAttributes": ["*"],

    # 페이지네이션 설정
    "pagination": {
        "maxTotalHits": 10000
    }
}


def apply_settings_to_index(index_name: str, max_retries: int = 3) -> bool:
    """
    특정 인덱스에 설정 적용

    Args:
        index_name: 인덱스명
        max_retries: 재시도 횟수

    Returns:
        성공 여부
    """
    url = f"{MEILI_HOST}/indexes/{index_name}/settings"
    headers = {"Authorization": f"Bearer {MEILI_KEY}"}

    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n{'='*60}")
            print(f"📋 인덱스: {index_name}")
            print(f"🔧 설정 적용 중... (시도 {attempt}/{max_retries})")

            with httpx.Client(timeout=30.0) as client:
                # PATCH 요청으로 설정 업데이트
                response = client.patch(url, headers=headers, json=INDEX_SETTINGS)

                if response.status_code == 202:
                    # 태스크 대기
                    task_data = response.json()
                    task_uid = task_data.get("taskUid")
                    print(f"✅ 설정 적용 요청 성공 (Task UID: {task_uid})")

                    # 태스크 완료 대기
                    if task_uid is not None:
                        wait_for_task(index_name, task_uid)

                    # 적용된 설정 확인
                    verify_settings(index_name)
                    return True

                elif response.status_code == 404:
                    print(f"❌ 인덱스 '{index_name}'를 찾을 수 없습니다.")
                    print("💡 먼저 인덱스에 문서를 색인해야 합니다.")
                    return False

                else:
                    print(f"⚠️  예상치 못한 응답: {response.status_code}")
                    print(f"   응답 내용: {response.text}")

                    if attempt < max_retries:
                        wait_time = 2 ** attempt  # 지수 백오프
                        print(f"   {wait_time}초 후 재시도합니다...")
                        time.sleep(wait_time)
                    else:
                        return False

        except httpx.ConnectError as e:
            print(f"❌ 연결 실패: {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"   {wait_time}초 후 재시도합니다...")
                time.sleep(wait_time)
            else:
                print(f"💡 MEILI_HOST 환경변수를 확인하세요: {MEILI_HOST}")
                return False

        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"   {wait_time}초 후 재시도합니다...")
                time.sleep(wait_time)
            else:
                return False

    return False


def wait_for_task(index_name: str, task_uid: int, timeout: int = 30):
    """
    Meilisearch 태스크 완료 대기

    Args:
        index_name: 인덱스명
        task_uid: 태스크 UID
        timeout: 타임아웃 (초)
    """
    url = f"{MEILI_HOST}/tasks/{task_uid}"
    headers = {"Authorization": f"Bearer {MEILI_KEY}"}

    start_time = time.time()
    print(f"⏳ 태스크 완료 대기 중...")

    while time.time() - start_time < timeout:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)

                if response.status_code == 200:
                    task_data = response.json()
                    status = task_data.get("status")

                    if status == "succeeded":
                        print(f"✅ 태스크 완료")
                        return
                    elif status == "failed":
                        error = task_data.get("error", {})
                        print(f"❌ 태스크 실패: {error}")
                        return
                    else:
                        # 진행 중
                        time.sleep(1)
                else:
                    print(f"⚠️  태스크 상태 확인 실패: {response.status_code}")
                    return

        except Exception as e:
            print(f"⚠️  태스크 확인 중 오류: {e}")
            return

    print(f"⚠️  타임아웃: {timeout}초 초과")


def verify_settings(index_name: str):
    """
    적용된 설정 확인

    Args:
        index_name: 인덱스명
    """
    url = f"{MEILI_HOST}/indexes/{index_name}/settings"
    headers = {"Authorization": f"Bearer {MEILI_KEY}"}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)

            if response.status_code == 200:
                settings = response.json()
                print(f"\n📊 적용된 설정 확인:")
                print(f"   - searchableAttributes: {settings.get('searchableAttributes', [])[:2]}...")
                print(f"   - filterableAttributes: {settings.get('filterableAttributes', [])}")
                print(f"   - rankingRules: {len(settings.get('rankingRules', []))}개")
                print(f"   - synonyms: {len(settings.get('synonyms', {}))}개")
                print(f"   - typoTolerance: enabled={settings.get('typoTolerance', {}).get('enabled', False)}")
            else:
                print(f"⚠️  설정 확인 실패: {response.status_code}")

    except Exception as e:
        print(f"⚠️  설정 확인 중 오류: {e}")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🚀 Meilisearch 인덱스 설정 스크립트")
    print("=" * 60)
    print(f"📍 호스트: {MEILI_HOST}")
    print(f"📋 대상 인덱스:")
    print(f"   - {MEILI_INDEX_CIVIL}")
    print(f"   - {MEILI_INDEX_CRIMINAL}")
    print()

    # 헬스 체크
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{MEILI_HOST}/health")
            if response.status_code != 200:
                print(f"❌ Meilisearch 서버 응답 없음: {response.status_code}")
                sys.exit(1)
        print("✅ Meilisearch 서버 연결 성공\n")
    except Exception as e:
        print(f"❌ Meilisearch 서버 연결 실패: {e}")
        print(f"💡 MEILI_HOST를 확인하세요: {MEILI_HOST}")
        sys.exit(1)

    # 각 인덱스에 설정 적용
    results = {}
    for index_name in [MEILI_INDEX_CIVIL, MEILI_INDEX_CRIMINAL]:
        success = apply_settings_to_index(index_name)
        results[index_name] = success

    # 최종 결과
    print("\n" + "=" * 60)
    print("📊 최종 결과")
    print("=" * 60)

    all_success = True
    for index_name, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{status} - {index_name}")
        if not success:
            all_success = False

    if all_success:
        print("\n🎉 모든 인덱스 설정이 완료되었습니다!")
        print("\n💡 다음 단계:")
        print("   1. 문서 색인 시 body_ngram 필드 추가")
        print("   2. 기존 문서 재색인 (필요시)")
        print("   3. 검색 테스트 실행")
        sys.exit(0)
    else:
        print("\n⚠️  일부 인덱스 설정이 실패했습니다.")
        print("\n🔧 문제 해결:")
        print("   1. 인덱스가 존재하는지 확인 (문서가 색인되어 있어야 함)")
        print("   2. MEILI_KEY 권한 확인 (master key 필요)")
        print("   3. Meilisearch 로그 확인")
        sys.exit(1)


if __name__ == "__main__":
    main()
