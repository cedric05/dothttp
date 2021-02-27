# copied from https://github.com/ofw/curlify/
# visit https://github.com/ofw/curlify/blob/master/LICENSE for license

from shlex import quote


# for file input and multipart, rather than converting them to body, we use curl's actual syntax
def to_curl(request, bodydata=None):
    parts = []

    for k, v in sorted(request.headers.items()):
        parts += [('-H', '{0}: {1}'.format(k, v))]

    if request.body:
        body = request.body
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        parts += [('-d', body)]
    if isinstance(bodydata, list):
        for p in bodydata:
            parts.append(p)
    parts += [(None, request.url)]

    flat_parts = []
    for k, v in parts:
        if k and v:
            flat_parts.append(quote(k) + " " + quote(v))
        elif k:
            flat_parts.append(quote(k))
        elif v:
            flat_parts.append(quote(v))

    return f'curl -X {request.method} \\\n' + ' \\\n'.join(flat_parts)
