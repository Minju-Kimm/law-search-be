# Dockerfile
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 시스템 패키지(필요시 확장)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# 라이브러리
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스
COPY . .

# 컨테이너 포트 (리버스 프록시 뒤에 숨기므로 외부에 바로 노출하진 않음)
EXPOSE 8080

# uvicorn 실행
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
