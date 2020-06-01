import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Generate a custom lexical dataset parser and dataset metadata for a particular dataset")
    parser.add_argument("excel", type=Path, help="The Excel file to inspect")
    args = parser.parse_args()

if __name__ == "__main__":
    main()

