import json
import re
from json.encoder import _make_iterencode
from typing import Any, Iterator

try:
    from _json import make_encoder as c_make_encoder
except ImportError:
    c_make_encoder = None

INFINITY = float('inf')

ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\r\t]')
ESCAPE_DCT = {
    '\\': '\\\\',
    '\n': '\n',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\r': '\\r',
    '\t': '\\t',
}


def py_encode_basestring(s):
    """Return a JSON representation of a Python string

    """

    def replace(match):
        return ESCAPE_DCT[match.group(0)]

    return '"' + ESCAPE.sub(replace, s) + '"'


encode_basestring = (py_encode_basestring)


class JSONEncoder(json.JSONEncoder):
    def iterencode(self, o: Any, _one_shot: bool = ...) -> Iterator[str]:
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        if self.check_circular:
            markers = {}
        else:
            markers = None

        _encoder = encode_basestring

        def floatstr(o, allow_nan=self.allow_nan,
                     _repr=float.__repr__, _inf=INFINITY, _neginf=-INFINITY):
            # Check for specials.  Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on the
            # internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError(
                    "Out of range float values are not JSON compliant: " +
                    repr(o))

            return text

        if (_one_shot and c_make_encoder is not None
                and self.indent is None):
            _iterencode = c_make_encoder(
                markers, self.default, _encoder, self.indent,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, self.allow_nan)
        else:
            _iterencode = _make_iterencode(
                markers, self.default, _encoder, self.indent, floatstr,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, _one_shot)
        return _iterencode(o, 0)
