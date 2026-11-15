import argparse
import json

from clinical_pipeline.generate import generate_data
from clinical_pipeline.runner import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="clinical_pipeline")
    parser.add_argument("command", choices=["generate", "run"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-dbt", action="store_true", help="Skip dbt model builds.")
    parser.add_argument("--no-generate", action="store_true", help="Use existing CSV files in data/source/.")
    args = parser.parse_args()
    if args.command == "generate":
        generate_data(seed=args.seed)
        print("Synthetic source data generated.")
    else:
        print(json.dumps(run_pipeline(generate=not args.no_generate, run_dbt=not args.no_dbt, seed=args.seed), indent=2))


if __name__ == "__main__":
    main()
