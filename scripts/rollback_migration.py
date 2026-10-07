"""Roll back the product-foundation schema after an explicit data-loss flag."""

import argparse

from scripts.migrate import rollback


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-drop-research-data",
        action="store_true",
        help="required because rollback deletes verified market bars and paper signals",
    )
    args = parser.parse_args()
    rollback(confirm_drop_data=args.confirm_drop_research_data)


if __name__ == "__main__":
    main()
