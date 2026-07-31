FROM python:3.11-slim

# HF Spaces containers run as uid 1000 — create a matching user
RUN useradd -m -u 1000 user

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY backend/ .
RUN chown -R user:user /app

USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Listen on the platform-provided PORT (Render), defaulting to 7860 (Hugging Face Spaces)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
