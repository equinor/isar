FROM python:3.10-slim AS builder

WORKDIR /app
RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc
RUN python -m pip install --upgrade pip

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies before ISAR to cache pip installation
COPY . .
RUN pip install .

# Install the base isar-robot package
RUN pip install isar-robot

FROM python:3.10-slim
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 3000

# Env variable for ISAR to know it is running in docker
ENV IS_DOCKER=true

# Add non-root user
RUN useradd --create-home --shell /bin/bash 1000
RUN chown -R 1000 /app
RUN chmod 755 /app
USER 1000

COPY . .
CMD python main.py
