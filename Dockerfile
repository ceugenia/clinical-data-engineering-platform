FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CLINICAL_DATA_DIR=/app/data

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY dbt ./dbt
COPY app ./app
COPY docs ./docs

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

EXPOSE 8501

CMD ["sh", "-c", "python -m clinical_pipeline generate && python -m clinical_pipeline run --no-generate && streamlit run app/streamlit_app.py --server.address=0.0.0.0"]
