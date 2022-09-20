FROM python:3.10-slim

RUN apt-get update
RUN apt-get install -y git

WORKDIR /app

ENV VIRTUAL_ENV=/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m pip install --upgrade pip

# Install dependencies before ISAR to cache pip installation
RUN mkdir -p src
COPY setup.py README.md ./
RUN pip install .

COPY . .

RUN pip install -e .

EXPOSE 3000

# Env variable for ISAR to know it is running in docker
ENV IS_DOCKER=true

CMD python main.py
