FROM python:3
LABEL maintainer="Adam Frank afrank@mozilla.com"

WORKDIR /app
COPY . /app

RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-ansi --no-root
RUN poetry run tox

RUN poetry build