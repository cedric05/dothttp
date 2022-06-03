## Dothttp agent docs 

There is support for running http notebooks on `https://vscode.dev` with dothttp-agent. For running requests in notebook, vscode service will invoke api via `localhost:5000`.  With this, one reviewing requets or quickly making requets is far easier.

### RUN
To run agent via docker 

```shell
docker run --restart always -p 5000:5000 ghcr.io/cedric05/dothttp:latest
```

To run with python 

```shell
# install dependencies
python -m pip install dothttp-req --pre waitress flask flask-cors
# run flask app
python -m waitress --port 5000 dotextensions.server.agent:app
```