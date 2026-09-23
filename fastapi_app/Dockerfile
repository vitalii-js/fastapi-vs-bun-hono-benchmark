FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
COPY fastapi_app/requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt
COPY fastapi_app/main.py ./
COPY data ./data
ENV WORKERS=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS} --loop uvloop --http httptools --no-access-log --log-level warning"]
