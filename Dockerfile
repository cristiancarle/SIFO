FROM python:3-slim

WORKDIR /app

COPY . .

EXPOSE 5000

CMD ["python3", "app.py"]
