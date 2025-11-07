# OAuth Authentication Setup Guide

이 문서는 FastAPI에 통합된 Google 및 Naver OAuth 인증 설정 가이드입니다.

## 목차
- [기능 개요](#기능-개요)
- [OAuth 제공자 설정](#oauth-제공자-설정)
- [환경 변수 설정](#환경-변수-설정)
- [API 엔드포인트](#api-엔드포인트)
- [프론트엔드 통합](#프론트엔드-통합)
- [데이터베이스 마이그레이션](#데이터베이스-마이그레이션)

## 기능 개요

### 구현된 기능
- ✅ Google OAuth 2.0 (OIDC) 로그인
- ✅ Naver OAuth 2.0 로그인
- ✅ JWT 기반 세션 관리
- ✅ HttpOnly 쿠키 (XSS 방지)
- ✅ 사용자 자동 생성/업데이트 (upsert)
- ✅ 북마크 CRUD (법령 조문 저장)
- ✅ 보호된 엔드포인트 (`/me`, `/bookmarks`)

### 보안 기능
- **HttpOnly Cookie**: XSS 공격 방지
- **SameSite=Lax**: CSRF 공격 완화
- **Secure Flag**: Production에서 HTTPS 전용
- **JWT 만료**: 7일 자동 만료
- **CORS Whitelist**: 허용된 도메인만 접근

## OAuth 제공자 설정

### 1. Google OAuth 설정

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 생성 또는 선택
3. **APIs & Services** > **Credentials** 이동
4. **Create Credentials** > **OAuth 2.0 Client ID** 선택
5. Application type: **Web application**
6. Authorized redirect URIs 추가:
   ```
   http://localhost:8080/api/auth/auth/google
   https://yourdomain.com/api/auth/auth/google
   ```
7. Client ID와 Client Secret 복사

### 2. Naver OAuth 설정

1. [Naver Developers](https://developers.naver.com/apps/#/register) 접속
2. 애플리케이션 등록
3. **사용 API**: 네이버 로그인
4. **제공 정보**: 이메일, 이름
5. **Callback URL** 설정:
   ```
   http://localhost:8080/api/auth/auth/naver
   https://yourdomain.com/api/auth/auth/naver
   ```
6. Client ID와 Client Secret 복사

## 환경 변수 설정

`.env` 파일 생성 (`.env.example` 참고):

```bash
# OAuth Credentials
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
NAVER_CLIENT_ID=your-naver-client-id
NAVER_CLIENT_SECRET=your-naver-client-secret

# JWT & Session
JWT_SECRET=your-super-secret-jwt-key-min-32-chars
SESSION_SECRET=your-super-secret-session-key-min-32-chars

# Frontend
FRONTEND_URL=http://localhost:3000

# Environment
ENV=development  # or production
DEBUG=true

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

## API 엔드포인트

### 인증 관련

#### 1. 로그인 시작
```http
GET /api/auth/login/{provider}
```
- **Parameters**:
  - `provider`: `google` 또는 `naver`
- **Response**: OAuth 제공자 페이지로 리다이렉트

#### 2. OAuth 콜백 (자동 호출)
```http
GET /api/auth/auth/{provider}
```
- **Parameters**:
  - `provider`: `google` 또는 `naver`
- **Response**:
  - 성공: `{FRONTEND_URL}/auth/success` 리다이렉트 + JWT 쿠키 설정
  - 실패: `{FRONTEND_URL}/auth/error?message={error}` 리다이렉트

#### 3. 로그아웃
```http
POST /api/auth/logout
```
- **Response**: JWT 쿠키 삭제

### 사용자 관련

#### 4. 현재 사용자 정보
```http
GET /api/users/me
```
- **Headers**: Cookie에 `access_token` 필요
- **Response**:
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "홍길동",
  "provider": "google",
  "created_at": "2025-11-07T00:00:00Z"
}
```

### 북마크 관련

#### 5. 북마크 목록 조회
```http
GET /api/bookmarks
```
- **Headers**: Cookie에 `access_token` 필요
- **Response**:
```json
[
  {
    "id": 1,
    "lawCode": "CIVIL_CODE",
    "articleNo": 103,
    "articleSubNo": 0,
    "created_at": "2025-11-07T00:00:00Z"
  }
]
```

#### 6. 북마크 추가
```http
POST /api/bookmarks
Content-Type: application/json

{
  "lawCode": "CIVIL_CODE",
  "articleNo": 103,
  "articleSubNo": 0
}
```
- **Headers**: Cookie에 `access_token` 필요
- **Response**: 생성된 북마크 객체 (201 Created)

#### 7. 북마크 삭제
```http
DELETE /api/bookmarks/{bookmark_id}
```
- **Headers**: Cookie에 `access_token` 필요
- **Response**: 204 No Content

## 프론트엔드 통합

### 로그인 플로우

```javascript
// 1. 로그인 버튼 클릭
function loginWithGoogle() {
  window.location.href = 'http://localhost:8080/api/auth/login/google';
}

function loginWithNaver() {
  window.location.href = 'http://localhost:8080/api/auth/login/naver';
}

// 2. 성공 페이지 (/auth/success)에서 처리
// JWT는 자동으로 HttpOnly 쿠키에 저장됨
console.log('로그인 성공!');

// 3. API 호출 (쿠키 자동 전송)
fetch('http://localhost:8080/api/users/me', {
  credentials: 'include'  // 쿠키 포함 필수!
})
  .then(res => res.json())
  .then(user => console.log(user));
```

### CORS 설정 주의사항

프론트엔드에서 API 호출 시 **반드시** `credentials: 'include'` 옵션 사용:

```javascript
// Fetch API
fetch('http://localhost:8080/api/users/me', {
  credentials: 'include'
})

// Axios
axios.get('http://localhost:8080/api/users/me', {
  withCredentials: true
})
```

## 데이터베이스 마이그레이션

### 마이그레이션 실행

```bash
# PostgreSQL에 접속
psql -U your_user -d lawdb

# 마이그레이션 SQL 실행
\i db/migrations/003_create_auth_tables.sql
```

### 테이블 구조

#### `users` 테이블
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    provider VARCHAR(50) NOT NULL,
    provider_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_provider_user UNIQUE (provider, provider_id)
);
```

#### `bookmarks` 테이블
```sql
CREATE TABLE bookmarks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    law_code VARCHAR(50) NOT NULL,
    article_no INTEGER NOT NULL,
    article_sub_no INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_bookmark UNIQUE (user_id, law_code, article_no, article_sub_no)
);
```

## 프로덕션 체크리스트

- [ ] `.env` 파일에 실제 OAuth credentials 설정
- [ ] `JWT_SECRET`을 안전한 랜덤 문자열로 변경 (최소 32자)
- [ ] `SESSION_SECRET`을 안전한 랜덤 문자열로 변경
- [ ] `ENV=production` 설정
- [ ] `DEBUG=false` 설정
- [ ] CORS_ORIGINS에 실제 프론트엔드 도메인 설정
- [ ] OAuth 제공자에 프로덕션 콜백 URL 등록
- [ ] HTTPS 활성화 (Secure 쿠키 작동)
- [ ] 데이터베이스 백업 설정

## 트러블슈팅

### "Not authenticated" 에러
- 쿠키가 전송되지 않는 경우: `credentials: 'include'` 옵션 확인
- 쿠키가 만료된 경우: 다시 로그인

### OAuth 리다이렉트 에러
- 콜백 URL이 OAuth 제공자에 등록되어 있는지 확인
- URL이 정확히 일치하는지 확인 (trailing slash 주의)

### CORS 에러
- `CORS_ORIGINS`에 프론트엔드 도메인이 포함되어 있는지 확인
- `allow_credentials=True` 설정 확인

## 추가 참고 자료

- [Authlib Documentation](https://docs.authlib.org/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [Naver Login API](https://developers.naver.com/docs/login/overview/)
