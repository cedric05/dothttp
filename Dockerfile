FROM python:3.14
LABEL io.whalebrew.config.networks '["host"]'
ADD pyproject.toml /app/
WORKDIR /app
RUN pip install poetry
RUN poetry config virtualenvs.create false 
RUN poetry install --all-extras --no-root
COPY dothttp /app/dothttp
COPY dotextensions /app/dotextensions
COPY README.md /app/
ENTRYPOINT ["python"]
CMD ["-m", "waitress", "--port", "5000", "dotextensions.server.agent:app"]
EXPOSE 5000
