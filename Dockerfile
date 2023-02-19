FROM python:3.11
RUN pip install -U pip poetry
RUN poetry config virtualenvs.create false
COPY ./pyproject.toml pyproject.toml
COPY ./crudapi crudapi
COPY ./README.md README.md
RUN poetry install --without dev
RUN pip install asyncpg
CMD ["python", "crudapi"]
