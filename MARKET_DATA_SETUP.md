# Market data and research setup

## Free personal NGX data: Investo

The backend supports Investo's daily NGX feed using the `INVESTO_API` environment variable shown in your Render screenshot. The key stays on the backend; Flutter never receives it. Investo's developer plan is free for personal/evaluation use, has a 1,000-request daily limit, and provides EOD prices and history. Attribution is required. Its terms do not allow permanent raw-price mirrors or sharing raw prices with other users without written permission.

- [Investo developer API](https://investo.ng/developers)
- [Investo API terms](https://investo.ng/api-terms)

For personal use, configure these Render variables:

```text
INVESTO_API=<the key already stored in Render>
INVESTO_PERSONAL_OWNER_EMAIL=<email used by your HybStockAdvisor account>
```

Do not paste the key into chat, Flutter, or GitHub. The backend only serves this free-tier market data to the matching owner account. Invited testers will not receive Investo prices unless Investo gives written permission for that use. The adapter keeps provider responses in process memory for five minutes and does not write Investo's raw feed to MySQL or CSV.

## Licensed NGX data for tester access

For invited tester distribution or persistent historical storage, the backend also supports the official NGX Market Data API for end-of-day prices and OHLCV history. This adapter is opt-in. NGX documents these feeds for authorized clients and requires an access token. An API token alone does not establish permission to redistribute data to invited users; review the applicable pricing, policy, and agreement materials first.

- [NGX API documentation](https://marketdataapiv3.ngxgroup.com/portal/Home/Documentation)
- [NGX data pricing, policies, and contracts](https://ngxgroup.com/exchange/data/data-pricing-policies-contracts/)
- [NGX X-DataPortal](https://ngxgroup.com/exchange/data/x-dataportal/)
- [GSE data services for the later Ghana phase](https://gse.com.gh/data-services/)

NGX lists seven days of historical price data as free in its Data Portal. Treat that as portal access only; do not assume it covers API access, historical backfills, or serving data to testers. Review the current NGX agreement and the intended app use before enabling data.

## Configure the backend and database

1. Copy `.env.example` to `.env` and provide the database URL and a random `JWT_SECRET_KEY` of at least 32 characters. Configure email and Gemini only if those services are needed.
2. For personal testing, set `INVESTO_API` and `INVESTO_PERSONAL_OWNER_EMAIL` as described above. For invited testers, use an NGX data agreement that permits the intended service, then set `NGX_DATA_API_TOKEN` and `NGX_MARKET_DATA_USE_APPROVED=true`. Do not use the Investo free-tier key to serve tester accounts.
3. Apply the versioned schema migration from the repository root:

   ```bash
   python -m scripts.migrate
   ```

   To roll back this product-foundation schema later, run `python -m scripts.rollback_migration --confirm-drop-research-data`. This removes invitation, market-bar, paper-signal, and model-approval tables while preserving accounts and portfolios; the flag is required because market research data is deleted.

4. Add invited account email addresses to `INVITED_USER_EMAILS` as a comma-separated Render environment variable. The Flutter signup screen remains unchanged; the backend accepts only those emails and the personal owner email. For clients that submit a one-use code directly, the optional token flow remains available:

   ```bash
   python -m scripts.create_invite --expires-in-days 7
   ```

5. Only when an NGX agreement permits persistent storage, ingest the authorized EOD snapshot after market close. Re-running the job updates the same exchange/symbol/date rows rather than duplicating them:

   ```bash
   python -m scripts.ingest_market_data
   ```

   Historical data can be backfilled for a symbol when the applicable NGX permission permits it:

   ```bash
   python -m scripts.ingest_market_data --history-symbol GTCO --start-date 2020-01-01 --end-date 2026-10-07
   ```

6. Export verified market history for model research:

   ```bash
   python -m scripts.export_market_history
   python -m src.processing.feature_engineering
   ```

The licensed NGX ingestion command is intended to run once after the daily market close. Configure it as a scheduled job on the chosen host; there is no in-app refresh endpoint that exposes the provider token. A failed or unconfigured source leaves prices and signals unavailable rather than substituting samples. Do not use this persistence workflow with Investo's free personal key.

## Signal research gate

The target columns now cover 5, 10, and 20 trading sessions. The primary horizon is ten sessions. The evaluation command requires both the matching market-index history and an explicit round-trip cost assumption:

```bash
python -m src.modeltraining.swing_backtest \
  --benchmark path/to/ngx_all_share_index.csv \
  --round-trip-cost-bps 100
```

The benchmark file must contain `date,close`, with one row per index trading session. Replace the example cost with a documented assumption for the intended market and account. The report is marked `review_required`; it does not publish signals or claim model value automatically. The API serves a directional signal only when the model has a persisted release approval, the latest-close prediction is explicitly published, and the source data is fresh.

For personal research from Investo's free API, use the memory-only command instead of ingesting Investo bars into the database:

```bash
python -m scripts.train_swing_from_investo --round-trip-cost-bps <documented-total-cost>
```

Optionally pass `--symbols GTCO,MTNN` to limit history requests. With no symbol list, the command uses the Investo-listed equities and NGX All-Share Index. It calculates chronological 5/10/20-session evaluations and fits a 10-session research candidate only if validation folds and both training classes are available. It saves derived metrics and the unapproved model under ignored `data/reports/` and `models/research_only/` paths. It does not persist raw provider bars, approve the model, or publish app signals. The required cost must represent your intended account's round-trip fees and slippage; do not use a placeholder as a real backtest assumption.

Once verified history is present, run `python -m scripts.generate_paper_predictions` after each successful daily ingestion. It fits the same price-only 10-session classifier evaluated by the walk-forward backtest, excludes labels whose future prices were not yet available at the prediction date, stores the contemporaneous training-period prior, and writes only paper rows. Re-running it for the same close is idempotent. Paper rows are never served as live signals.

An analyst can also record an explicit candidate with `python -m scripts.record_paper_signal --symbol GTCO --direction positive --probability-positive 0.58 --prior-probability-positive 0.51 --model-version price_only_hgb_10d_v1 --evidence "brief model rationale"`. Manual rows without a prior captured at prediction time can be reviewed but cannot pass the release gate. After the chosen horizon has elapsed, run `python -m scripts.paper_track_signals --round-trip-cost-bps 100`; it records realized outcomes and writes a review-only report. The paper Brier comparison uses each prediction's stored prior on the same scored samples; it does not estimate a baseline from the paper outcomes.

To request model approval, provide both reports and an explicit sample threshold and reviewer:

```bash
python -m scripts.approve_model \
  --backtest-report data/reports/swing_backtest.json \
  --paper-report data/reports/paper_track_latest.json \
  --symbol GTCO \
  --model-version swing-v1 \
  --minimum-paper-samples 40 \
  --reviewer "Your name"
```

Approval fails unless the backtest report matches the exact model version, 10-session walk-forward Brier score beats its prior baseline, net excess return beats the matched exchange index after costs, and the paper group for that exact symbol/model has enough matched samples, better Brier score, hit rate above 50%, and positive net directional return. Approval is stored with both reports and reviewer identity. To publish a current prediction from that approved model, use `python -m scripts.publish_signal --symbol GTCO --direction positive --probability-positive 0.58 --model-version price_only_hgb_10d_v1 --evidence "brief model rationale"`. The signal must match the latest verified close; no trade is placed. No training or approval step publishes signals automatically.

## API behavior

- `/api/summary`, `/api/forecast/{symbol}`, `/api/insights/{symbol}`, and `/api/user/{id}/assets` require authentication.
- Market responses identify the exchange, NGN currency, data source, source timestamp, and stale state. With Investo configured, the API fetches directly and limits raw-price access to `INVESTO_PERSONAL_OWNER_EMAIL`; otherwise it uses approved, persisted NGX bars. Empty data is returned as unavailable metadata; the API does not read ignored per-ticker CSV files.
- Registration requires a one-use, expiring invitation code. Existing user accounts are retained.
- Chat answers use verified data and state when data is absent or stale. No simulated social sentiment is part of the active data refresh path.

For Flutter Web, set `CORS_ALLOW_ORIGINS` to the exact deployed origin(s). Do not put Investo, NGX, or Gemini keys in the Flutter app.
