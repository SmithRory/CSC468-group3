FROM python:latest

RUN mkdir /app

WORKDIR /app

COPY requirements.txt /app
COPY logfile.xsd /app
COPY src/ /app

#Add if running in VM --proxy="http://192.168.4.1:3128"
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

EXPOSE 4444:4444

CMD ["python3", "main.py"]
