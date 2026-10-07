"""Legacy training name, now routed to review-only swing validation."""

from src.modeltraining.swing_backtest import main


def train_models(*_args, **_kwargs):
    raise RuntimeError(
        "Automatic model fitting is disabled. Run this entry point with "
        "--benchmark and --round-trip-cost-bps to create a chronological review report."
    )


if __name__ == "__main__":
    main()
