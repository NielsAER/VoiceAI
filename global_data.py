# shared_data.py

# Initialize an empty dictionary to store key-value pairs
global_data = {}


def add_key_value_pair(key, value):
    global_data[key] = value


def get_value_for_key(key):
    return global_data.get(key)
