FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .
COPY templates/ templates/
EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0"]