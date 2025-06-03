import json
import logging
import os
import re
import string
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from json import JSONDecodeError
from random import Random
from types import FunctionType
from typing import Dict, List, Union

from ..exceptions import HttpFileException, PropertyNotFoundException
import ast
import operator

base_logger = logging.getLogger("dothttp")


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
    return "".join(PropertyProvider.random.choice(chars) for _ in range(size))


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
    return initial + random_string_generator(
        length - 1, string.ascii_letters + string.digits
    )


def get_random_int(length=None):
    random = PropertyProvider.random
    if not length:
        length = random.randint(1, 10)
    return random.randint(10 ** (length - 1), 10 ** (length))


def get_random_float(*_args):
    random = PropertyProvider.random
    length = random.randint(1, 10)
    denom = random.randint(1, 10)
    return random.randint(10 ** (length - 1), 10 ** (length)) / 10**denom


def get_random_bool(*_args):
    random = PropertyProvider.random
    return random.choice(["true", "false"])


def get_uuid(*_args):
    return str(uuid.uuid4())


def get_random_slug(length):
    if not length or length <= 1:
        length = 4
    return "-".join(
        random_string_generator(size=get_random_int(1)) for _i in range(length)
    )


def get_timestamp(*_args):
    return int(datetime.timestamp(datetime.now()))

math_operators = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
    '%': operator.mod,
    '**': operator.pow
}

def evaluate_expression(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode='eval')
        code = compile(tree, '<string>', 'eval')
        result = eval(code, {"__builtins__": None}, math_operators)
        return str(result)
    except Exception as e:
        base_logger.error(f"Error evaluating expression `{expression}`: {e}")
        return expression

property_regex = re.compile(r"{{(?P<var>.*?)}}", re.DOTALL)

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
    var_regex = property_regex
    rand_map: Dict[str, FunctionType] = {
        "$randomStr": get_random_str,
        "$randomInt": get_random_int,
        "$randomFloat": get_random_float,
        "$randomBool": get_random_bool,
        "$guid": get_uuid,
        "$uuid": get_uuid,
        "$timestamp": get_timestamp,
        "$randomLoremSlug": get_random_slug,
        "$randomSlug": get_random_slug,
    }

    # random_string_regex = re.compile(
    #     r'.*?(?P<category>\$randomStr|\$randomInt|\$randomBool|\$randomFloat|\$guid)(?P<length>:\d*)?')
    random_string_regex = re.compile(
        r".*?(?P<category>"
        + "|".join("\\" + key for key in rand_map)
        + ")(?P<length>:\\d*)?"
    )

    expression_regex = re.compile(r"\$expr:(?P<expression>.*)")

    def __init__(self, property_file=""):
        self.infile_properties: Dict[str, Property] = {}
        self.env_properties = {}
        self.system_command_properties = {}
        self.command_line_properties = {}
        self.property_file = property_file
        self.is_running_system_command_enabled = False
        self.errors = []

    def enable_system_command(self):
        self.is_running_system_command_enabled = True

    def add_system_command_properties(self, system_command_dict: dict):
        self.system_command_properties.update(system_command_dict)

    def add_command_line_property(self, key: str, value: str):
        self.command_line_properties[key] = value

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
        self.update_in_file_properties_for_content(
            content, self.infile_properties)

    def get_properties_for_content(self, content):
        infile_properties: Dict[str, Property] = {}
        self.update_in_file_properties_for_content(content, infile_properties)
        return infile_properties

    def update_in_file_properties_for_content(self, content, infile_properties):
        out = self.var_regex.findall(content)
        tuple(self.validate_n_gen(x, infile_properties) for x in out if x)

    def check_properties_for_content(self, content):
        content_prop_needed = self.get_properties_for_content(content)
        props_needed = set(content_prop_needed.keys())
        available_properties = self.available_properties_list()
        missing_props = props_needed - available_properties
        if len(missing_props) != 0:
            raise PropertyNotFoundException(
                var=missing_props,
                propertyfile=(
                    self.property_file if self.property_file else "not specified"
                ),
            )
        return content_prop_needed, props_needed

    def available_properties_list(self):
        return (
            set(self.env_properties.keys())
            .union(set(self.command_line_properties.keys()))
            .union(set(self.system_command_properties.keys()))
            .union(set((key.strip("DOTHTTP_ENV_") for key in os.environ.keys() if key.startswith("DOTHTTP_ENV_"))))
            .union(
                set(
                    key.strip()
                    for key in self.infile_properties
                    if self.infile_properties[key].value is not None
                    or PropertyProvider.is_special_keyword(key)
                )
            )
        )

    def get_all_properties_variables(self):
        # TODO
        d = dict()
        d.update(self.command_line_properties)
        return d

    @staticmethod
    def is_special_keyword(key):
        key = key.strip()
        ret = any(
            key.startswith(rand_category_name)
            for rand_category_name in PropertyProvider.rand_map
        )
        return ret or key.startswith("$expr:")

    def get_updated_content(self, content, type="str"):
        try:
            content_prop_needed, props_needed = self.check_properties_for_content(
                content)
            for var in props_needed:
                if type == "str":
                    value = self.resolve_property_string(var)
                    for text_to_replace in content_prop_needed[var].text:
                        content = content.replace(
                            "{{" + text_to_replace + "}}", str(value)
                        )
                else:
                    content = self.resolve_property_object(var)
                base_logger.debug(f"using `{content}` for property {var}")
            return content
        except PropertyNotFoundException as e:
            self.errors.append(e)
            return content
    
    def get_updated_obj_content(self, content):
        return self.get_updated_content(content, "obj")

    def validate_n_gen(self, prop, cache: Dict[str, Property]):
        p: Union[Property, None] = None
        if "=" in prop:
            # consider only first `=`
            key, value = prop.split("=", 1)
            # strip white space for keys
            key = key.strip()

            # strip white space for values
            value = value.strip()
            if value and value[0] == value[-1] and value[0] in {"'", '"'}:
                # strip "'" "'" if it has any
                # like ranga=" ramprasad" --> we should replace with "
                # ramprasad"
                value = value[1:-1]
            elif value and (value.startswith("p'") and value.endswith("'") or value.startswith('p"') and value.endswith('"')):
                # lets substitute property with property
                value = value[2:-1]
                prop_handler = self
                class PropertyResolver:
                    # hassle of creating class is to make it work with format_map
                    # instead of format which can be used with dict and can cause memory leak
                    def __getitem__(self, key):
                        if key in prop_handler.command_line_properties:
                            return prop_handler.command_line_properties[key]
                        if key in prop_handler.env_properties:
                            return prop_handler.env_properties[key]
                        if key in cache and isinstance(cache[key].value, str):
                            return cache[key].value
                        raise KeyError(key)
                value = value.format_map(PropertyResolver())
            match = PropertyProvider.get_random_match(value)
            if match:
                if key in cache:
                    p = cache[key]
                    p.text.append(prop)
                else:
                    p = Property(
                        [prop], key, PropertyProvider.resolve_special(
                            value, match)
                    )
            else:
                # if result is randomType
                if key in cache:
                    p = cache[key]
                    p.text.append(prop)
                    if cache[key].value and value != cache[key].value:
                        p.value = HttpFileException(
                            message=f"propert.y: `{key}` is defaulted with two/more different values, panicked "
                        )
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
    def resolve_special(prop, match):
        if match:
            groups = match.groupdict()
            category = groups["category"]
            rand_length = int(
                (groups.get("length") if groups.get("length") else ":0")[1:]
            )
            value = str(PropertyProvider.rand_map[category](rand_length))
            return prop.replace("".join(i for i in match.groups() if i), value)
        return prop

    @staticmethod
    def get_random_match(prop):
        match = PropertyProvider.random_string_regex.match(prop)
        return match
    
    def add_infile_property_from_var(self, key, value, can_override: bool = True):
        """
        Adds a property from a variable to infile_properties.
        If can_override is True, the property will always be added/updated.
        If can_override is False, the property will only be added if it doesn't exist
        or its value is None.
        """
        if can_override or (
            key not in self.infile_properties or self.infile_properties[key].value is None
        ):
            self.infile_properties[key] = Property([''], key, value)

    def resolve_system_command_prop(self, key):
        command = self.system_command_properties.get(key)
        if command is None:
            return None
        else:
            if not self.is_running_system_command_enabled:
                base_logger.error(
                    f"system command is disabled, by adding '@insecure'")
                return 'running system command is disabled, enable it by adding @insecure'
            try:
                result = subprocess.run(
                    command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                return result.stdout
            except subprocess.CalledProcessError as e:
                base_logger.error(
                    f"Error while executing system command: {command} with error: {e}")
                return ''

    def resolve_property_string(self, key: str):
        if PropertyProvider.is_special_keyword(key):
            match = PropertyProvider.get_random_match(key)
            if not match:
                match = PropertyProvider.expression_regex.match(key)
                if match:
                    return evaluate_expression(match.groupdict()["expression"])
            return PropertyProvider.resolve_special(
                key, match
            )

        def find_according_to_category(key):
            yield self.command_line_properties.get(key)
            yield self.env_properties.get(key)
            yield self.infile_properties[key].value
            yield os.environ.get(f"DOTHTTP_ENV_{key}")
            yield self.resolve_system_command_prop(key)

        for prop_value in find_according_to_category(key):
            if prop_value is not None:
                if isinstance(prop_value, HttpFileException):
                    raise prop_value
                else:
                    base_logger.debug(
                        f"property `{key}` resolved with value `{prop_value}`"
                    )
                    return prop_value

    def resolve_property_object(self, content: str) -> object:
        val = self.resolve_property_string(content)
        # if val is string then try to convert to json
        if isinstance(val, str):
            try:
                return json.loads(val)
            except JSONDecodeError:
                base_logger.debug(f"property `{content}` value non json decodable")
                return val
        else:
            return val


def get_no_replace_property_provider():
    property_util = PropertyProvider()
    property_util.get_updated_content = lambda x: x
    property_util.get_updated_obj_content = lambda x: x
    return property_util


class StringFormatPropertyResolver:
    def __init__(self, property_util: PropertyProvider):
        self.property_util = property_util
    # hassle of creating class is to make it work with format_map
    # instead of format which can be used with dict and can cause memory leak
    def __getitem__(self, key):
        if key in self.property_util.command_line_properties:
            return self.property_util.command_line_properties[key]
        if key in self.property_util.env_properties:
            return self.property_util.env_properties[key]
        if key in self.property_util.infile_properties and self.property_util.infile_properties[key].value is not None:
            return self.property_util.infile_properties[key].value
        raise KeyError(key)