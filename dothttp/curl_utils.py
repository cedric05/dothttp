# copied from https://github.com/ofw/curlify/
# visit https://github.com/ofw/curlify/blob/master/LICENSE for license

from shlex import quote

# for file input and multipart, rather than converting them to body, we use curl's actual syntax


def to_curl(url, method, bodydata=None):
    parts = []
    if isinstance(bodydata, list):
        for p in bodydata:
            parts.append(p)

    flat_parts = []
    for k, v in parts:
        if k and v:
            flat_parts.append(quote(k) + " " + quote(v))
        elif k:
            flat_parts.append(quote(k))
        elif v:
            flat_parts.append(quote(v))

    return f'curl -X {method} --url {url} \\\n' + ' \\\n'.join(flat_parts)
