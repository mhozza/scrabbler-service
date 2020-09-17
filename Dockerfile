FROM python:3.8-slim

WORKDIR /scrabbler

RUN apt-get update -y && \
    apt-get install -y gcc libffi-dev libssl-dev && \
    pip install --no-cache-dir --upgrade pip poetry && \
    poetry config virtualenvs.create false

COPY ./pyproject.toml .
COPY ./poetry.lock .

RUN poetry install --no-interaction --no-root

COPY . .

RUN apt-get purge -y --auto-remove gcc libffi-dev && \
    apt-get clean -y

CMD scrabbler_service/scrabbler_service.py --port 9000 --lazy-init
