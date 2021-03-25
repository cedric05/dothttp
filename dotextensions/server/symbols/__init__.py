from typing import Optional

from dothttp.request_base import RequestCompiler


class allkey(dict):
    def get(self, key: str) -> Optional:
        ret_val = super().get(key)
        if (ret_val):
            return ret_val
        return ''


class FetchNames(RequestCompiler):

    def load(self):
        self.load_content()
        props = self.get_declared_props()
        for prop in props:
            self.properties[prop] = '""'
        super().load()
