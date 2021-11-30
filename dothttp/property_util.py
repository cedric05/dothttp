import json
import logging
import re
import string
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from json import JSONDecodeError
from random import Random
from types import FunctionType
from typing import Dict, Union, List

from .exceptions import HttpFileException, PropertyNotFoundException

base_logger = logging.getLogger('dothttp')


@dataclass
class Property:
    text: List = field(default_factory=list())
    key: Union[str, None] = None
    value: Union[str, None, HttpFileException] = None


def random_string_generator(size=4, chars=string.ascii_lowercase + string.digits):
    """
    Args:
        size: size of string
        chars: list of chars allowed

    Returns:
        str: randomString with length and allowed chars
    """
    return ''.join(PropertyProvider.random.choice(chars) for _ in range(size))


def get_random_str(length=None):
    """
    Args:
        length: None, int

    Returns: randomstring for given length

    special chars/space is not part of generated random string
    """
    random = PropertyProvider.random
    if not length:
        length = random.randint(1, 10)
    initial = random.choice(string.ascii_letters)
    return initial + random_string_generator(length - 1, string.ascii_letters + string.digits)


def get_random_int(length=None):
    random = PropertyProvider.random
    if not length:
        length = random.randint(1, 10)
    return random.randint(10 ** (length - 1), 10 ** (length))


def get_random_float(*_args):
    random = PropertyProvider.random
    length = random.randint(1, 10)
    denom = random.randint(1, 10)
    return random.randint(10 ** (length - 1), 10 ** (length)) / 10 ** denom


def get_random_bool(*_args):
    random = PropertyProvider.random
    return random.choice(['true', 'false'])


def get_uuid(*_args):
    return str(uuid.uuid4())


def get_random_slug(length):
    if not length or length <= 1:
        length = 4
    return '-'.join(random_string_generator(size=get_random_int(1)) for _i in range(length))


def get_timestamp(*_args):
    return int(datetime.timestamp(datetime.now()))


class PropertyProvider:
    """
        1. properties defined in file itself ({{a=10}})
            allowed values are
            {{ a=ranga}} {{a=ranga }} {{ a=ranga }} {{ a="ranga" }} {{ a='ranga' }}
            a=ranga for all above
            {{ a="ranga "}}
            in above case whitespace is considered
        2. properties from command line
        3. properties from file's activated env
        4. properties from files's '*'
    :return:
    """
    random = Random()
    var_regex = re.compile(r'{{(?P<var>.*?)}}', re.DOTALL)
    rand_map: Dict[str, FunctionType] = {
        '$randomStr': get_random_str,
        '$randomInt': get_random_int,
        '$randomFloat': get_random_float,
        '$randomBool': get_random_bool,
        '$guid': get_uuid,
        '$uuid': get_uuid,
        '$timestamp': get_timestamp,
        '$randomLoremSlug': get_random_slug,
        '$randomSlug': get_random_slug,
    }

    # random_string_regex = re.compile(
    #     r'.*?(?P<category>\$randomStr|\$randomInt|\$randomBool|\$randomFloat|\$guid)(?P<length>:\d*)?')
    random_string_regex = re.compile(
        r'.*?(?P<category>' + "|".join("\\" + key for key in rand_map) + ')(?P<length>:\d*)?')

    def __init__(self, property_file=""):
        self.command_properties = {}
        self.env_properties = {}
        self.infile_properties: Dict[str, Property] = {}
        self.property_file = property_file
        self._resolvable_properties = set()

    def add_command_property(self, key: str, value: str):
        self.command_properties[key] = value

    def add_env_property_from_dict(self, env: dict):
        # TODO fix this, this could be json.dumps and
        #  json.loads will create performance issues
        for key in env:
            if not isinstance(env[key], str):
                self.env_properties[key] = json.dumps(env[key])
            else:
                self.env_properties[key] = env[key]

    def add_env_property(self, key: str, value: str):
        self.env_properties[key] = value

    def add_infile_properties(self, content):
        self.infile_properties = self.get_properties_for_content(content)

    def get_properties_for_content(self, content):
        infile_properties: Dict[str, Property] = {}
        out = self.var_regex.findall(content)
        tuple(self.validate_n_gen(x, infile_properties) for x in out if x)
        return infile_properties

    def check_properties_for_content(self, content):
        content_prop_needed = self.get_properties_for_content(content)
        props_needed = set(content_prop_needed.keys())

        missing_props = props_needed - self.available_properties_list()
        if len(missing_props) != 0:
            raise PropertyNotFoundException(
                var=missing_props, propertyfile=self.property_file if self.property_file else "not specified")
        return content_prop_needed, props_needed

    @lru_cache
    def available_properties_list(self):
        return set(self.env_properties.keys()).union(
            set(self.command_properties.keys())).union(
            set(key for key in self.infile_properties if
                self.infile_properties[key].value is not None or PropertyProvider.is_random_key(key)))

    def get_all_properties_variables(self):
        # TODO
        d = dict()
        d.update(self.command_properties)
        return d

    @staticmethod
    def is_random_key(key):
        return any(key.startswith(rand_category_name) for rand_category_name in PropertyProvider.rand_map)

    def get_updated_content(self, content, type='str'):
        content_prop_needed, props_needed = self.check_properties_for_content(content)
        for var in props_needed:
            # command line props take preference
            func = self.resolve_property_string if type == 'str' else self.resolve_property_object
            value = func(var)
            base_logger.debug(f'using `{value}` for property {var}')
            for text_to_replace in content_prop_needed[var].text:
                content = content.replace("{{" + text_to_replace + "}}", value)
        return content

    @staticmethod
    def validate_n_gen(prop, cache: Dict[str, Property]):
        p: Union[Property, None] = None
        if '=' in prop:
            key_values = prop.split('=')
            if len(key_values) != 2:
                raise HttpFileException(message='default property should not have multiple `=`')
            key, value = key_values
            # strip white space for keys
            key = key.strip()

            # strip white space for values
            value = value.strip()
            if value and value[0] == value[-1] and value[0] in {"'", '"'}:
                # strip "'" "'" if it has any
                # like ranga=" ramprasad" --> we should replace with " ramprasad"
                value = value[1:-1]

            match = PropertyProvider.get_random_match(value)
            if match:
                if key in cache:
                    p = cache[key]
                    p.text.append(prop)
                else:
                    p = Property([prop], key, PropertyProvider.resolve_random(value, match))
            else:
                # if result is randomType
                if key in cache:
                    p = cache[key]
                    p.text.append(prop)
                    if cache[key].value and value != cache[key].value:
                        p.value = HttpFileException(
                            message=f'propert.y: `{key}` is defaulted with two/more different values, panicked ')
                    else:
                        p.value = value
                else:
                    p = Property([prop], key, value)
            cache.setdefault(key, p)
        else:
            if prop in cache:
                cache[prop].text.append(prop)
            else:
                p = Property([prop])
                cache.setdefault(prop, p)
        return p

    @staticmethod
    def resolve_random(prop, match):
        if (match):
            groups = match.groupdict()
            category = groups['category']
            rand_length = int((groups.get('length') if groups.get('length') else ':0')[1:])
            value = str(PropertyProvider.rand_map[category](rand_length))
            return prop.replace("".join(i for i in match.groups() if i), value)
        return prop

    @staticmethod
    def get_random_match(prop):
        match = PropertyProvider.random_string_regex.match(prop)
        return match

    def resolve_property_string(self, key: str):
        if PropertyProvider.is_random_key(key):
            return PropertyProvider.resolve_random(key, PropertyProvider.get_random_match(key))
        prop_values = self.command_properties.get(key), self.env_properties.get(key), self.infile_properties[key].value
        for prop_value in prop_values:
            if prop_value is not None:
                if isinstance(prop_value, HttpFileException):
                    raise prop_value
                else:
                    base_logger.debug(f"property `{key}` resolved with value `${prop_value}`")
                    return prop_value

    def resolve_property_object(self, key: str) -> object:
        val = self.resolve_property_string(key)
        try:
            return json.loads(val)
        except JSONDecodeError:
            base_logger.debug(f"property `{key}` value non json decodable")
            return val
