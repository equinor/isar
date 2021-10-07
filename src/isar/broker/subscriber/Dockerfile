FROM python:3.8-slim

ENV VIRTUAL_ENV "/venv"
RUN python -m venv $VIRTUAL_ENV
ENV PATH "$VIRTUAL_ENV/bin:$PATH"

WORKDIR /root

RUN mkdir subscriber
WORKDIR /root/subscriber

COPY ./ ./

RUN \
    pip3 install -r requirements.txt

EXPOSE 1883

ARG USER
ARG PASSWORD
ENV VERNEMQ_USER=$USER
ENV VERNEMQ_PASSWORD=$PASSWORD

# RUN useradd -u 8877 run_user
# USER run_user

CMD ["python", "-u","subscriber.py"]
