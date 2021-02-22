class DotHttpException(Exception):
    pass


class PropertyNotFound(DotHttpException):
    def __init__(self, var, args):
        message = f'{var} property not defined in {args.file}'
        super(PropertyNotFound, self).__init__(message)