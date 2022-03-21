FROM python:3.10-slim

RUN apt-get update
RUN apt-get install -y git

WORKDIR /app

# Default robot repository
ARG ROBOT_REPOSITORY_CLONE_URL=https://github.com/equinor/isar-robot.git

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
RUN pip install git+${ROBOT_REPOSITORY_CLONE_URL}@main

EXPOSE 3000

# Change user to avoid running as root
# User needs to have an explicit guid for radix
RUN useradd -ms /bin/bash --uid 1001 isar
RUN chown -R 1001 /app
RUN chmod 755 /app
USER 1001

CMD python main.py
