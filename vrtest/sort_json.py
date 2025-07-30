import json

with open('test_props.json', 'r') as f:
    data = json.load(f)

sorted_data = dict(sorted(data.items()))

with open('test_props.json', 'w') as f:
    f.write('{\n')
    items = list(sorted_data.items())
    for i, (key, value) in enumerate(items):
        if i == len(items) - 1:
            f.write(f'    "{key}": {json.dumps(value)}\n')
        else:
            f.write(f'    "{key}": {json.dumps(value)},\n')
    f.write('}\n')

