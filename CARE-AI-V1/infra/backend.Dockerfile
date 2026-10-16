FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY frontend /frontend
RUN mkdir -p /app/data
ENV CARE_AI_DB_PATH=/app/data/care_ai.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
