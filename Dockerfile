FROM python:3.10-slim

WORKDIR /app

ENV VIRTUAL_ENV=/venv
RUN python -m venv --copies $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m pip install --upgrade pip
RUN pip install poetry==1.7.0

# Install dependencies before ISAR to cache main dependencies
RUN mkdir -p src
COPY pyproject.toml poetry.lock README.md LICENSE ./
RUN poetry install --no-ansi --no-interaction --no-root --only main

# Install the base isar-robot package
RUN pip install isar-robot

COPY . .

RUN poetry install --no-ansi --no-interaction --only-root

EXPOSE 3000

# Env variable for ISAR to know it is running in docker
ENV IS_DOCKER=true

# # Add non-root user
RUN useradd --create-home --shell /bin/bash 1000
RUN chown -R 1000 /app
RUN chmod 755 /app
USER 1000

CMD python main.py
