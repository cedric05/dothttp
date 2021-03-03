from enum import Enum
from typing import Optional, Dict, Any, Union, List, TypeVar, Callable, Type, cast

T = TypeVar("T")
EnumT = TypeVar("EnumT", bound=Enum)


def from_dict(f: Callable[[Any], T], x: Any) -> Dict[str, T]:
    assert isinstance(x, dict)
    return {k: f(v) for (k, v) in x.items()}


def from_none(x: Any) -> Any:
    assert x is None
    return x


def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except:
            pass
    assert False


def to_enum(c: Type[EnumT], x: Any) -> EnumT:
    assert isinstance(x, c)
    return x.value


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_bool(x: Any) -> bool:
    assert isinstance(x, bool)
    return x


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def from_float(x: Any) -> float:
    assert isinstance(x, (float, int)) and not isinstance(x, bool)
    return float(x)


def to_float(x: Any) -> float:
    assert isinstance(x, float)
    return x


class AuthType(Enum):
    APIKEY = "apikey"
    AWSV4 = "awsv4"
    BASIC = "basic"
    BEARER = "bearer"
    DIGEST = "digest"
    EDGEGRID = "edgegrid"
    HAWK = "hawk"
    NOAUTH = "noauth"
    NTLM = "ntlm"
    OAUTH1 = "oauth1"
    OAUTH2 = "oauth2"


class Auth:
    """Represents authentication helpers provided by Postman"""
    """The attributes for API Key Authentication. e.g. key, value, in."""
    apikey: Optional[Dict[str, Any]]
    """The attributes for [AWS
    Auth](http://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html). e.g.
    accessKey, secretKey, region, service.
    """
    awsv4: Optional[Dict[str, Any]]
    """The attributes for [Basic
    Authentication](https://en.wikipedia.org/wiki/Basic_access_authentication). e.g.
    username, password.
    """
    basic: Optional[Dict[str, Any]]
    """The attributes for [Bearer Token Authentication](https://tools.ietf.org/html/rfc6750).
    e.g. token.
    """
    bearer: Optional[Dict[str, Any]]
    """The attributes for [Digest
    Authentication](https://en.wikipedia.org/wiki/Digest_access_authentication). e.g.
    username, password, realm, nonce, nonceCount, algorithm, qop, opaque, clientNonce.
    """
    digest: Optional[Dict[str, Any]]
    """The attributes for [Akamai EdgeGrid
    Authentication](https://developer.akamai.com/legacy/introduction/Client_Auth.html). e.g.
    accessToken, clientToken, clientSecret, baseURL, nonce, timestamp, headersToSign.
    """
    edgegrid: Optional[Dict[str, Any]]
    """The attributes for [Hawk Authentication](https://github.com/hueniverse/hawk). e.g.
    authId, authKey, algorith, user, nonce, extraData, appId, delegation, timestamp.
    """
    hawk: Optional[Dict[str, Any]]
    noauth: Any
    """The attributes for [NTLM
    Authentication](https://msdn.microsoft.com/en-us/library/cc237488.aspx). e.g. username,
    password, domain, workstation.
    """
    ntlm: Optional[Dict[str, Any]]
    """The attributes for [OAuth1](https://oauth.net/1/). e.g. consumerKey, consumerSecret,
    token, tokenSecret, signatureMethod, timestamp, nonce, version, realm, encodeOAuthSign.
    """
    oauth1: Optional[Dict[str, Any]]
    """The attributes for [OAuth2](https://oauth.net/2/). e.g. accessToken, addTokenTo."""
    oauth2: Optional[Dict[str, Any]]
    type: AuthType

    def __init__(self, apikey: Optional[Dict[str, Any]], awsv4: Optional[Dict[str, Any]],
                 basic: Optional[Dict[str, Any]], bearer: Optional[Dict[str, Any]], digest: Optional[Dict[str, Any]],
                 edgegrid: Optional[Dict[str, Any]], hawk: Optional[Dict[str, Any]], noauth: Any,
                 ntlm: Optional[Dict[str, Any]], oauth1: Optional[Dict[str, Any]], oauth2: Optional[Dict[str, Any]],
                 type: AuthType) -> None:
        self.apikey = apikey
        self.awsv4 = awsv4
        self.basic = basic
        self.bearer = bearer
        self.digest = digest
        self.edgegrid = edgegrid
        self.hawk = hawk
        self.noauth = noauth
        self.ntlm = ntlm
        self.oauth1 = oauth1
        self.oauth2 = oauth2
        self.type = type

    @staticmethod
    def from_dict(obj: Any) -> 'Auth':
        assert isinstance(obj, dict)
        apikey = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("apikey"))
        awsv4 = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("awsv4"))
        basic = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("basic"))
        bearer = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("bearer"))
        digest = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("digest"))
        edgegrid = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("edgegrid"))
        hawk = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("hawk"))
        noauth = obj.get("noauth")
        ntlm = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("ntlm"))
        oauth1 = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("oauth1"))
        oauth2 = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("oauth2"))
        type = AuthType(obj.get("type"))
        return Auth(apikey, awsv4, basic, bearer, digest, edgegrid, hawk, noauth, ntlm, oauth1, oauth2, type)

    def to_dict(self) -> dict:
        result: dict = {}
        result["apikey"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.apikey)
        result["awsv4"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.awsv4)
        result["basic"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.basic)
        result["bearer"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.bearer)
        result["digest"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.digest)
        result["edgegrid"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.edgegrid)
        result["hawk"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.hawk)
        result["noauth"] = self.noauth
        result["ntlm"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.ntlm)
        result["oauth1"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.oauth1)
        result["oauth2"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.oauth2)
        result["type"] = to_enum(AuthType, self.type)
        return result


class PathClass:
    type: Optional[str]
    value: Optional[str]

    def __init__(self, type: Optional[str], value: Optional[str]) -> None:
        self.type = type
        self.value = value

    @staticmethod
    def from_dict(obj: Any) -> 'PathClass':
        assert isinstance(obj, dict)
        type = from_union([from_str, from_none], obj.get("type"))
        value = from_union([from_str, from_none], obj.get("value"))
        return PathClass(type, value)

    def to_dict(self) -> dict:
        result: dict = {}
        result["type"] = from_union([from_str, from_none], self.type)
        result["value"] = from_union([from_str, from_none], self.value)
        return result


class Description:
    """The content of the description goes here, as a raw string."""
    content: Optional[str]
    """Holds the mime type of the raw description content. E.g: 'text/markdown' or 'text/html'.
    The type is used to correctly render the description when generating documentation, or in
    the Postman app.
    """
    type: Optional[str]
    """Description can have versions associated with it, which should be put in this property."""
    version: Any

    def __init__(self, content: Optional[str], type: Optional[str], version: Any) -> None:
        self.content = content
        self.type = type
        self.version = version

    @staticmethod
    def from_dict(obj: Any) -> 'Description':
        assert isinstance(obj, dict)
        content = from_union([from_str, from_none], obj.get("content"))
        type = from_union([from_str, from_none], obj.get("type"))
        version = obj.get("version")
        return Description(content, type, version)

    def to_dict(self) -> dict:
        result: dict = {}
        result["content"] = from_union([from_str, from_none], self.content)
        result["type"] = from_union([from_str, from_none], self.type)
        result["version"] = self.version
        return result


class QueryParam:
    description: Union[Description, None, str]
    """If set to true, the current query parameter will not be sent with the request."""
    disabled: Optional[bool]
    key: Optional[str]
    value: Optional[str]

    def __init__(self, description: Union[Description, None, str], disabled: Optional[bool], key: Optional[str],
                 value: Optional[str]) -> None:
        self.description = description
        self.disabled = disabled
        self.key = key
        self.value = value

    @staticmethod
    def from_dict(obj: Any) -> 'QueryParam':
        assert isinstance(obj, dict)
        description = from_union([Description.from_dict, from_none, from_str], obj.get("description"))
        disabled = from_union([from_bool, from_none], obj.get("disabled"))
        key = from_union([from_none, from_str], obj.get("key"))
        value = from_union([from_none, from_str], obj.get("value"))
        return QueryParam(description, disabled, key, value)

    def to_dict(self) -> dict:
        result: dict = {}
        result["description"] = from_union([lambda x: to_class(Description, x), from_none, from_str], self.description)
        result["disabled"] = from_union([from_bool, from_none], self.disabled)
        result["key"] = from_union([from_none, from_str], self.key)
        result["value"] = from_union([from_none, from_str], self.value)
        return result


class VariableType(Enum):
    """A variable may have multiple types. This field specifies the type of the variable."""
    ANY = "any"
    BOOLEAN = "boolean"
    NUMBER = "number"
    STRING = "string"


class Variable:
    """Collection variables allow you to define a set of variables, that are a *part of the
    collection*, as opposed to environments, which are separate entities.
    *Note: Collection variables must not contain any sensitive information.*

    Using variables in your Postman requests eliminates the need to duplicate requests, which
    can save a lot of time. Variables can be defined, and referenced to from any part of a
    request.
    """
    description: Union[Description, None, str]
    disabled: Optional[bool]
    """A variable ID is a unique user-defined value that identifies the variable within a
    collection. In traditional terms, this would be a variable name.
    """
    id: Optional[str]
    """A variable key is a human friendly value that identifies the variable within a
    collection. In traditional terms, this would be a variable name.
    """
    key: Optional[str]
    """Variable name"""
    name: Optional[str]
    """When set to true, indicates that this variable has been set by Postman"""
    system: Optional[bool]
    """A variable may have multiple types. This field specifies the type of the variable."""
    type: Optional[VariableType]
    """The value that a variable holds in this collection. Ultimately, the variables will be
    replaced by this value, when say running a set of requests from a collection
    """
    value: Any

    def __init__(self, description: Union[Description, None, str], disabled: Optional[bool], id: Optional[str],
                 key: Optional[str], name: Optional[str], system: Optional[bool], type: Optional[VariableType],
                 value: Any) -> None:
        self.description = description
        self.disabled = disabled
        self.id = id
        self.key = key
        self.name = name
        self.system = system
        self.type = type
        self.value = value

    @staticmethod
    def from_dict(obj: Any) -> 'Variable':
        assert isinstance(obj, dict)
        description = from_union([Description.from_dict, from_none, from_str], obj.get("description"))
        disabled = from_union([from_bool, from_none], obj.get("disabled"))
        id = from_union([from_str, from_none], obj.get("id"))
        key = from_union([from_str, from_none], obj.get("key"))
        name = from_union([from_str, from_none], obj.get("name"))
        system = from_union([from_bool, from_none], obj.get("system"))
        type = from_union([VariableType, from_none], obj.get("type"))
        value = obj.get("value")
        return Variable(description, disabled, id, key, name, system, type, value)

    def to_dict(self) -> dict:
        result: dict = {}
        result["description"] = from_union([lambda x: to_class(Description, x), from_none, from_str], self.description)
        result["disabled"] = from_union([from_bool, from_none], self.disabled)
        result["id"] = from_union([from_str, from_none], self.id)
        result["key"] = from_union([from_str, from_none], self.key)
        result["name"] = from_union([from_str, from_none], self.name)
        result["system"] = from_union([from_bool, from_none], self.system)
        result["type"] = from_union([lambda x: to_enum(VariableType, x), from_none], self.type)
        result["value"] = self.value
        return result


class URLClass:
    """Contains the URL fragment (if any). Usually this is not transmitted over the network, but
    it could be useful to store this in some cases.
    """
    hash: Optional[str]
    """The host for the URL, E.g: api.yourdomain.com. Can be stored as a string or as an array
    of strings.
    """
    host: Union[List[str], None, str]
    path: Union[List[Union[PathClass, str]], None, str]
    """The port number present in this URL. An empty value implies 80/443 depending on whether
    the protocol field contains http/https.
    """
    port: Optional[str]
    """The protocol associated with the request, E.g: 'http'"""
    protocol: Optional[str]
    """An array of QueryParams, which is basically the query string part of the URL, parsed into
    separate variables
    """
    query: Optional[List[QueryParam]]
    """The string representation of the request URL, including the protocol, host, path, hash,
    query parameter(s) and path variable(s).
    """
    raw: Optional[str]
    """Postman supports path variables with the syntax `/path/:variableName/to/somewhere`. These
    variables are stored in this field.
    """
    variable: Optional[List[Variable]]

    def __init__(self, hash: Optional[str], host: Union[List[str], None, str],
                 path: Union[List[Union[PathClass, str]], None, str], port: Optional[str], protocol: Optional[str],
                 query: Optional[List[QueryParam]], raw: Optional[str], variable: Optional[List[Variable]]) -> None:
        self.hash = hash
        self.host = host
        self.path = path
        self.port = port
        self.protocol = protocol
        self.query = query
        self.raw = raw
        self.variable = variable

    @staticmethod
    def from_dict(obj: Any) -> 'URLClass':
        assert isinstance(obj, dict)
        hash = from_union([from_str, from_none], obj.get("hash"))
        host = from_union([lambda x: from_list(from_str, x), from_str, from_none], obj.get("host"))
        path = from_union(
            [lambda x: from_list(lambda x: from_union([PathClass.from_dict, from_str], x), x), from_str, from_none],
            obj.get("path"))
        port = from_union([from_str, from_none], obj.get("port"))
        protocol = from_union([from_str, from_none], obj.get("protocol"))
        query = from_union([lambda x: from_list(QueryParam.from_dict, x), from_none], obj.get("query"))
        raw = from_union([from_str, from_none], obj.get("raw"))
        variable = from_union([lambda x: from_list(Variable.from_dict, x), from_none], obj.get("variable"))
        return URLClass(hash, host, path, port, protocol, query, raw, variable)

    def to_dict(self) -> dict:
        result: dict = {}
        result["hash"] = from_union([from_str, from_none], self.hash)
        result["host"] = from_union([lambda x: from_list(from_str, x), from_str, from_none], self.host)
        result["path"] = from_union(
            [lambda x: from_list(lambda x: from_union([lambda x: to_class(PathClass, x), from_str], x), x), from_str,
             from_none], self.path)
        result["port"] = from_union([from_str, from_none], self.port)
        result["protocol"] = from_union([from_str, from_none], self.protocol)
        result["query"] = from_union([lambda x: from_list(lambda x: to_class(QueryParam, x), x), from_none], self.query)
        result["raw"] = from_union([from_str, from_none], self.raw)
        result["variable"] = from_union([lambda x: from_list(lambda x: to_class(Variable, x), x), from_none],
                                        self.variable)
        return result


class Script:
    """A script is a snippet of Javascript code that can be used to to perform setup or teardown
    operations on a particular response.
    """
    exec: Union[List[str], None, str]
    """A unique, user defined identifier that can  be used to refer to this script from requests."""
    id: Optional[str]
    """Script name"""
    name: Optional[str]
    src: Union[URLClass, None, str]
    """Type of the script. E.g: 'text/javascript'"""
    type: Optional[str]

    def __init__(self, exec: Union[List[str], None, str], id: Optional[str], name: Optional[str],
                 src: Union[URLClass, None, str], type: Optional[str]) -> None:
        self.exec = exec
        self.id = id
        self.name = name
        self.src = src
        self.type = type

    @staticmethod
    def from_dict(obj: Any) -> 'Script':
        assert isinstance(obj, dict)
        exec = from_union([lambda x: from_list(from_str, x), from_str, from_none], obj.get("exec"))
        id = from_union([from_str, from_none], obj.get("id"))
        name = from_union([from_str, from_none], obj.get("name"))
        src = from_union([URLClass.from_dict, from_str, from_none], obj.get("src"))
        type = from_union([from_str, from_none], obj.get("type"))
        return Script(exec, id, name, src, type)

    def to_dict(self) -> dict:
        result: dict = {}
        result["exec"] = from_union([lambda x: from_list(from_str, x), from_str, from_none], self.exec)
        result["id"] = from_union([from_str, from_none], self.id)
        result["name"] = from_union([from_str, from_none], self.name)
        result["src"] = from_union([lambda x: to_class(URLClass, x), from_str, from_none], self.src)
        result["type"] = from_union([from_str, from_none], self.type)
        return result


class Event:
    """Postman allows you to configure scripts to run when specific events occur. These scripts
    are stored here, and can be referenced in the collection by their ID.

    Defines a script associated with an associated event name
    """
    """Indicates whether the event is disabled. If absent, the event is assumed to be enabled."""
    disabled: Optional[bool]
    """A unique identifier for the enclosing event."""
    id: Optional[str]
    """Can be set to `test` or `prerequest` for test scripts or pre-request scripts respectively."""
    listen: str
    script: Optional[Script]

    def __init__(self, disabled: Optional[bool], id: Optional[str], listen: str, script: Optional[Script]) -> None:
        self.disabled = disabled
        self.id = id
        self.listen = listen
        self.script = script

    @staticmethod
    def from_dict(obj: Any) -> 'Event':
        assert isinstance(obj, dict)
        disabled = from_union([from_bool, from_none], obj.get("disabled"))
        id = from_union([from_str, from_none], obj.get("id"))
        listen = from_str(obj.get("listen"))
        script = from_union([Script.from_dict, from_none], obj.get("script"))
        return Event(disabled, id, listen, script)

    def to_dict(self) -> dict:
        result: dict = {}
        result["disabled"] = from_union([from_bool, from_none], self.disabled)
        result["id"] = from_union([from_str, from_none], self.id)
        result["listen"] = from_str(self.listen)
        result["script"] = from_union([lambda x: to_class(Script, x), from_none], self.script)
        return result


class CollectionVersionClass:
    """A human friendly identifier to make sense of the version numbers. E.g: 'beta-3'"""
    identifier: Optional[str]
    """Increment this number if you make changes to the collection that changes its behaviour.
    E.g: Removing or adding new test scripts. (partly or completely).
    """
    major: int
    meta: Any
    """You should increment this number if you make changes that will not break anything that
    uses the collection. E.g: removing a folder.
    """
    minor: int
    """Ideally, minor changes to a collection should result in the increment of this number."""
    patch: int

    def __init__(self, identifier: Optional[str], major: int, meta: Any, minor: int, patch: int) -> None:
        self.identifier = identifier
        self.major = major
        self.meta = meta
        self.minor = minor
        self.patch = patch

    @staticmethod
    def from_dict(obj: Any) -> 'CollectionVersionClass':
        assert isinstance(obj, dict)
        identifier = from_union([from_str, from_none], obj.get("identifier"))
        major = from_int(obj.get("major"))
        meta = obj.get("meta")
        minor = from_int(obj.get("minor"))
        patch = from_int(obj.get("patch"))
        return CollectionVersionClass(identifier, major, meta, minor, patch)

    def to_dict(self) -> dict:
        result: dict = {}
        result["identifier"] = from_union([from_str, from_none], self.identifier)
        result["major"] = from_int(self.major)
        result["meta"] = self.meta
        result["minor"] = from_int(self.minor)
        result["patch"] = from_int(self.patch)
        return result


class Information:
    """Detailed description of the info block"""
    """Every collection is identified by the unique value of this field. The value of this field
    is usually easiest to generate using a UID generator function. If you already have a
    collection, it is recommended that you maintain the same id since changing the id usually
    implies that is a different collection than it was originally.
    *Note: This field exists for compatibility reasons with Collection Format V1.*
    """
    postman_id: Optional[str]
    description: Union[Description, None, str]
    """A collection's friendly name is defined by this field. You would want to set this field
    to a value that would allow you to easily identify this collection among a bunch of other
    collections, as such outlining its usage or content.
    """
    name: str
    """This should ideally hold a link to the Postman schema that is used to validate this
    collection. E.g: https://schema.getpostman.com/collection/v1
    """
    schema: str
    version: Union[CollectionVersionClass, None, str]

    def __init__(self, postman_id: Optional[str], description: Union[Description, None, str], name: str, schema: str,
                 version: Union[CollectionVersionClass, None, str]) -> None:
        self.postman_id = postman_id
        self.description = description
        self.name = name
        self.schema = schema
        self.version = version

    @staticmethod
    def from_dict(obj: Any) -> 'Information':
        assert isinstance(obj, dict)
        postman_id = from_union([from_str, from_none], obj.get("_postman_id"))
        description = from_union([Description.from_dict, from_none, from_str], obj.get("description"))
        name = from_str(obj.get("name"))
        schema = from_str(obj.get("schema"))
        version = from_union([CollectionVersionClass.from_dict, from_str, from_none], obj.get("version"))
        return Information(postman_id, description, name, schema, version)

    def to_dict(self) -> dict:
        result: dict = {}
        result["_postman_id"] = from_union([from_str, from_none], self.postman_id)
        result["description"] = from_union([lambda x: to_class(Description, x), from_none, from_str], self.description)
        result["name"] = from_str(self.name)
        result["schema"] = from_str(self.schema)
        result["version"] = from_union([lambda x: to_class(CollectionVersionClass, x), from_str, from_none],
                                       self.version)
        return result


class File:
    content: Optional[str]
    src: Optional[str]

    def __init__(self, content: Optional[str], src: Optional[str]) -> None:
        self.content = content
        self.src = src

    @staticmethod
    def from_dict(obj: Any) -> 'File':
        assert isinstance(obj, dict)
        content = from_union([from_str, from_none], obj.get("content"))
        src = from_union([from_none, from_str], obj.get("src"))
        return File(content, src)

    def to_dict(self) -> dict:
        result: dict = {}
        result["content"] = from_union([from_str, from_none], self.content)
        result["src"] = from_union([from_none, from_str], self.src)
        return result


class FormParameterType(Enum):
    FILE = "file"
    TEXT = "text"


class FormParameter:
    """Override Content-Type header of this form data entity."""
    content_type: Optional[str]
    description: Union[Description, None, str]
    """When set to true, prevents this form data entity from being sent."""
    disabled: Optional[bool]
    key: str
    type: Optional[FormParameterType]
    value: Optional[str]
    src: Union[List[Any], None, str]

    def __init__(self, content_type: Optional[str], description: Union[Description, None, str],
                 disabled: Optional[bool], key: str, type: Optional[FormParameterType], value: Optional[str],
                 src: Union[List[Any], None, str]) -> None:
        self.content_type = content_type
        self.description = description
        self.disabled = disabled
        self.key = key
        self.type = type
        self.value = value
        self.src = src

    @staticmethod
    def from_dict(obj: Any) -> 'FormParameter':
        assert isinstance(obj, dict)
        content_type = from_union([from_str, from_none], obj.get("contentType"))
        description = from_union([Description.from_dict, from_none, from_str], obj.get("description"))
        disabled = from_union([from_bool, from_none], obj.get("disabled"))
        key = from_str(obj.get("key"))
        type = from_union([FormParameterType, from_none], obj.get("type"))
        value = from_union([from_str, from_none], obj.get("value"))
        src = from_union([lambda x: from_list(lambda x: x, x), from_none, from_str], obj.get("src"))
        return FormParameter(content_type, description, disabled, key, type, value, src)

    def to_dict(self) -> dict:
        result: dict = {}
        result["contentType"] = from_union([from_str, from_none], self.content_type)
        result["description"] = from_union([lambda x: to_class(Description, x), from_none, from_str], self.description)
        result["disabled"] = from_union([from_bool, from_none], self.disabled)
        result["key"] = from_str(self.key)
        result["type"] = from_union([lambda x: to_enum(FormParameterType, x), from_none], self.type)
        result["value"] = from_union([from_str, from_none], self.value)
        result["src"] = from_union([lambda x: from_list(lambda x: x, x), from_none, from_str], self.src)
        return result


class Mode(Enum):
    """Postman stores the type of data associated with this request in this field."""
    FILE = "file"
    FORMDATA = "formdata"
    GRAPHQL = "graphql"
    RAW = "raw"
    URLENCODED = "urlencoded"


class URLEncodedParameter:
    description: Union[Description, None, str]
    disabled: Optional[bool]
    key: str
    value: Optional[str]

    def __init__(self, description: Union[Description, None, str], disabled: Optional[bool], key: str,
                 value: Optional[str]) -> None:
        self.description = description
        self.disabled = disabled
        self.key = key
        self.value = value

    @staticmethod
    def from_dict(obj: Any) -> 'URLEncodedParameter':
        assert isinstance(obj, dict)
        description = from_union([Description.from_dict, from_none, from_str], obj.get("description"))
        disabled = from_union([from_bool, from_none], obj.get("disabled"))
        key = from_str(obj.get("key"))
        value = from_union([from_str, from_none], obj.get("value"))
        return URLEncodedParameter(description, disabled, key, value)

    def to_dict(self) -> dict:
        result: dict = {}
        result["description"] = from_union([lambda x: to_class(Description, x), from_none, from_str], self.description)
        result["disabled"] = from_union([from_bool, from_none], self.disabled)
        result["key"] = from_str(self.key)
        result["value"] = from_union([from_str, from_none], self.value)
        return result


class Body:
    """This field contains the data usually contained in the request body."""
    """When set to true, prevents request body from being sent."""
    disabled: Optional[bool]
    file: Optional[File]
    formdata: Optional[List[FormParameter]]
    graphql: Optional[Dict[str, Any]]
    """Postman stores the type of data associated with this request in this field."""
    mode: Optional[Mode]
    """Additional configurations and options set for various body modes."""
    options: Optional[Dict[str, Any]]
    raw: Optional[str]
    urlencoded: Optional[List[URLEncodedParameter]]

    def __init__(self, disabled: Optional[bool], file: Optional[File], formdata: Optional[List[FormParameter]],
                 graphql: Optional[Dict[str, Any]], mode: Optional[Mode], options: Optional[Dict[str, Any]],
                 raw: Optional[str], urlencoded: Optional[List[URLEncodedParameter]]) -> None:
        self.disabled = disabled
        self.file = file
        self.formdata = formdata
        self.graphql = graphql
        self.mode = mode
        self.options = options
        self.raw = raw
        self.urlencoded = urlencoded

    @staticmethod
    def from_dict(obj: Any) -> 'Body':
        assert isinstance(obj, dict)
        disabled = from_union([from_bool, from_none], obj.get("disabled"))
        file = from_union([File.from_dict, from_none], obj.get("file"))
        formdata = from_union([lambda x: from_list(FormParameter.from_dict, x), from_none], obj.get("formdata"))
        graphql = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("graphql"))
        mode = from_union([Mode, from_none], obj.get("mode"))
        options = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("options"))
        raw = from_union([from_str, from_none], obj.get("raw"))
        urlencoded = from_union([lambda x: from_list(URLEncodedParameter.from_dict, x), from_none],
                                obj.get("urlencoded"))
        return Body(disabled, file, formdata, graphql, mode, options, raw, urlencoded)

    def to_dict(self) -> dict:
        result: dict = {}
        result["disabled"] = from_union([from_bool, from_none], self.disabled)
        result["file"] = from_union([lambda x: to_class(File, x), from_none], self.file)
        result["formdata"] = from_union([lambda x: from_list(lambda x: to_class(FormParameter, x), x), from_none],
                                        self.formdata)
        result["graphql"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.graphql)
        result["mode"] = from_union([lambda x: to_enum(Mode, x), from_none], self.mode)
        result["options"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.options)
        result["raw"] = from_union([from_str, from_none], self.raw)
        result["urlencoded"] = from_union(
            [lambda x: from_list(lambda x: to_class(URLEncodedParameter, x), x), from_none], self.urlencoded)
        return result


class CERT:
    """An object containing path to file certificate, on the file system"""
    """The path to file containing key for certificate, on the file system"""
    src: Any

    def __init__(self, src: Any) -> None:
        self.src = src

    @staticmethod
    def from_dict(obj: Any) -> 'CERT':
        assert isinstance(obj, dict)
        src = obj.get("src")
        return CERT(src)

    def to_dict(self) -> dict:
        result: dict = {}
        result["src"] = self.src
        return result


class Key:
    """An object containing path to file containing private key, on the file system"""
    """The path to file containing key for certificate, on the file system"""
    src: Any

    def __init__(self, src: Any) -> None:
        self.src = src

    @staticmethod
    def from_dict(obj: Any) -> 'Key':
        assert isinstance(obj, dict)
        src = obj.get("src")
        return Key(src)

    def to_dict(self) -> dict:
        result: dict = {}
        result["src"] = self.src
        return result


class Certificate:
    """A representation of an ssl certificate"""
    """An object containing path to file certificate, on the file system"""
    cert: Optional[CERT]
    """An object containing path to file containing private key, on the file system"""
    key: Optional[Key]
    """A list of Url match pattern strings, to identify Urls this certificate can be used for."""
    matches: Optional[List[str]]
    """A name for the certificate for user reference"""
    name: Optional[str]
    """The passphrase for the certificate"""
    passphrase: Optional[str]

    def __init__(self, cert: Optional[CERT], key: Optional[Key], matches: Optional[List[str]], name: Optional[str],
                 passphrase: Optional[str]) -> None:
        self.cert = cert
        self.key = key
        self.matches = matches
        self.name = name
        self.passphrase = passphrase

    @staticmethod
    def from_dict(obj: Any) -> 'Certificate':
        assert isinstance(obj, dict)
        cert = from_union([CERT.from_dict, from_none], obj.get("cert"))
        key = from_union([Key.from_dict, from_none], obj.get("key"))
        matches = from_union([lambda x: from_list(from_str, x), from_none], obj.get("matches"))
        name = from_union([from_str, from_none], obj.get("name"))
        passphrase = from_union([from_str, from_none], obj.get("passphrase"))
        return Certificate(cert, key, matches, name, passphrase)

    def to_dict(self) -> dict:
        result: dict = {}
        result["cert"] = from_union([lambda x: to_class(CERT, x), from_none], self.cert)
        result["key"] = from_union([lambda x: to_class(Key, x), from_none], self.key)
        result["matches"] = from_union([lambda x: from_list(from_str, x), from_none], self.matches)
        result["name"] = from_union([from_str, from_none], self.name)
        result["passphrase"] = from_union([from_str, from_none], self.passphrase)
        return result


class Header:
    """A representation for a list of headers

    Represents a single HTTP Header
    """
    description: Union[Description, None, str]
    """If set to true, the current header will not be sent with requests."""
    disabled: Optional[bool]
    """This holds the LHS of the HTTP Header, e.g ``Content-Type`` or ``X-Custom-Header``"""
    key: str
    """The value (or the RHS) of the Header is stored in this field."""
    value: str

    def __init__(self, description: Union[Description, None, str], disabled: Optional[bool], key: str,
                 value: str) -> None:
        self.description = description
        self.disabled = disabled
        self.key = key
        self.value = value

    @staticmethod
    def from_dict(obj: Any) -> 'Header':
        assert isinstance(obj, dict)
        description = from_union([Description.from_dict, from_none, from_str], obj.get("description"))
        disabled = from_union([from_bool, from_none], obj.get("disabled"))
        key = from_str(obj.get("key"))
        value = from_str(obj.get("value"))
        return Header(description, disabled, key, value)

    def to_dict(self) -> dict:
        result: dict = {}
        result["description"] = from_union([lambda x: to_class(Description, x), from_none, from_str], self.description)
        result["disabled"] = from_union([from_bool, from_none], self.disabled)
        result["key"] = from_str(self.key)
        result["value"] = from_str(self.value)
        return result


class ProxyConfig:
    """Using the Proxy, you can configure your custom proxy into the postman for particular url
    match
    """
    """When set to true, ignores this proxy configuration entity"""
    disabled: Optional[bool]
    """The proxy server host"""
    host: Optional[str]
    """The Url match for which the proxy config is defined"""
    match: Optional[str]
    """The proxy server port"""
    port: Optional[int]
    """The tunneling details for the proxy config"""
    tunnel: Optional[bool]

    def __init__(self, disabled: Optional[bool], host: Optional[str], match: Optional[str], port: Optional[int],
                 tunnel: Optional[bool]) -> None:
        self.disabled = disabled
        self.host = host
        self.match = match
        self.port = port
        self.tunnel = tunnel

    @staticmethod
    def from_dict(obj: Any) -> 'ProxyConfig':
        assert isinstance(obj, dict)
        disabled = from_union([from_bool, from_none], obj.get("disabled"))
        host = from_union([from_str, from_none], obj.get("host"))
        match = from_union([from_str, from_none], obj.get("match"))
        port = from_union([from_int, from_none], obj.get("port"))
        tunnel = from_union([from_bool, from_none], obj.get("tunnel"))
        return ProxyConfig(disabled, host, match, port, tunnel)

    def to_dict(self) -> dict:
        result: dict = {}
        result["disabled"] = from_union([from_bool, from_none], self.disabled)
        result["host"] = from_union([from_str, from_none], self.host)
        result["match"] = from_union([from_str, from_none], self.match)
        result["port"] = from_union([from_int, from_none], self.port)
        result["tunnel"] = from_union([from_bool, from_none], self.tunnel)
        return result


class RequestClass:
    auth: Optional[Auth]
    body: Optional[Body]
    certificate: Optional[Certificate]
    description: Union[Description, None, str]
    header: Union[List[Header], None, str]
    method: Optional[str]
    proxy: Optional[ProxyConfig]
    url: Union[URLClass, None, str]

    def __init__(self, auth: Optional[Auth], body: Optional[Body], certificate: Optional[Certificate],
                 description: Union[Description, None, str], header: Union[List[Header], None, str],
                 method: Optional[str], proxy: Optional[ProxyConfig], url: Union[URLClass, None, str]) -> None:
        self.auth = auth
        self.body = body
        self.certificate = certificate
        self.description = description
        self.header = header
        self.method = method
        self.proxy = proxy
        self.url = url

    @staticmethod
    def from_dict(obj: Any) -> 'RequestClass':
        assert isinstance(obj, dict)
        auth = from_union([from_none, Auth.from_dict], obj.get("auth"))
        body = from_union([Body.from_dict, from_none], obj.get("body"))
        certificate = from_union([Certificate.from_dict, from_none], obj.get("certificate"))
        description = from_union([Description.from_dict, from_none, from_str], obj.get("description"))
        header = from_union([lambda x: from_list(Header.from_dict, x), from_str, from_none], obj.get("header"))
        method = from_union([from_str, from_none], obj.get("method"))
        proxy = from_union([ProxyConfig.from_dict, from_none], obj.get("proxy"))
        url = from_union([URLClass.from_dict, from_str, from_none], obj.get("url"))
        return RequestClass(auth, body, certificate, description, header, method, proxy, url)

    def to_dict(self) -> dict:
        result: dict = {}
        result["auth"] = from_union([from_none, lambda x: to_class(Auth, x)], self.auth)
        result["body"] = from_union([lambda x: to_class(Body, x), from_none], self.body)
        result["certificate"] = from_union([lambda x: to_class(Certificate, x), from_none], self.certificate)
        result["description"] = from_union([lambda x: to_class(Description, x), from_none, from_str], self.description)
        result["header"] = from_union([lambda x: from_list(lambda x: to_class(Header, x), x), from_str, from_none],
                                      self.header)
        result["method"] = from_union([from_str, from_none], self.method)
        result["proxy"] = from_union([lambda x: to_class(ProxyConfig, x), from_none], self.proxy)
        result["url"] = from_union([lambda x: to_class(URLClass, x), from_str, from_none], self.url)
        return result


class Cookie:
    """A Cookie, that follows the [Google Chrome
    format](https://developer.chrome.com/extensions/cookies)
    """
    """The domain for which this cookie is valid."""
    domain: str
    """When the cookie expires."""
    expires: Union[float, None, str]
    """Custom attributes for a cookie go here, such as the [Priority
    Field](https://code.google.com/p/chromium/issues/detail?id=232693)
    """
    extensions: Optional[List[Any]]
    """True if the cookie is a host-only cookie. (i.e. a request's URL domain must exactly match
    the domain of the cookie).
    """
    host_only: Optional[bool]
    """Indicates if this cookie is HTTP Only. (if True, the cookie is inaccessible to
    client-side scripts)
    """
    http_only: Optional[bool]
    max_age: Optional[str]
    """This is the name of the Cookie."""
    name: Optional[str]
    """The path associated with the Cookie."""
    path: str
    """Indicates if the 'secure' flag is set on the Cookie, meaning that it is transmitted over
    secure connections only. (typically HTTPS)
    """
    secure: Optional[bool]
    """True if the cookie is a session cookie."""
    session: Optional[bool]
    """The value of the Cookie."""
    value: Optional[str]

    def __init__(self, domain: str, expires: Union[float, None, str], extensions: Optional[List[Any]],
                 host_only: Optional[bool], http_only: Optional[bool], max_age: Optional[str], name: Optional[str],
                 path: str, secure: Optional[bool], session: Optional[bool], value: Optional[str]) -> None:
        self.domain = domain
        self.expires = expires
        self.extensions = extensions
        self.host_only = host_only
        self.http_only = http_only
        self.max_age = max_age
        self.name = name
        self.path = path
        self.secure = secure
        self.session = session
        self.value = value

    @staticmethod
    def from_dict(obj: Any) -> 'Cookie':
        assert isinstance(obj, dict)
        domain = from_str(obj.get("domain"))
        expires = from_union([from_float, from_str, from_none], obj.get("expires"))
        extensions = from_union([lambda x: from_list(lambda x: x, x), from_none], obj.get("extensions"))
        host_only = from_union([from_bool, from_none], obj.get("hostOnly"))
        http_only = from_union([from_bool, from_none], obj.get("httpOnly"))
        max_age = from_union([from_str, from_none], obj.get("maxAge"))
        name = from_union([from_str, from_none], obj.get("name"))
        path = from_str(obj.get("path"))
        secure = from_union([from_bool, from_none], obj.get("secure"))
        session = from_union([from_bool, from_none], obj.get("session"))
        value = from_union([from_str, from_none], obj.get("value"))
        return Cookie(domain, expires, extensions, host_only, http_only, max_age, name, path, secure, session, value)

    def to_dict(self) -> dict:
        result: dict = {}
        result["domain"] = from_str(self.domain)
        result["expires"] = from_union([to_float, from_str, from_none], self.expires)
        result["extensions"] = from_union([lambda x: from_list(lambda x: x, x), from_none], self.extensions)
        result["hostOnly"] = from_union([from_bool, from_none], self.host_only)
        result["httpOnly"] = from_union([from_bool, from_none], self.http_only)
        result["maxAge"] = from_union([from_str, from_none], self.max_age)
        result["name"] = from_union([from_str, from_none], self.name)
        result["path"] = from_str(self.path)
        result["secure"] = from_union([from_bool, from_none], self.secure)
        result["session"] = from_union([from_bool, from_none], self.session)
        result["value"] = from_union([from_str, from_none], self.value)
        return result


class ResponseClass:
    """The raw text of the response."""
    body: Optional[str]
    """The numerical response code, example: 200, 201, 404, etc."""
    code: Optional[int]
    cookie: Optional[List[Cookie]]
    header: Union[List[Union[Header, str]], None, str]
    """A unique, user defined identifier that can  be used to refer to this response from
    requests.
    """
    id: Optional[str]
    original_request: Union[RequestClass, None, str]
    """The time taken by the request to complete. If a number, the unit is milliseconds. If the
    response is manually created, this can be set to `null`.
    """
    response_time: Union[float, None, str]
    """The response status, e.g: '200 OK'"""
    status: Optional[str]
    """Set of timing information related to request and response in milliseconds"""
    timings: Optional[Dict[str, Any]]

    def __init__(self, body: Optional[str], code: Optional[int], cookie: Optional[List[Cookie]],
                 header: Union[List[Union[Header, str]], None, str], id: Optional[str],
                 original_request: Union[RequestClass, None, str], response_time: Union[float, None, str],
                 status: Optional[str], timings: Optional[Dict[str, Any]]) -> None:
        self.body = body
        self.code = code
        self.cookie = cookie
        self.header = header
        self.id = id
        self.original_request = original_request
        self.response_time = response_time
        self.status = status
        self.timings = timings

    @staticmethod
    def from_dict(obj: Any) -> 'ResponseClass':
        assert isinstance(obj, dict)
        body = from_union([from_none, from_str], obj.get("body"))
        code = from_union([from_int, from_none], obj.get("code"))
        cookie = from_union([lambda x: from_list(Cookie.from_dict, x), from_none], obj.get("cookie"))
        header = from_union(
            [lambda x: from_list(lambda x: from_union([Header.from_dict, from_str], x), x), from_none, from_str],
            obj.get("header"))
        id = from_union([from_str, from_none], obj.get("id"))
        original_request = from_union([RequestClass.from_dict, from_str, from_none], obj.get("originalRequest"))
        response_time = from_union([from_float, from_str, from_none], obj.get("responseTime"))
        status = from_union([from_str, from_none], obj.get("status"))
        timings = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("timings"))
        return ResponseClass(body, code, cookie, header, id, original_request, response_time, status, timings)

    def to_dict(self) -> dict:
        result: dict = {}
        result["body"] = from_union([from_none, from_str], self.body)
        result["code"] = from_union([from_int, from_none], self.code)
        result["cookie"] = from_union([lambda x: from_list(lambda x: to_class(Cookie, x), x), from_none], self.cookie)
        result["header"] = from_union(
            [lambda x: from_list(lambda x: from_union([lambda x: to_class(Header, x), from_str], x), x), from_none,
             from_str], self.header)
        result["id"] = from_union([from_str, from_none], self.id)
        result["originalRequest"] = from_union([lambda x: to_class(RequestClass, x), from_str, from_none],
                                               self.original_request)
        result["responseTime"] = from_union([to_float, from_str, from_none], self.response_time)
        result["status"] = from_union([from_str, from_none], self.status)
        result["timings"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.timings)
        return result


class Items:
    """Items are entities which contain an actual HTTP request, and sample responses attached to
    it.

    One of the primary goals of Postman is to organize the development of APIs. To this end,
    it is necessary to be able to group requests together. This can be achived using
    'Folders'. A folder just is an ordered set of requests.
    """
    description: Union[Description, None, str]
    event: Optional[List[Event]]
    """A unique ID that is used to identify collections internally"""
    id: Optional[str]
    """A human readable identifier for the current item.

    A folder's friendly name is defined by this field. You would want to set this field to a
    value that would allow you to easily identify this folder.
    """
    name: Optional[str]
    protocol_profile_behavior: Optional[Dict[str, Any]]
    request: Union[RequestClass, None, str]
    response: Optional[List[Union[List[Any], bool, ResponseClass, float, int, None, str]]]
    variable: Optional[List[Variable]]
    auth: Optional[Auth]
    """Items are entities which contain an actual HTTP request, and sample responses attached to
    it. Folders may contain many items.
    """
    item: Optional[List['Items']]

    def __init__(self, description: Union[Description, None, str], event: Optional[List[Event]], id: Optional[str],
                 name: Optional[str], protocol_profile_behavior: Optional[Dict[str, Any]],
                 request: Union[RequestClass, None, str],
                 response: Optional[List[Union[List[Any], bool, ResponseClass, float, int, None, str]]],
                 variable: Optional[List[Variable]], auth: Optional[Auth], item: Optional[List['Items']]) -> None:
        self.description = description
        self.event = event
        self.id = id
        self.name = name
        self.protocol_profile_behavior = protocol_profile_behavior
        self.request = request
        self.response = response
        self.variable = variable
        self.auth = auth
        self.item = item

    @staticmethod
    def from_dict(obj: Any) -> 'Items':
        assert isinstance(obj, dict)
        description = from_union([Description.from_dict, from_none, from_str], obj.get("description"))
        event = from_union([lambda x: from_list(Event.from_dict, x), from_none], obj.get("event"))
        id = from_union([from_str, from_none], obj.get("id"))
        name = from_union([from_str, from_none], obj.get("name"))
        protocol_profile_behavior = from_union([lambda x: from_dict(lambda x: x, x), from_none],
                                               obj.get("protocolProfileBehavior"))
        request = from_union([RequestClass.from_dict, from_str, from_none], obj.get("request"))
        response = from_union([lambda x: from_list(lambda x: from_union(
            [from_none, from_float, from_int, from_bool, from_str, lambda x: from_list(lambda x: x, x),
             ResponseClass.from_dict], x), x), from_none], obj.get("response"))
        variable = from_union([lambda x: from_list(Variable.from_dict, x), from_none], obj.get("variable"))
        auth = from_union([from_none, Auth.from_dict], obj.get("auth"))
        item = from_union([lambda x: from_list(Items.from_dict, x), from_none], obj.get("item"))
        return Items(description, event, id, name, protocol_profile_behavior, request, response, variable, auth, item)

    def to_dict(self) -> dict:
        result: dict = {}
        result["description"] = from_union([lambda x: to_class(Description, x), from_none, from_str], self.description)
        result["event"] = from_union([lambda x: from_list(lambda x: to_class(Event, x), x), from_none], self.event)
        result["id"] = from_union([from_str, from_none], self.id)
        result["name"] = from_union([from_str, from_none], self.name)
        result["protocolProfileBehavior"] = from_union([lambda x: from_dict(lambda x: x, x), from_none],
                                                       self.protocol_profile_behavior)
        result["request"] = from_union([lambda x: to_class(RequestClass, x), from_str, from_none], self.request)
        result["response"] = from_union([lambda x: from_list(lambda x: from_union(
            [from_none, to_float, from_int, from_bool, from_str, lambda x: from_list(lambda x: x, x),
             lambda x: to_class(ResponseClass, x)], x), x), from_none], self.response)
        result["variable"] = from_union([lambda x: from_list(lambda x: to_class(Variable, x), x), from_none],
                                        self.variable)
        result["auth"] = from_union([from_none, lambda x: to_class(Auth, x)], self.auth)
        result["item"] = from_union([lambda x: from_list(lambda x: to_class(Items, x), x), from_none], self.item)
        return result


class PostmanCollection:
    auth: Optional[Auth]
    event: Optional[List[Event]]
    info: Information
    """Items are the basic unit for a Postman collection. You can think of them as corresponding
    to a single API endpoint. Each Item has one request and may have multiple API responses
    associated with it.
    """
    item: List[Items]
    protocol_profile_behavior: Optional[Dict[str, Any]]
    variable: Optional[List[Variable]]

    def __init__(self, auth: Optional[Auth], event: Optional[List[Event]], info: Information, item: List[Items],
                 protocol_profile_behavior: Optional[Dict[str, Any]], variable: Optional[List[Variable]]) -> None:
        self.auth = auth
        self.event = event
        self.info = info
        self.item = item
        self.protocol_profile_behavior = protocol_profile_behavior
        self.variable = variable

    @staticmethod
    def from_dict(obj: Any) -> 'PostmanCollection':
        assert isinstance(obj, dict)
        auth = from_union([from_none, Auth.from_dict], obj.get("auth"))
        event = from_union([lambda x: from_list(Event.from_dict, x), from_none], obj.get("event"))
        info = Information.from_dict(obj.get("info"))
        item = from_list(Items.from_dict, obj.get("item"))
        protocol_profile_behavior = from_union([lambda x: from_dict(lambda x: x, x), from_none],
                                               obj.get("protocolProfileBehavior"))
        variable = from_union([lambda x: from_list(Variable.from_dict, x), from_none], obj.get("variable"))
        return PostmanCollection(auth, event, info, item, protocol_profile_behavior, variable)

    def to_dict(self) -> dict:
        result: dict = {}
        result["auth"] = from_union([from_none, lambda x: to_class(Auth, x)], self.auth)
        result["event"] = from_union([lambda x: from_list(lambda x: to_class(Event, x), x), from_none], self.event)
        result["info"] = to_class(Information, self.info)
        result["item"] = from_list(lambda x: to_class(Items, x), self.item)
        result["protocolProfileBehavior"] = from_union([lambda x: from_dict(lambda x: x, x), from_none],
                                                       self.protocol_profile_behavior)
        result["variable"] = from_union([lambda x: from_list(lambda x: to_class(Variable, x), x), from_none],
                                        self.variable)
        return result


def postman_collection_from_dict(s: Any) -> PostmanCollection:
    return PostmanCollection.from_dict(s)


def postman_to_dict(x: PostmanCollection) -> Any:
    return to_class(PostmanCollection, x)
