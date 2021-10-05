FROM ubuntu:18.04

RUN apt-get update -y && \
    apt-get install -y python3-pip python3.7

ENV ENVIRONMENT=development

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY . /app

EXPOSE 5000
EXPOSE 80

ENTRYPOINT ["python3"]

CMD ["main.py"]
