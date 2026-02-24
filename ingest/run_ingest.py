"""
Simple CLI to run ingestion steps (scaffold).

This script is intentionally conservative: it doesn't run large downloads by default.
Use it to orchestrate targeted downloads and to record provenance.
"""
import argparse
from ingest.collector import collect_gov_guideline, collect_open_textbook, collect_pmcoa_sample


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gov", action="store_true", help="Collect example gov guidelines (no-op)")
    parser.add_argument("--pmcoa", action="store_true", help="Collect PMCOA sample (placeholder)")
    args = parser.parse_args()

    if args.gov:
        urls = [
            "https://www.nhs.uk/live-well/eat-well/",
        ]
        collect_gov_guideline(urls)

    if args.pmcoa:
        collect_pmcoa_sample()

    if not (args.gov or args.pmcoa):
        print("No action. Use --gov or --pmcoa (this is a scaffold).")


if __name__ == "__main__":
    main()
