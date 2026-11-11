"""Validate administrator-provided backend metadata without reading AWS credentials."""
import os
import re
from pathlib import Path


def validate(text, expected):
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'(\w+)\s*=\s*(?:"([^"\n]+)"|(true|false))\s*', line)
        if not match:
            raise ValueError('Unsupported backend setting; use credential-free literal metadata only')
        key, string, boolean = match.groups()
        if key in values:
            raise ValueError('Duplicate backend setting')
        values[key] = string if string is not None else boolean == 'true'
    required = dict(expected, region='us-west-2', encrypt=True)
    if values != required:
        raise ValueError('Backend does not exactly match the administrator-approved existing state')


if __name__ == '__main__':
    validate(Path(os.environ['TF_BACKEND_FILE']).read_text(), {
        'bucket': os.environ['TF_STATE_BUCKET'],
        'key': os.environ['TF_STATE_KEY'],
        'dynamodb_table': os.environ['TF_LOCK_TABLE'],
    })
    print('Backend metadata matches approved existing state; migration is disabled')
