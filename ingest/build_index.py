"""
CLI wrapper to run the index building from existing JSONL or raw text files.
Example:
  python ingest/build_index.py --jsonl data/nutrition_qa.jsonl --out data/index
"""
from pathlib import Path
from ingest.processor import build_from_jsonl


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--jsonl', help='input JSONL file', default='data/nutrition_qa.jsonl')
    p.add_argument('--out', help='output index dir', default='data/index')
    p.add_argument('--model', help='sentence-transformers model', default='all-MiniLM-L6-v2')
    args = p.parse_args()

    idx, meta = build_from_jsonl(Path(args.jsonl), Path(args.out), model_name=args.model)
    print('Index saved to', idx)
    print('Metadata saved to', meta)


if __name__ == '__main__':
    main()
