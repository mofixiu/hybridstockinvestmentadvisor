"""Legacy entry point routed to the time-ordered swing evaluation.

Historical accuracy-only validation does not authorize a live signal. This
command now produces the same review-only 5/10/20-session report as the current
evaluation pipeline and requires a benchmark and explicit cost assumption.
"""

from src.modeltraining.swing_backtest import main


if __name__ == "__main__":
    main()
