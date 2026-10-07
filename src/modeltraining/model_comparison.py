"""Legacy comparison entry point, now using leakage-aware validation."""

from src.modeltraining.swing_backtest import main


def run_comparative_analysis(*_args, **_kwargs):
    raise RuntimeError(
        "In-sample champion selection is disabled. Run this entry point with "
        "--benchmark and --round-trip-cost-bps for a review-only walk-forward report."
    )


if __name__ == "__main__":
    main()
