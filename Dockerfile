FROM python:3
LABEL maintainer="Adam Frank afrank@mozilla.com"

WORKDIR /app

COPY . /app

RUN python setup.py build test install