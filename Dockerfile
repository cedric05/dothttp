FROM python:3.8
LABEL io.whalebrew.config.networks '["host"]'
ADD requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt
COPY dothttp /app/dothttp
COPY dotextensions /app/dotextensions
COPY setup.py README.md  /app/
RUN ls && python setup.py install
RUN pip install flask flask-cors waitress
ENTRYPOINT ["python"]
CMD ["-m", "waitress", "--port", "5000", "dotextensions.server.agent:app"]
EXPOSE 5000
