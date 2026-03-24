FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY game.py .

# Copy dictionary if present (optional — falls back to NLTK)
COPY sowpods.txt* ./

# HuggingFace Spaces expects the app to listen on port 7860
EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
