import argparse
import json

from clinical_pipeline.generate import generate_data
from clinical_pipeline.runner import run_pipeline
from clinical_pipeline.simulate_changes import simulate_source_changes


def main() -> None:
    parser = argparse.ArgumentParser(prog="clinical_pipeline")
    parser.add_argument(
        "command",
        choices=["generate", "run", "simulate"],
        help="Generate synthetic sources, run the pipeline, or simulate source updates.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--no-dbt",
        action="store_true",
        help="Skip dbt model builds and tests.",
    )
    parser.add_argument(
        "--no-generate",
        action="store_true",
        help="Use existing CSV files in data/source/.",
    )
    args = parser.parse_args()

    if args.command == "generate":
        generate_data(seed=args.seed)
        print("Synthetic source data generated.")
    elif args.command == "simulate":
        print(json.dumps(simulate_source_changes(), indent=2))
    else:
        result = run_pipeline(
            generate=not args.no_generate,
            run_dbt=not args.no_dbt,
            seed=args.seed,
        )
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
