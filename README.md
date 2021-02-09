# Inspiration

With the rise in usage of microservices, using http/curl is essential part of most developer's jobs. There are multiple
options out there (some are curl, postmant) . My Ideal choice would be to use curl but problems with it is having no
history. Postman solves that problem but once user logs in, postman actually syncs it to their servers which i did not
like.

## GOAL

dothttp will provide simple, cleaner architecture for making http requests. It uses xtext (eclipse developed dsl) to
build a custom dsl.

## KICKSTART

```shell
git clone git@github.com:cedric05/dothttp.git
cd dothttp
```

### python3.9

```
python3 -m dothttp examples/dothttpazure.http
```

### docker

```
docker build -t dothttp .
docker run -it --rm dothttp
```

### whalebrew

## Features

1. easy and cleaner http syntax
1. variable substitution with property file
1. generates curl from http for easy sharing

```
docker build -t dothttp .
whalebrew install dothttp
dothttp examples/dothttpazure.http
```

## First DotHttpRequest and more

```get.http
GET "https://httpbin.org/get"
```

## Run

`dothttp simple.http`

prints

```json
{
  "args": {},
  "headers": {
    "Accept-Encoding": "identity",
    "Host": "httpbin.org",
    "User-Agent": "python-urllib3/1.26.3",
    "X-Amzn-Trace-Id": "Root=1-6022266a-20fb552e530ba3d90c75be6d"
  },
  "origin": "117.216.243.24",
  "url": "https://httpbin.org/get"
}
```

### POST request

```post.http
POST "https://httpbin.org/post"
```

```json
{
  "args": {},
  "data": "",
  "files": {},
  "form": {},
  "headers": {
    "Accept-Encoding": "identity",
    "Content-Length": "0",
    "Host": "httpbin.org",
    "User-Agent": "python-urllib3/1.26.3",
    "X-Amzn-Trace-Id": "Root=1-602228fa-3c3ed5213b6d8c2d2a223148"
  },
  "json": null,
  "origin": "117.216.243.24",
  "url": "https://httpbin.org/post"
}
```

similarly, other methods`GET, POST, OPTIONS, DELETE, CONNECT, PUT, HEAD, TRACE` support is available.

### Query

query params can be added to request by specifying
` query ( "key", "value")`
` ?  "key", "value"`
` ? "key": "value"`
` ? "key"= "value"`
all four are accepted. going with `query("hi", "hi2)` is more readable. `?"key"= "value"` is more concise

### Payload

user can specify payload by mentioning below four forms (for various scenarios).

- `data("ram")`

  user can also mention its `content-type` with
  `data("ram", "text/plain")`
- `data({"key": "value"})` for form input.
- `json({"key": "value"})` for json payload.
- `file("path/to/file", "type")` uploads file as payload (type is optional).
- `files(("photo", "path/to/file/photo.jpg", "image/jpeg"),
  ("photo details", '{"name":"prasanth"}', "application/json")   
  )`

  for multipart upload
  **dothttp** will figure out content type by going through file/data, when type is not mentioned.

### Comments

**dothttp** will use `#` for commenting entire line.

### Templating

```.http
POST 'https://httpbin.org/post'
? ("{{key}}", "{{value}}")
data('{"{{key}}" :"{{value}}"}', 'application/json')
```

- specify variable values through property file ([sample.json](./examples/.dothttp.json)).
    - user can define environments and can activate multiple environments at a time
    - **dothttp** by default will read variables from `"*"` section
    - for example
      `dothttp --property-file path/to/file.json --env ram chandra`

      will activate `*` section properties, `ram` section properties and `chandra` section properties
      `dothttp --env ram chandra`
      will activate `*` section properties, `ram` section properties and `chandra` section properties
      from `.dothttp.json` in httpfile name space
- through command line
  `dothttp --property key=ram value=ranga`
  will replace `{{ram}}` to `ranga` from the file
- through file itself. (will be helpful for default properties)

```
POST 'https://{{host=httpbin.org}}/post'
```

### Headers

User can define headers in below three formats

1. `header('content-type', 'application/json')` readable
2. `'content-type': 'application/json'` concise
3. property file `headers` section from property-file can also be used. in most scenarios, headers section will be
   common for a host. having them in property file would ease them.

### Authentication

- basic auth currently **dothttp** only supports basic auth. more are yet to come.

`basicauth('username','password')'` --> will compute add respective headers.

### Property file

```json
{
  "*": {
    "host": "httpbin.org"
  },
  "headers": {
    "content-type": "plain/text"
  },
  "preprod": {
    "host": "preprod.httpbin.org"
  }
}
```

#### Special sections in property file

1. `*` section in property file will be activated once user specifies property file if user didn't specifiy file
   and `.dothttp.json` exists, it will be activated
2. `headers` once a property file is activated. headers from property file will be added to request by default without
   user having to specify in `.http` file

### Command line options

```
usage: dothttp [-h] [--curl] [--property-file PROPERTY_FILE] [--no-cookie] [--env ENV [ENV ...]] [--debug] [--info] [--format] [--stdout]
               [--property PROPERTY [PROPERTY ...]]
               file

http requests for humans

optional arguments:
  -h, --help            show this help message and exit

general:
  --curl                generates curl script
  --no-cookie, -nc      cookie storage is disabled
  --debug, -d           debug will enable logs and exceptions
  --info, -i            more information
  file                  http file

property:
  --property-file PROPERTY_FILE, -p PROPERTY_FILE
                        property file
  --env ENV [ENV ...], -e ENV [ENV ...]
                        environment to select in property file. properties will be enabled on FIFO
  --property PROPERTY [PROPERTY ...]
                        list of property's

format:
  --format, -fmt        formatter
  --stdout              print to commandline
```

checkout [examples]('./examples/dothttpazure.http')
