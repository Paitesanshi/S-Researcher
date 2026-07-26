FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt setup.py README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --no-deps -e .

COPY config/ ./config/
COPY examples/ ./examples/
COPY scripts/ ./scripts/
COPY researcher.sh LICENSE CITATION.cff REPRODUCIBILITY.md ./
RUN chmod +x researcher.sh scripts/*.sh

ENTRYPOINT ["./researcher.sh"]
CMD ["--help"]
