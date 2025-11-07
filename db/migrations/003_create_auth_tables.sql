-- Migration: Create users and bookmarks tables for OAuth authentication
-- Date: 2025-11-07

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    provider VARCHAR(50) NOT NULL,
    provider_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_provider_user UNIQUE (provider, provider_id)
);

CREATE INDEX idx_users_email ON users(email);

-- Create bookmarks table
CREATE TABLE IF NOT EXISTS bookmarks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    law_code VARCHAR(50) NOT NULL,
    article_no INTEGER NOT NULL,
    article_sub_no INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_bookmark UNIQUE (user_id, law_code, article_no, article_sub_no)
);

CREATE INDEX idx_bookmarks_user_id ON bookmarks(user_id);
CREATE INDEX idx_bookmarks_law_article ON bookmarks(law_code, article_no, article_sub_no);

-- Add comment
COMMENT ON TABLE users IS 'OAuth authenticated users';
COMMENT ON TABLE bookmarks IS 'User bookmarked law articles';
