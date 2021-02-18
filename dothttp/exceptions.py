def exception_wrapper(message, ):
    def wrapper(cls):
        class exc(cls):
            def __init__(self, **kwargs):
                self.message = message.format(**kwargs)

        return exc

    return wrapper


@exception_wrapper("root dothttp exception")
class DotHttpException(Exception):
    pass


@exception_wrapper("incorrect paramter key: `{key}` value: `{value}` . message `{message}`")
class ParameterException(DotHttpException):
    pass


@exception_wrapper("error with httpfile message: `{message}`")
class HttpFileException(DotHttpException):
    pass


@exception_wrapper("http file: `{file}` http file not found")
class HttpFileNotFoundException(HttpFileException):
    pass


# TODO modify this to provide more information
@exception_wrapper("httpfile `{file}` syntax issue: {message}")
class HttpFileSyntaxException(HttpFileException):
    pass


@exception_wrapper('property json schema validation failed! file `{file}`')
class PropertyFileException(DotHttpException):
    pass


@exception_wrapper('property file `{propertyfile}` not found')
class PropertyFileNotFoundException(PropertyFileException):
    pass


@exception_wrapper('property file `{propertyfile}` is not a json file')
class PropertyFileNotJsonException(PropertyFileException):
    message = "property file is not a json file"


@exception_wrapper('Payload file `{datafile}` not found')
class DataFileNotFoundException(HttpFileException):
    message = "data file mentioned is not a valid"


@exception_wrapper('property `{var}` not defined in propertyfile/commandline/httpfile propertyfile:`{propertyfile}`')
class PropertyNotFoundException(PropertyFileException):
    pass


@exception_wrapper("error with command line property format, property `{prop}`")
class CommandLinePropError(DotHttpException):
    pass


@exception_wrapper("invalid payload")
class PayloadNotValidException(HttpFileException):
    pass


@exception_wrapper("invalid payload data, expected str,json payload: `{payload}`")
class PayloadDataNotValidException(PayloadNotValidException):
    pass
