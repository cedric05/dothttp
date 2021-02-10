FROM ghcr.io/cedric05/python3.9:main as builder

LABEL maintainer="kesavarapu.siva@gmail.com"

# whalebrew recommendations, won't harm any mainstream flow
LABEL io.whalebrew.config.networks '["host"]'
LABEL io.whalebrew.config.environment '["PYTHONPATH=/app"]'
LABEL io.whalebrew.config.working_dir '/work'

# install pipenv first
RUN pip install pipenv
WORKDIR /app
# install dependencies
COPY Pipfile.lock Pipfile /app/
RUN pipenv install --system --deploy
# as a final step, add source
ADD . /app 
# entrypoint or command
# ENTRYPOINT [ "bash" ]
ENTRYPOINT ["python", "-m", "dothttp"]

FROM builder
RUN pipenv install --dev --system
RUN apt update && apt install zip
RUN pyinstaller dothttp-cli.spec && cd dist/ && zip -r ../dothttp-cli.zip dothttp-cli/ && cd .. && rm -rf dist build
