FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN mkdir -p /app/data
EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000
ENV DB_PATH=/app/data/agenda.db

CMD ["python3", "server.py"]
