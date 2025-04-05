import logging
from typing import Dict, List, Optional, Union

from ..utils.property_util import PropertyProvider, StringFormatPropertyResolver, get_no_replace_property_provider
from ..utils.common import triple_or_double_tostring
from .expression import Token, TokenType

base_logger = logging.getLogger("dothttp")


class JsonParser:
    def __init__(self, property_util: PropertyProvider):
        self.property_util = property_util

    def json_or_array_to_json(self, model) -> Union[Dict, List]:
        if isinstance(model, Dict) or isinstance(model, List):
            return model
        if json_object := model.object:
            return {
                self.get_key(member): self.jsonmodel_to_json(member.value)
                for member in json_object.members
            }
        elif array := model.array:
            return [self.jsonmodel_to_json(value) for value in array.values]
        elif var_value := model.var:
            return self.property_util.get_updated_obj_content(var_value)
        else:
            return self.get_simple_non_iterative(model)

    def get_key(self, member):
        if member.key:
            return triple_or_double_tostring(member.key, self.property_util.get_updated_content)
        elif member.var:
            return self.property_util.get_updated_obj_content(member.var)

    def get_simple_non_iterative(self, model):
        if id := model.id:
            try: 
                return self.property_util.get_updated_obj_content("{{%s}}" % id)
            except:
                # in case variable not found, 
                return id
        if str_value := model.strs:
            return triple_or_double_tostring(str_value, self.property_util.get_updated_content)
        elif var_value := model.var:
            return self.property_util.get_updated_obj_content(var_value)
        elif int_val := model.int:
            return int_val.value
        elif flt := model.flt:
            return flt.value
        elif bl := model.bl:
            return bl.value
        elif inter := model.inter:
            return inter[2:-1].format_map(StringFormatPropertyResolver(self.property_util))
        elif model == "null":
            return None
        elif expr := model.expr:
            try:
                expression = Token.parse_expr(expr)
                new_expression = ""
                for token in expression:
                    if token.token_type == TokenType.VAR:
                        value = self.property_util.resolve_property_string(token.value)
                    else:
                        value = token.value
                    if not isinstance(value, str):
                        value = str(value)
                    new_expression += value
                return eval(new_expression)
            except:
                base_logger.error(f"error in evaluating expression {expr}, new expression {new_expression}")
                return 0

    def jsonmodel_to_json(self, model):
        if json_object := model.object:
            return {
                self.get_key(member): self.jsonmodel_to_json(member.value)
                for member in json_object.members
            }
        elif array := model.array:
            return [self.jsonmodel_to_json(value) for value in array.values]
        else:
            return self.get_simple_non_iterative(model)


# Supporting function
def json_or_array_to_json(model, property_util: Optional[PropertyProvider]=None) -> Union[Dict, List]:
    if property_util is None:
        # This is a hack to ignore replacement of variables where it is not needed
        property_util = get_no_replace_property_provider()
    parser = JsonParser(property_util)
    return parser.json_or_array_to_json(model)


def jsonmodel_to_json(model, property_util: Optional[PropertyProvider]=None) -> Union[Dict, List]:
    if property_util is None:
        # This is a hack to ignore replacement of variables where it is not needed
        property_util = get_no_replace_property_provider()
    parser = JsonParser(property_util)
    return parser.jsonmodel_to_json(model)