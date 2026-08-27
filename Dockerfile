FROM python:3.12-slim
ENV PYTHONUNBUFFERED 1
WORKDIR /goetc
COPY requirements.txt /goetc/
RUN pip install -r requirements.txt
COPY . /goetc/
CMD gunicorn --bind 0.0.0.0:9300 --worker-tmp-dir /dev/shm --workers=2 --threads=4 --worker-class=gthread goetc.web:app
