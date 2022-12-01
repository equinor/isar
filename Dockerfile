FROM python:3.10-slim

WORKDIR /app

ENV VIRTUAL_ENV=/venv
RUN python -m venv --copies $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m pip install --upgrade pip

# Install dependencies before ISAR to cache pip installation
RUN mkdir -p src
COPY setup.py README.md ./
RUN pip install .

# Install the base isar-robot package
RUN pip install isar-robot

COPY . .

RUN pip install .

EXPOSE 3000

# Env variable for ISAR to know it is running in docker
ENV IS_DOCKER=true

# # Add non-root user
RUN useradd --create-home --shell /bin/bash 1000
RUN chown -R 1000 /app
RUN chmod 755 /app
USER 1000

CMD python main.py
