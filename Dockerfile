FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY dbt ./dbt
COPY app ./app
COPY data ./data
RUN pip install --no-cache-dir .
EXPOSE 8501
CMD ["sh", "-c", "python -m clinical_pipeline run && streamlit run app/streamlit_app.py --server.address=0.0.0.0"]
