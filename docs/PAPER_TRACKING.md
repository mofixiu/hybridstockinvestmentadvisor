# NGX paper tracking

The paper tracker uses Investo daily history transiently. It does not write raw
prices, volume, or feature rows to the database or disk. It records derived
10-session predictions and, after ten future closes are available, derived
realized returns. It never publishes an app signal.

## Run once

From the backend repository root, with the local `.env` configured:

```sh
source venv/bin/activate
python -m scripts.run_investo_paper_tracking --round-trip-cost-bps 300
```

The report is written to `data/reports/paper_track_latest.json`, which is
gitignored. The model uses the same 300 bps assumption as the current historical
backtest.

## Schedule on this Mac

Run `sh scripts/install_paper_tracking_schedule.sh` once. It installs a
per-user `launchd` job for weekdays at 16:30 local time. The Mac must be logged
in and able to reach the configured database and Investo API. If it is asleep
at the scheduled time, launchd may run the missed job when the Mac wakes.

The log is `data/reports/paper_tracking.log`. To stop the job:

```sh
launchctl bootout "gui/$(id -u)" \
  "/Users/mofiyinebo/Library/LaunchAgents/com.hybstockadvisor.paper-tracking.plist"
```

The installed schedule does not move the Investo key out of the ignored backend
`.env` file. Do not commit that file or put the key in Flutter.
