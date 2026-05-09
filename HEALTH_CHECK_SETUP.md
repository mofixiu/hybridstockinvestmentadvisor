# Keep Render Service Alive with Health Check Cron Job

Since Render's free tier puts services to sleep after 15 minutes of inactivity, we need to ping it periodically.

## Option 1: macOS Crontab (Local Machine)

### Setup:
1. Make the script executable:
```bash
chmod +x health_check.py
```

2. Open your crontab editor:
```bash
crontab -e
```

3. Add one of these lines to run health checks every 10 minutes:
```cron
*/10 * * * * cd /Users/mofiyinebo/Documents/HybStockAdvisor && /usr/bin/python3 health_check.py >> /tmp/health_check.log 2>&1
```

Or every 5 minutes:
```cron
*/5 * * * * cd /Users/mofiyinebo/Documents/HybStockAdvisor && /usr/bin/python3 health_check.py >> /tmp/health_check.log 2>&1
```

4. Save and exit (Ctrl+X, then Y, then Enter in nano editor)

5. Check logs:
```bash
tail -f /tmp/health_check.log
```

---

## Option 2: GitHub Actions (RECOMMENDED - Always Free!)

This runs on GitHub's servers, so you don't need your local machine running.

1. Create folder structure:
```bash
mkdir -p .github/workflows
```

2. Create file: `.github/workflows/health-check.yml`

Add this content:
```yaml
name: Health Check

on:
  schedule:
    # Runs every 10 minutes
    - cron: '*/10 * * * *'
  # Allow manual trigger
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - name: Ping health endpoint
        run: |
          curl -X GET "https://your-app.onrender.com/" \
            -H "accept: application/json" \
            -w "\nStatus: %{http_code}\n"
```

3. Replace `https://your-app.onrender.com/` with your actual Render URL

4. Push to GitHub - it will automatically run!

---

## Option 3: Free Monitoring Services

Use free services that ping endpoints:
- **UptimeRobot** (https://uptimerobot.com) - Super easy, no setup needed
- **StatusCake** (https://www.statuscake.com)
- **Pingdom**

Just add your Render URL and set interval to 5-10 minutes.

---

## Setup Instructions

1. **First**, update the `RENDER_URL` in `health_check.py` with your actual Render URL:
```python
RENDER_URL = "https://hybstockadvisor.onrender.com"  # Update this
```

Or set environment variable:
```bash
export RENDER_URL="https://your-app.onrender.com"
```

2. **Test it**:
```bash
python3 health_check.py
```

You should see:
```
[2026-05-09 14:32:15] ✅ Health check passed: {'status': 'Online', 'message': 'Welcome to the HybStockAdvisor Engine'}
```

---

## Recommended: Use GitHub Actions + Local Backup

- GitHub Actions as primary (always running)
- Local cron as backup (if GitHub is down, unlikely but possible)

This gives you maximum uptime without paying anything!
