FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY .env .

EXPOSE 6103

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "6103"] 