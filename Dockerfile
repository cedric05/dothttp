ARG VARIANT="3.9"
FROM python:${VARIANT}
RUN pip install pipenv
WORKDIR /app
ADD Pipfile.lock .
ADD Pipfile /app/
RUN pipenv install --system --deploy
ADD . /app
CMD ["python", "-m" , "dothttp", "examples/dothttpazure.http"]