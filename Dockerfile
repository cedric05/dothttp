ARG VARIANT="3.9"
FROM ghcr.io/cedric05/python3.9:main

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
