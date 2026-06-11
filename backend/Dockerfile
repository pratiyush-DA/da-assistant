FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    wget \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

# Pre-download embedding model so first document ingest is not blocked for minutes
ENV HF_HOME=/data/hf_cache
RUN mkdir -p /data/hf_cache \
    && python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-large-en-v1.5')"

# Warm unstructured layout detector for hi_res PDF image OCR (best-effort)
RUN python -c "import os; os.environ.setdefault('EXTRACT_IMAGE_BLOCK_CROP_HORIZONTAL_PAD','20'); os.environ.setdefault('EXTRACT_IMAGE_BLOCK_CROP_VERTICAL_PAD','10'); from unstructured.partition.pdf import partition_pdf; print('unstructured inference ready')" \
    || echo "hi_res model preload skipped (optional)"

COPY . .

RUN mkdir -p /data/uploads

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
