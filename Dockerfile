FROM python

RUN pip3 install poetry
WORKDIR /app

COPY ./poetry.lock /app/
COPY ./pyproject.toml /app/
RUN poetry install --no-dev

COPY . /app/

CMD ["poetry", "run", "python3", "slack-client.py"]

