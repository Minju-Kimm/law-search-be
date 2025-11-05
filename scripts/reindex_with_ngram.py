#!/usr/bin/env python3
"""
기존 문서에 body_ngram 필드 추가 (재색인)

PostgreSQL에서 데이터를 읽어 body_ngram을 생성하고
Meilisearch에 재색인합니다.

실행 방법:
    python scripts/reindex_with_ngram.py

환경변수 필요:
    MEILI_HOST, MEILI_KEY, DATABASE_URL
"""
import os
import sys
import time
import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.textproc import prepare_document_for_indexing

load_dotenv()

MEILI_HOST = os.getenv("MEILI_HOST")
MEILI_KEY = os.getenv("MEILI_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

INDEXES = {
    "CIVIL_CODE": os.getenv("MEILI_INDEX_CIVIL", "civil-articles"),
    "CRIMINAL_CODE": os.getenv("MEILI_INDEX_CRIMINAL", "criminal-articles")
}

BATCH_SIZE = 500  # 한 번에 색인할 문서 수


def fetch_documents_from_db(law_code: str):
    """
    PostgreSQL에서 문서 가져오기

    Args:
        law_code: 법령 코드 (CIVIL_CODE, CRIMINAL_CODE)

    Returns:
        문서 리스트
    """
    engine = create_engine(DATABASE_URL)

    query = text("""
        SELECT
            law_code as "lawCode",
            article_no as "articleNo",
            article_sub_no as "articleSubNo",
            jo_code as "joCode",
            heading,
            body,
            notes,
            clauses
        FROM articles
        WHERE law_code = :law_code
        ORDER BY article_no, article_sub_no
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"law_code": law_code})
            docs = []
            for row in result:
                doc = dict(row._mapping)
                # JSONB 필드는 그대로 유지
                docs.append(doc)

        return docs

    except Exception as e:
        print(f"❌ DB 조회 실패: {e}")
        return []


def reindex_to_meilisearch(index_name: str, docs: list, batch_size: int = BATCH_SIZE):
    """
    Meilisearch에 재색인 (배치 처리)

    Args:
        index_name: 인덱스명
        docs: 문서 리스트
        batch_size: 배치 크기

    Returns:
        성공 여부
    """
    if not docs:
        print("⚠️  색인할 문서가 없습니다.")
        return False

    # body_ngram 추가
    print(f"⚙️  body_ngram 생성 중... ({len(docs)}개 문서)")
    prepared_docs = []
    for i, doc in enumerate(docs):
        prepared = prepare_document_for_indexing(doc)
        prepared_docs.append(prepared)

        if (i + 1) % 100 == 0:
            print(f"   처리 중: {i + 1}/{len(docs)}")

    print(f"✅ body_ngram 생성 완료")

    # 배치로 나누어 색인
    total_batches = (len(prepared_docs) + batch_size - 1) // batch_size
    print(f"📦 배치 색인 시작 (배치 크기: {batch_size}, 총 {total_batches}개 배치)")

    url = f"{MEILI_HOST}/indexes/{index_name}/documents"
    headers = {"Authorization": f"Bearer {MEILI_KEY}"}

    task_uids = []

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, len(prepared_docs))
        batch = prepared_docs[start_idx:end_idx]

        print(f"\n📤 배치 {batch_idx + 1}/{total_batches} 색인 중... ({len(batch)}개 문서)")

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=headers, json=batch)

                if response.status_code == 202:
                    task_data = response.json()
                    task_uid = task_data.get("taskUid")
                    task_uids.append(task_uid)
                    print(f"✅ 배치 색인 요청 성공 (Task UID: {task_uid})")
                else:
                    print(f"❌ 배치 색인 실패: {response.status_code}")
                    print(f"   응답: {response.text[:200]}")
                    return False

        except Exception as e:
            print(f"❌ 배치 색인 중 오류: {e}")
            return False

        # 배치 간 지연 (서버 부하 방지)
        if batch_idx < total_batches - 1:
            time.sleep(0.5)

    # 모든 태스크 완료 대기
    print(f"\n⏳ 색인 태스크 완료 대기 중... ({len(task_uids)}개)")
    all_succeeded = wait_for_tasks(task_uids)

    if all_succeeded:
        print(f"✅ 모든 배치 색인 완료")
        return True
    else:
        print(f"⚠️  일부 배치 색인 실패")
        return False


def wait_for_tasks(task_uids: list, timeout: int = 300):
    """
    여러 태스크 완료 대기

    Args:
        task_uids: 태스크 UID 리스트
        timeout: 타임아웃 (초)

    Returns:
        모든 태스크 성공 여부
    """
    start_time = time.time()
    pending_tasks = set(task_uids)

    while pending_tasks and (time.time() - start_time < timeout):
        for task_uid in list(pending_tasks):
            url = f"{MEILI_HOST}/tasks/{task_uid}"
            headers = {"Authorization": f"Bearer {MEILI_KEY}"}

            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(url, headers=headers)

                    if response.status_code == 200:
                        task_data = response.json()
                        status = task_data.get("status")

                        if status == "succeeded":
                            pending_tasks.remove(task_uid)
                            print(f"   ✅ Task {task_uid} 완료")
                        elif status == "failed":
                            error = task_data.get("error", {})
                            print(f"   ❌ Task {task_uid} 실패: {error}")
                            pending_tasks.remove(task_uid)
                            return False

            except Exception as e:
                print(f"   ⚠️  Task {task_uid} 확인 중 오류: {e}")

        if pending_tasks:
            time.sleep(2)

    if pending_tasks:
        print(f"⚠️  타임아웃: {len(pending_tasks)}개 태스크 미완료")
        return False

    return True


def verify_index(index_name: str, expected_count: int):
    """
    인덱스 색인 결과 확인

    Args:
        index_name: 인덱스명
        expected_count: 예상 문서 수
    """
    url = f"{MEILI_HOST}/indexes/{index_name}/stats"
    headers = {"Authorization": f"Bearer {MEILI_KEY}"}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)

            if response.status_code == 200:
                stats = response.json()
                doc_count = stats.get("numberOfDocuments", 0)
                print(f"\n📊 인덱스 통계:")
                print(f"   - 문서 수: {doc_count} / {expected_count}")
                print(f"   - 색인 중: {stats.get('isIndexing', False)}")

                if doc_count >= expected_count:
                    print(f"   ✅ 색인 완료 확인")
                else:
                    print(f"   ⚠️  문서 수가 예상보다 적습니다")

            else:
                print(f"⚠️  통계 확인 실패: {response.status_code}")

    except Exception as e:
        print(f"⚠️  통계 확인 중 오류: {e}")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🔄 Meilisearch 재색인 스크립트 (body_ngram 추가)")
    print("=" * 60)
    print(f"📍 호스트: {MEILI_HOST}")
    print(f"📋 대상 인덱스:")
    for law_code, index_name in INDEXES.items():
        print(f"   - {law_code} → {index_name}")
    print()

    # 환경변수 확인
    if not all([MEILI_HOST, MEILI_KEY, DATABASE_URL]):
        print("❌ 환경변수가 설정되지 않았습니다:")
        print("   - MEILI_HOST")
        print("   - MEILI_KEY")
        print("   - DATABASE_URL")
        sys.exit(1)

    # Meilisearch 헬스체크
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{MEILI_HOST}/health")
            if response.status_code != 200:
                print(f"❌ Meilisearch 서버 응답 없음: {response.status_code}")
                sys.exit(1)
        print("✅ Meilisearch 서버 연결 성공\n")
    except Exception as e:
        print(f"❌ Meilisearch 서버 연결 실패: {e}")
        sys.exit(1)

    # 각 법령별 재색인
    results = {}

    for law_code, index_name in INDEXES.items():
        print(f"\n{'='*60}")
        print(f"📋 {law_code} → {index_name}")
        print("=" * 60)

        # DB에서 문서 가져오기
        print(f"📥 PostgreSQL에서 데이터 가져오는 중...")
        docs = fetch_documents_from_db(law_code)

        if not docs:
            print(f"⚠️  문서가 없거나 조회 실패")
            results[index_name] = False
            continue

        print(f"✅ 문서 {len(docs)}개 가져옴")

        # 재색인
        success = reindex_to_meilisearch(index_name, docs)
        results[index_name] = success

        if success:
            # 색인 결과 확인
            verify_index(index_name, len(docs))

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
        print("\n🎉 모든 재색인이 완료되었습니다!")
        print("\n💡 다음 단계:")
        print("   1. 검색 테스트 실행")
        print("   2. body_ngram 필드 확인")
        print("   3. 검색 품질 개선 확인")
        sys.exit(0)
    else:
        print("\n⚠️  일부 재색인이 실패했습니다.")
        print("\n🔧 문제 해결:")
        print("   1. Meilisearch 로그 확인")
        print("   2. 디스크 용량 확인")
        print("   3. 인덱스 설정 확인 (scripts/setup_meili.py)")
        sys.exit(1)


if __name__ == "__main__":
    main()
