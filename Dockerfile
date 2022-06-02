FROM python:3.10
LABEL io.whalebrew.config.networks '["host"]'
RUN pip install dothttp-req --pre
RUN pip install flask flask-cors
ENTRYPOINT ["python"]
CMD ["-m dotextensions.server http"]
