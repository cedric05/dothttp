from ...server import BaseHandler, Command, Result


class SwaggerImporter(BaseHandler):
    name = "/import/2.0/swagger"

    def get_method(self):
        return SwaggerImporter.name

    def run(self, command: Command) -> Result:
        mode = command.params['mode']
        if mode == 'filename':
            self.import_file(command.params)
        else:
            self.import_link(command.params)

    def import_file(self, params):
        filename = params['filename']
        with open(filename) as f:
            data = f.read()

    def import_link(self, params):
        link = params['url']
