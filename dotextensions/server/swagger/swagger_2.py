from typing import Optional, Dict, Any, List, TypeVar, Callable, Type, cast

T = TypeVar("T")


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


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


class Components:
    callbacks: Optional[Dict[str, Any]]
    examples: Optional[Dict[str, Any]]
    headers: Optional[Dict[str, Any]]
    links: Optional[Dict[str, Any]]
    parameters: Optional[Dict[str, Any]]
    request_bodies: Optional[Dict[str, Any]]
    responses: Optional[Dict[str, Any]]
    schemas: Optional[Dict[str, Any]]
    security_schemes: Optional[Dict[str, Any]]

    def __init__(self, callbacks: Optional[Dict[str, Any]], examples: Optional[Dict[str, Any]],
                 headers: Optional[Dict[str, Any]], links: Optional[Dict[str, Any]],
                 parameters: Optional[Dict[str, Any]], request_bodies: Optional[Dict[str, Any]],
                 responses: Optional[Dict[str, Any]], schemas: Optional[Dict[str, Any]],
                 security_schemes: Optional[Dict[str, Any]]) -> None:
        self.callbacks = callbacks
        self.examples = examples
        self.headers = headers
        self.links = links
        self.parameters = parameters
        self.request_bodies = request_bodies
        self.responses = responses
        self.schemas = schemas
        self.security_schemes = security_schemes

    @staticmethod
    def from_dict(obj: Any) -> 'Components':
        assert isinstance(obj, dict)
        callbacks = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("callbacks"))
        examples = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("examples"))
        headers = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("headers"))
        links = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("links"))
        parameters = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("parameters"))
        request_bodies = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("requestBodies"))
        responses = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("responses"))
        schemas = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("schemas"))
        security_schemes = from_union([lambda x: from_dict(lambda x: x, x), from_none], obj.get("securitySchemes"))
        return Components(callbacks, examples, headers, links, parameters, request_bodies, responses, schemas,
                          security_schemes)

    def to_dict(self) -> dict:
        result: dict = {}
        result["callbacks"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.callbacks)
        result["examples"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.examples)
        result["headers"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.headers)
        result["links"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.links)
        result["parameters"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.parameters)
        result["requestBodies"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.request_bodies)
        result["responses"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.responses)
        result["schemas"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.schemas)
        result["securitySchemes"] = from_union([lambda x: from_dict(lambda x: x, x), from_none], self.security_schemes)
        return result


class ExternalDocumentation:
    description: Optional[str]
    url: str

    def __init__(self, description: Optional[str], url: str) -> None:
        self.description = description
        self.url = url

    @staticmethod
    def from_dict(obj: Any) -> 'ExternalDocumentation':
        assert isinstance(obj, dict)
        description = from_union([from_str, from_none], obj.get("description"))
        url = from_str(obj.get("url"))
        return ExternalDocumentation(description, url)

    def to_dict(self) -> dict:
        result: dict = {}
        result["description"] = from_union([from_str, from_none], self.description)
        result["url"] = from_str(self.url)
        return result


class Contact:
    email: Optional[str]
    name: Optional[str]
    url: Optional[str]

    def __init__(self, email: Optional[str], name: Optional[str], url: Optional[str]) -> None:
        self.email = email
        self.name = name
        self.url = url

    @staticmethod
    def from_dict(obj: Any) -> 'Contact':
        assert isinstance(obj, dict)
        email = from_union([from_str, from_none], obj.get("email"))
        name = from_union([from_str, from_none], obj.get("name"))
        url = from_union([from_str, from_none], obj.get("url"))
        return Contact(email, name, url)

    def to_dict(self) -> dict:
        result: dict = {}
        result["email"] = from_union([from_str, from_none], self.email)
        result["name"] = from_union([from_str, from_none], self.name)
        result["url"] = from_union([from_str, from_none], self.url)
        return result


class License:
    name: str
    url: Optional[str]

    def __init__(self, name: str, url: Optional[str]) -> None:
        self.name = name
        self.url = url

    @staticmethod
    def from_dict(obj: Any) -> 'License':
        assert isinstance(obj, dict)
        name = from_str(obj.get("name"))
        url = from_union([from_str, from_none], obj.get("url"))
        return License(name, url)

    def to_dict(self) -> dict:
        result: dict = {}
        result["name"] = from_str(self.name)
        result["url"] = from_union([from_str, from_none], self.url)
        return result


class Info:
    contact: Optional[Contact]
    description: Optional[str]
    license: Optional[License]
    terms_of_service: Optional[str]
    title: str
    version: str

    def __init__(self, contact: Optional[Contact], description: Optional[str], license: Optional[License],
                 terms_of_service: Optional[str], title: str, version: str) -> None:
        self.contact = contact
        self.description = description
        self.license = license
        self.terms_of_service = terms_of_service
        self.title = title
        self.version = version

    @staticmethod
    def from_dict(obj: Any) -> 'Info':
        assert isinstance(obj, dict)
        contact = from_union([Contact.from_dict, from_none], obj.get("contact"))
        description = from_union([from_str, from_none], obj.get("description"))
        license = from_union([License.from_dict, from_none], obj.get("license"))
        terms_of_service = from_union([from_str, from_none], obj.get("termsOfService"))
        title = from_str(obj.get("title"))
        version = from_str(obj.get("version"))
        return Info(contact, description, license, terms_of_service, title, version)

    def to_dict(self) -> dict:
        result: dict = {}
        result["contact"] = from_union([lambda x: to_class(Contact, x), from_none], self.contact)
        result["description"] = from_union([from_str, from_none], self.description)
        result["license"] = from_union([lambda x: to_class(License, x), from_none], self.license)
        result["termsOfService"] = from_union([from_str, from_none], self.terms_of_service)
        result["title"] = from_str(self.title)
        result["version"] = from_str(self.version)
        return result


class Paths:
    pass

    def __init__(self, ) -> None:
        pass

    @staticmethod
    def from_dict(obj: Any) -> 'Paths':
        assert isinstance(obj, dict)
        return Paths()

    def to_dict(self) -> dict:
        result: dict = {}
        return result


class ServerVariable:
    default: str
    description: Optional[str]
    enum: Optional[List[str]]

    def __init__(self, default: str, description: Optional[str], enum: Optional[List[str]]) -> None:
        self.default = default
        self.description = description
        self.enum = enum

    @staticmethod
    def from_dict(obj: Any) -> 'ServerVariable':
        assert isinstance(obj, dict)
        default = from_str(obj.get("default"))
        description = from_union([from_str, from_none], obj.get("description"))
        enum = from_union([lambda x: from_list(from_str, x), from_none], obj.get("enum"))
        return ServerVariable(default, description, enum)

    def to_dict(self) -> dict:
        result: dict = {}
        result["default"] = from_str(self.default)
        result["description"] = from_union([from_str, from_none], self.description)
        result["enum"] = from_union([lambda x: from_list(from_str, x), from_none], self.enum)
        return result


class Server:
    description: Optional[str]
    url: str
    variables: Optional[Dict[str, ServerVariable]]

    def __init__(self, description: Optional[str], url: str, variables: Optional[Dict[str, ServerVariable]]) -> None:
        self.description = description
        self.url = url
        self.variables = variables

    @staticmethod
    def from_dict(obj: Any) -> 'Server':
        assert isinstance(obj, dict)
        description = from_union([from_str, from_none], obj.get("description"))
        url = from_str(obj.get("url"))
        variables = from_union([lambda x: from_dict(ServerVariable.from_dict, x), from_none], obj.get("variables"))
        return Server(description, url, variables)

    def to_dict(self) -> dict:
        result: dict = {}
        result["description"] = from_union([from_str, from_none], self.description)
        result["url"] = from_str(self.url)
        result["variables"] = from_union([lambda x: from_dict(lambda x: to_class(ServerVariable, x), x), from_none],
                                         self.variables)
        return result


class Tag:
    description: Optional[str]
    external_docs: Optional[ExternalDocumentation]
    name: str

    def __init__(self, description: Optional[str], external_docs: Optional[ExternalDocumentation], name: str) -> None:
        self.description = description
        self.external_docs = external_docs
        self.name = name

    @staticmethod
    def from_dict(obj: Any) -> 'Tag':
        assert isinstance(obj, dict)
        description = from_union([from_str, from_none], obj.get("description"))
        external_docs = from_union([ExternalDocumentation.from_dict, from_none], obj.get("externalDocs"))
        name = from_str(obj.get("name"))
        return Tag(description, external_docs, name)

    def to_dict(self) -> dict:
        result: dict = {}
        result["description"] = from_union([from_str, from_none], self.description)
        result["externalDocs"] = from_union([lambda x: to_class(ExternalDocumentation, x), from_none],
                                            self.external_docs)
        result["name"] = from_str(self.name)
        return result


class Swagger2:
    """Validation schema for OpenAPI Specification 3.0.X."""
    components: Optional[Components]
    external_docs: Optional[ExternalDocumentation]
    info: Info
    openapi: str
    paths: Paths
    security: Optional[List[Dict[str, List[str]]]]
    servers: Optional[List[Server]]
    tags: Optional[List[Tag]]

    def __init__(self, components: Optional[Components], external_docs: Optional[ExternalDocumentation], info: Info,
                 openapi: str, paths: Paths, security: Optional[List[Dict[str, List[str]]]],
                 servers: Optional[List[Server]], tags: Optional[List[Tag]]) -> None:
        self.components = components
        self.external_docs = external_docs
        self.info = info
        self.openapi = openapi
        self.paths = paths
        self.security = security
        self.servers = servers
        self.tags = tags

    @staticmethod
    def from_dict(obj: Any) -> 'Swagger2':
        assert isinstance(obj, dict)
        components = from_union([Components.from_dict, from_none], obj.get("components"))
        external_docs = from_union([ExternalDocumentation.from_dict, from_none], obj.get("externalDocs"))
        info = Info.from_dict(obj.get("info"))
        openapi = from_str(obj.get("openapi"))
        paths = Paths.from_dict(obj.get("paths"))
        security = from_union(
            [lambda x: from_list(lambda x: from_dict(lambda x: from_list(from_str, x), x), x), from_none],
            obj.get("security"))
        servers = from_union([lambda x: from_list(Server.from_dict, x), from_none], obj.get("servers"))
        tags = from_union([lambda x: from_list(Tag.from_dict, x), from_none], obj.get("tags"))
        return Swagger2(components, external_docs, info, openapi, paths, security, servers, tags)

    def to_dict(self) -> dict:
        result: dict = {}
        result["components"] = from_union([lambda x: to_class(Components, x), from_none], self.components)
        result["externalDocs"] = from_union([lambda x: to_class(ExternalDocumentation, x), from_none],
                                            self.external_docs)
        result["info"] = to_class(Info, self.info)
        result["openapi"] = from_str(self.openapi)
        result["paths"] = to_class(Paths, self.paths)
        result["security"] = from_union(
            [lambda x: from_list(lambda x: from_dict(lambda x: from_list(from_str, x), x), x), from_none],
            self.security)
        result["servers"] = from_union([lambda x: from_list(lambda x: to_class(Server, x), x), from_none], self.servers)
        result["tags"] = from_union([lambda x: from_list(lambda x: to_class(Tag, x), x), from_none], self.tags)
        return result


def swagger2_from_dict(s: Any) -> Swagger2:
    return Swagger2.from_dict(s)


def swagger2_to_dict(x: Swagger2) -> Any:
    return to_class(Swagger2, x)
