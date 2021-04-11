FROM python:3.9
LABEL io.whalebrew.config.networks '["host"]'
RUN pip install dothttp-req
ENTRYPOINT ["dothttp"]
CMD ["dothttp"]
