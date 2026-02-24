import json
import os


def test_data_file_exists_and_valid():
    here = os.path.dirname(__file__)
    data_file = os.path.join(here, '..', 'data', 'nutrition_qa.jsonl')
    assert os.path.exists(data_file)
    count = 0
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            assert 'id' in obj
            assert 'text' in obj
            count += 1
    assert count >= 3
