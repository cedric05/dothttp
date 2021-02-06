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
1. variable substition with property file
1. generates curl from http for easy sharing



```
docker build -t dothttp .
whalebrew install dothttp
dothttp examples/dothttpazure.http
```

checkout [examples]('./examples/dothttpazure.http')

- [x] variable substitution
- [x] properties file
- [x] support various data types like json, text (headers should be added automatically)
- [ ] update README.md to explain syntax and examples to refer
- [x] tests
- [ ] integration tests
- [ ] file uploads
- [x] handle 200, 300, 400, 500 exception (user readable messages)
- [ ] output should have rolling output format
- [ ] multiple logging options ?
- [x] should handle exceptions, only message should be shown.
- [x] debug mode to show logs
- [ ] multi form upload
- [ ] basic auth
- [ ] aws auth
- [X] command line arguments to curl and to make http request
- [ ] easy installation package using pyinstaller, docker, brew
- [ ] language server?, formatting
