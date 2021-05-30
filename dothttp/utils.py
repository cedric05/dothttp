import os


def get_real_file_path(path='http.tx', current_file=__file__, ):
    if os.path.exists(current_file):
        tx_model_path = os.path.join(os.path.dirname(os.path.abspath(current_file)), path)
    else:
        tx_model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(current_file))), path)
    return tx_model_path
