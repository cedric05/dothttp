import os


def get_real_file_path(path='http.tx', current_file=__file__, ):
    if os.path.exists(current_file):
        tx_model_path = os.path.join(os.path.dirname(os.path.abspath(current_file)), path)
    else:
        tx_model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(current_file))), path)
    return tx_model_path


def triple_or_double_tostring(list_of_triple_or_double, update_content_func):
    return "".join(
        [update_content_func(i.triple[3:-3]) if i.triple else update_content_func(i.str) for i in
         list_of_triple_or_double])


def quote_or_unquote(line: str):
    if '"' in line and "'" in line:
        return '"', line.replace("'", "\\'")
    elif '"' in line:
        return "'", line
    else:
        return '"', line


APPLICATION_JSON = "application/json"
