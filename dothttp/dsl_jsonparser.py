import json
from typing import Union, Dict, List


def json_or_array_to_json(model, update_content_func) -> Union[Dict, List]:
    if isinstance(model, Dict) or isinstance(model, List):
        # TODO
        # this is bad
        # hooking here could lead to other issues
        return model
    if array := model.array:
        return [update_content_func(value, update_content_func) for value in array.values]
    elif json_object := model.object:
        return {
            # TODO i'm confused about key weather it should be string or int or float (value has float, number,
            #  boolean, null) but key is unsupported by requests
            get_key(member, update_content_func): jsonmodel_to_json(member.value, update_content_func)
            for
            member in
            json_object.members}


def get_key(member, update_content_func):
    if member.key:
        return update_content_func(member.key)
    return update_content_func(member.var)


def jsonmodel_to_json(model, update_content_func):
    if str_value := model.str:
        return update_content_func(str_value.value)
    elif var_value := model.var:
        return get_json_data(var_value, update_content_func)
    elif flt := model.flt:
        return flt.value
    elif bl := model.bl:
        return bl.value
    elif json_object := model.object:
        return {member.key: jsonmodel_to_json(member.value, update_content_func) for member in json_object.members}
    elif array := model.array:
        return [jsonmodel_to_json(value, update_content_func) for value in array.values]
    elif model == 'null':
        return None


def get_json_data(var_value, update_content_func):
    content: str = update_content_func(var_value)
    try:
        return json.loads(content)
    except ValueError:
        return content
