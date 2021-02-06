# TODO clean up
def json_or_array_to_json(model):
    if array := model.array:
        return [jsonmodel_to_json(value) for value in array.values]
    elif json_object := model.object:
        return {member.key: jsonmodel_to_json(member.value) for member in json_object.members}


def jsonmodel_to_json(model):
    if str_value := model.str:
        return str_value.value
    elif flt := model.flt:
        return flt.value
    elif bl := model.bl:
        return bl.value
    elif json_object := model.object:
        return {member.key: jsonmodel_to_json(member.value) for member in json_object.members}
    elif array := model.array:
        return [jsonmodel_to_json(value) for value in array.values]
    elif model == 'null':
        return None
