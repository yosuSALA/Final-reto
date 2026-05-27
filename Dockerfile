FROM python:3.11-slim

WORKDIR /app

# System deps needed by pdfplumber (MuPDF) and reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the rest of the project
COPY . .

# Directories written at runtime
RUN mkdir -p backend/test_pdfs backend/generated_reports /app/data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", "--port", "8000"]
