FROM python:3.8-alpine

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app
#Add if running in VM --proxy="http://192.168.4.1:3128"
RUN pip install --proxy="http://192.168.4.1:3128" --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

COPY logfile.xsd /app
COPY src/ /app

CMD ["python3", "main.py"]
#CMD ["python3", "-m", "cProfile", "-o", "stats", "main.py"]
