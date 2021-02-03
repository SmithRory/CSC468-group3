FROM python:latest

RUN mkdir /app

WORKDIR /app

COPY requirements.txt /app
COPY src/ /app

RUN pip install -r requirements.txt

CMD ["python3", "main.py"]