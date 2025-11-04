-- ============================================
-- 법령 검색 시스템 DB 스키마
-- ============================================

-- 1) 법령 테이블
CREATE TABLE IF NOT EXISTS law (
    id         BIGSERIAL PRIMARY KEY,
    code       TEXT NOT NULL UNIQUE,  -- 예: 'CIVIL_CODE', 'CRIMINAL_CODE'
    name_ko    TEXT NOT NULL,         -- 예: '민법', '형법'
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_law_code ON law(code);

-- 2) 조문 테이블
CREATE TABLE IF NOT EXISTS article (
    id             BIGSERIAL PRIMARY KEY,
    law_id         BIGINT NOT NULL REFERENCES law(id) ON DELETE CASCADE,
    article_no     INT NOT NULL,
    article_sub_no INT NOT NULL DEFAULT 0,
    jo_code        CHAR(6) NOT NULL,      -- '000100' = 1조0, '010203' = 102조3
    heading        TEXT,                  -- 예: '제1조(목적)'
    body           TEXT NOT NULL,
    notes          TEXT[] DEFAULT '{}',   -- 예: ['[전문개정 2023.03.14]']
    clauses_json   JSONB,                 -- 항/호/목 구조화 데이터
    search_text    TEXT,                  -- 검색용 정규화 텍스트
    source_hash    TEXT,                  -- 본문 해시 (변경 감지용)
    created_at     TIMESTAMP DEFAULT now(),
    updated_at     TIMESTAMP DEFAULT now()
);

-- 유니크 제약: 동일 법령 내에서 (조번호, 조의번호)는 유일
CREATE UNIQUE INDEX IF NOT EXISTS idx_article_unique
    ON article(law_id, article_no, article_sub_no);

-- 조회용 인덱스
CREATE INDEX IF NOT EXISTS idx_article_jo_code ON article(jo_code);
CREATE INDEX IF NOT EXISTS idx_article_no_sub ON article(article_no, article_sub_no);
CREATE INDEX IF NOT EXISTS idx_article_law_id ON article(law_id);

-- 전문 검색용 GIN 인덱스 (PostgreSQL full-text search)
CREATE INDEX IF NOT EXISTS idx_article_search_text
    ON article USING GIN (to_tsvector('simple', COALESCE(search_text, '')));

-- 3) 법령 초기 데이터 삽입 (idempotent)
INSERT INTO law (code, name_ko) VALUES ('CIVIL_CODE', '민법')
    ON CONFLICT (code) DO NOTHING;

INSERT INTO law (code, name_ko) VALUES ('CRIMINAL_CODE', '형법')
    ON CONFLICT (code) DO NOTHING;

-- 4) 업데이트 타임스탬프 자동 갱신 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 적용
DROP TRIGGER IF EXISTS update_law_updated_at ON law;
CREATE TRIGGER update_law_updated_at
    BEFORE UPDATE ON law
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_article_updated_at ON article;
CREATE TRIGGER update_article_updated_at
    BEFORE UPDATE ON article
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 완료
-- ============================================
