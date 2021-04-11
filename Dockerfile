ARG VARIANT="3.9"
FROM python:${VARIANT}
LABEL io.whalebrew.config.networks '["host"]'
RUN pip install dothttp-req
ENTRYPOINT ["dothttp"]
CMD ["dothttp"]
