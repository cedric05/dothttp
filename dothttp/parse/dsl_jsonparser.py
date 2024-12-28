import json
from typing import Dict, List, Optional, Union

from ..utils.property_util import PropertyProvider, get_no_replace_property_provider
from ..utils.common import triple_or_double_tostring


class JsonParser:
    def __init__(self, property_util: PropertyProvider):
        self.property_util = property_util

    def json_or_array_to_json(self, model) -> Union[Dict, List]:
        if isinstance(model, Dict) or isinstance(model, List):
            return model
        if array := model.array:
            return [self.jsonmodel_to_json(value) for value in array.values]
        elif json_object := model.object:
            return {
                self.get_key(member): self.jsonmodel_to_json(member.value)
                for member in json_object.members
            }

    def get_key(self, member):
        if member.key:
            return triple_or_double_tostring(member.key, self.property_util.get_updated_content)
        elif member.var:
            return self.property_util.get_updated_obj_content(member.var)

    def jsonmodel_to_json(self, model):
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
        elif json_object := model.object:
            return {
                self.get_key(member): self.jsonmodel_to_json(member.value)
                for member in json_object.members
            }
        elif array := model.array:
            return [self.jsonmodel_to_json(value) for value in array.values]
        elif model == "null":
            return None
        elif expr := model.expr:
            return eval(expr)


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