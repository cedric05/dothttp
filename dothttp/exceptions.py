def exception_wrapper(
    message,
):
    def wrapper(cls):
        class exc(cls):
            def __init__(self, **kwargs):
                self.message = message.format(**kwargs)
                self.kwargs = kwargs

        return exc

    return wrapper


@exception_wrapper("root dothttp exception")
class DotHttpException(Exception):
    def __str__(self) -> str:
        return self.message


class DothttpMultiExceptions(DotHttpException):
    def __init__(self, exceptions):
        self.exceptions = exceptions

    @property
    def message(self):
        return "\n".join([str(exception) for exception in self.exceptions])

    def __str__(self) -> str:
        return "\n".join([str(exception) for exception in self.exceptions])


@exception_wrapper(
    "http def with name `{base}` not defined for http  with name `{target}`"
)
class UndefinedHttpToExtend(DotHttpException):
    pass


@exception_wrapper(
    "incorrect paramter key: `{key}` value: `{value}` . message `{message}`"
)
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


@exception_wrapper("property json schema validation failed! file `{file}`")
class PropertyFileException(DotHttpException):
    pass


@exception_wrapper("property file `{propertyfile}` not found")
class PropertyFileNotFoundException(PropertyFileException):
    pass


@exception_wrapper("property file `{propertyfile}` is not a json file")
class PropertyFileNotJsonException(PropertyFileException):
    message = "property file is not a json file"


@exception_wrapper("Payload file `{datafile}` not found")
class DataFileNotFoundException(HttpFileException):
    message = "data file mentioned is not a valid"


@exception_wrapper(
    "property `{var}` not defined in propertyfile/commandline/httpfile propertyfile:`{propertyfile}`"
)
class PropertyNotFoundException(PropertyFileException):
    pass

@exception_wrapper(
    "index `{actual_key}` not found in `{indexed_value}` of target: `{target}`"
)
class VariableIndexNotAvailable(PropertyFileException):
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


@exception_wrapper("PreRequest Function:`{function}` failed with error: `{payload}`")
class PreRequestScriptException(DotHttpException):
    pass


@exception_wrapper("Python test function: `{function}` execution failed `{payload}`")
class ScriptException(DotHttpException):
    pass


@exception_wrapper(
    "AWSAuth expects all(access_id, secret_token, region, service) to be non empty access_id:`{access_id}`"
)
class DothttpAwsAuthException(DotHttpException):
    pass


@exception_wrapper("AzureAuth exception: {message}")
class DothttpAzureAuthException(DotHttpException):
    pass


@exception_wrapper("Certificate error: if you trust server provided certificate and not in cert chain, use `@insecure`")
class DothttpUnSignedCertException(DotHttpException):
    pass
