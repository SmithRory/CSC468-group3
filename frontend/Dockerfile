FROM python:latest

RUN mkdir /app

WORKDIR /app

COPY requirements.txt /app
COPY uwsgi.ini /app
COPY src/ /app

RUN pip install -r requirements.txt

CMD ["uwsgi", \
     "--manage-script-name", \
     "--mount", "/=main:app", \
     "uwsgi.ini"]