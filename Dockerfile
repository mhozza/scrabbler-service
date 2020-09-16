FROM python:3.8-slim

WORKDIR /scrabbler

RUN apt-get update -y && \
    apt-get install -y gcc libffi-dev libssl-dev && \
    pip install --no-cache-dir --upgrade pip poetry && \
    poetry config virtualenvs.create false

COPY . /scrabbler/

RUN poetry install --no-interaction --no-root

CMD scrabbler_service/scrabble.py --port 9000 --lazy-init
