"""Regression checks for the fail-closed NGX research foundation."""

import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite://")

import numpy as np
import pandas as pd
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.migrate import apply, rollback
from src.api import main
from src.api.database import Base, InviteToken, MarketDailyBar, PaperSignal, User
from src.api.market_data import market_summary, published_signal, signal_as_dict
from src.data import investo_provider, ngx_provider
from src.processing import feature_engineering
from src.processing.feature_engineering import add_swing_features
from src.modeltraining.swing_backtest import evaluate_horizon, FEATURE_COLUMNS, MODEL_VERSION
from scripts import ingest_market_data
from scripts import generate_paper_predictions, paper_track_signals, record_paper_signal
from scripts import approve_model
from scripts import publish_signal
from urllib.error import URLError


class ProductFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", future=True)
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False)
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.db = self.Session()
        for table in reversed(Base.metadata.sorted_tables):
            self.db.execute(table.delete())
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_provider_is_disabled_without_approval_and_token(self):
        with patch.dict(os.environ, {"NGX_DATA_API_TOKEN": "", "NGX_MARKET_DATA_USE_APPROVED": "false"}):
            with patch.object(ngx_provider, "urlopen") as request:
                with self.assertRaises(ngx_provider.MarketDataProviderError):
                    ngx_provider.fetch_end_of_day()
                request.assert_not_called()

    def test_eod_normalization_keeps_only_verified_positive_equity_rows(self):
        payload = [
            {"Asset": "EQUITY", "Symbol": "gtco", "TradeDate": "2026-10-06", "Close": "80.25"},
            {"Asset": "BOND", "Symbol": "BOND1", "TradeDate": "2026-10-06", "Close": "100"},
            {"Asset": "EQUITY", "Symbol": "ZERO", "TradeDate": "2026-10-06", "Close": "0"},
        ]
        with patch.object(ngx_provider, "_fetch_json", return_value=payload):
            bars = ngx_provider.fetch_end_of_day()
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0]["symbol"], "GTCO")
        self.assertEqual(bars[0]["currency"], "NGN")
        self.assertTrue(bars[0]["provider_verified"])

    def test_history_rows_inherit_requested_symbol(self):
        with patch.object(ngx_provider, "_fetch_json", return_value={"data": [
            {"date": "2026-10-05", "close": 20},
            {"date": "2026-10-06", "close": 21},
        ]}):
            bars = ngx_provider.fetch_history("GTCO", date(2026, 10, 5), date(2026, 10, 6))
        self.assertEqual([bar["symbol"] for bar in bars], ["GTCO", "GTCO"])

    def test_upsert_is_idempotent_and_rejects_unverified_input(self):
        bar = {
            "exchange": "NGX",
            "symbol": "GTCO",
            "trade_date": date.today(),
            "currency": "NGN",
            "open": 19,
            "high": 21,
            "low": 18,
            "close": 20,
            "volume": 1000,
            "source": "NGX Market Data API",
            "source_as_of": datetime.now(timezone.utc).replace(tzinfo=None),
            "provider_verified": True,
        }
        with patch.object(ingest_market_data, "SessionLocal", self.Session):
            self.assertEqual(ingest_market_data.upsert_bars([bar]), 1)
            updated = {**bar, "close": 22}
            self.assertEqual(ingest_market_data.upsert_bars([updated]), 1)
        saved = self.db.query(MarketDailyBar).filter_by(symbol="GTCO").one()
        self.assertEqual(float(saved.close), 22)
        self.assertEqual(self.db.query(MarketDailyBar).count(), 1)
        with self.assertRaises(ValueError):
            ingest_market_data._validate_bar({**bar, "provider_verified": False})

    def test_provider_retries_transient_outages(self):
        response = unittest.mock.MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.read.return_value = b'{"data": []}'
        with patch.dict(os.environ, {"NGX_DATA_API_TOKEN": "test-token", "NGX_MARKET_DATA_USE_APPROVED": "true"}):
            with patch.object(ngx_provider.time, "sleep"):
                with patch.object(ngx_provider, "urlopen", side_effect=[URLError("temporary"), URLError("temporary"), response]) as request:
                    result = ngx_provider._fetch_json("pricesEOD", {"a": "EQUITY"})
        self.assertEqual(result, {"data": []})
        self.assertEqual(request.call_count, 3)

    def test_investo_history_is_normalized_for_ngx(self):
        payload = [
            {"date": "2026-10-05", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1200}
        ]
        with patch.object(
            investo_provider,
            "_request_json",
            return_value=(payload, {"generated_at": "2026-10-06T09:00:00Z"}),
        ):
            bars = investo_provider.fetch_history("gtco", date(2026, 1, 1))

        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0]["exchange"], "NGX")
        self.assertEqual(bars[0]["currency"], "NGN")
        self.assertEqual(bars[0]["symbol"], "GTCO")
        self.assertEqual(bars[0]["close"], 103)
        self.assertEqual(bars[0]["source"], investo_provider.SOURCE_NAME)

    def test_summary_hides_unverified_bars_and_returns_typed_freshness_fields(self):
        today = date.today()
        self.db.add_all([
            MarketDailyBar(exchange="NGX", symbol="GOOD", trade_date=today, currency="NGN", close=10,
                           source="official", source_as_of=datetime.combine(today, datetime.min.time()), provider_verified=True),
            MarketDailyBar(exchange="NGX", symbol="FAKE", trade_date=today, currency="NGN", close=99,
                           source="sample", source_as_of=datetime.combine(today, datetime.min.time()), provider_verified=False),
        ])
        self.db.commit()
        with patch.dict(os.environ, {"NGX_DATA_API_TOKEN": "token", "NGX_MARKET_DATA_USE_APPROVED": "true"}):
            summary = market_summary(self.db)
        self.assertEqual([row["symbol"] for row in summary["data"]], ["GOOD"])
        self.assertEqual(summary["data"][0]["currency"], "NGN")
        self.assertFalse(summary["data"][0]["stale"])

    def test_stale_bar_suppresses_even_a_published_signal(self):
        old_date = date.today() - timedelta(days=8)
        bar = MarketDailyBar(
            exchange="NGX", symbol="GTCO", trade_date=old_date, currency="NGN", close=80,
            source="official", source_as_of=datetime.combine(old_date, datetime.min.time()), provider_verified=True,
        )
        signal = PaperSignal(
            exchange="NGX", symbol="GTCO", signal_date=old_date, horizon_sessions=10,
            direction="positive", probability_positive=0.7, model_version="v1",
            validation_status="published", evidence_json='["validated"]', source_as_of=bar.source_as_of,
        )
        result = signal_as_dict(signal, bar)
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "stale_data")
        self.assertIsNone(result["direction"])

    def test_paper_signals_are_scored_but_never_published_automatically(self):
        signal_date = date(2026, 1, 5)
        rows = []
        for offset in range(11):
            trade_date = signal_date + timedelta(days=offset)
            rows.append(MarketDailyBar(
                exchange="NGX", symbol="GTCO", trade_date=trade_date, currency="NGN",
                close=100 + offset, source="official",
                source_as_of=datetime.combine(trade_date, datetime.min.time()), provider_verified=True,
            ))
        self.db.add_all(rows)
        self.db.commit()
        paper = PaperSignal(
            exchange="NGX", symbol="GTCO", signal_date=signal_date, horizon_sessions=10,
            direction="positive", probability_positive=0.7, prior_probability_positive=0.5,
            model_version="swing-v1",
            validation_status="paper", evidence_json='["test paper prediction"]',
            source_as_of=rows[0].source_as_of,
        )
        self.db.add(paper)
        self.db.commit()
        self.assertEqual(paper_track_signals.evaluate_open_signals(self.db), 1)
        report = paper_track_signals.paper_track_report(self.db, 100)
        group = report["groups"]["NGX:GTCO:10:swing-v1"]
        self.assertAlmostEqual(group["mean_net_directional_return_pct"], 9.0, places=3)
        self.assertEqual(group["baseline_samples"], 1)
        self.assertAlmostEqual(group["baseline_matched_brier_score"], 0.09, places=3)
        self.assertAlmostEqual(group["prior_baseline_brier_score"], 0.25, places=3)
        self.assertEqual(report["validation_status"], "paper_only_review_required")
        self.assertIsNone(published_signal(self.db, "GTCO"))

    def test_paper_signal_recording_requires_fresh_verified_close(self):
        today = date.today()
        self.db.add(MarketDailyBar(
            exchange="NGX", symbol="GTCO", trade_date=today, currency="NGN", close=80,
            source="official", source_as_of=datetime.combine(today, datetime.min.time()), provider_verified=True,
        ))
        self.db.commit()
        with patch.dict(os.environ, {"NGX_DATA_API_TOKEN": "token", "NGX_MARKET_DATA_USE_APPROVED": "true"}):
            signal = record_paper_signal.record_paper_signal(
                self.db,
                symbol="gtco",
                direction="positive",
                probability_positive=0.61,
                model_version="swing-v1",
                evidence="Chronological review candidate",
            )
        self.assertEqual(signal.validation_status, "paper")
        self.assertIsNone(published_signal(self.db, "GTCO"))

    def test_paper_prediction_job_uses_verified_history_and_records_prior_baseline(self):
        dates = pd.bdate_range(end=date.today(), periods=360)
        rng = np.random.default_rng(23)
        rows = []
        for symbol, drift in (("GTCO", 0.0004), ("ZENITH", -0.0001)):
            closes = 100 * np.exp(np.cumsum(rng.normal(drift, 0.018, len(dates))))
            rows.extend(
                MarketDailyBar(
                    exchange="NGX",
                    symbol=symbol,
                    trade_date=trade_date.date(),
                    currency="NGN",
                    close=float(close),
                    volume=1000,
                    source="official test fixture",
                    source_as_of=datetime.combine(trade_date.date(), datetime.min.time()),
                    provider_verified=True,
                )
                for trade_date, close in zip(dates, closes)
            )
        self.db.add_all(rows)
        self.db.commit()
        with patch.dict(os.environ, {"NGX_DATA_API_TOKEN": "test-token", "NGX_MARKET_DATA_USE_APPROVED": "true"}):
            result = generate_paper_predictions.generate_paper_predictions(self.db)
            second_run = generate_paper_predictions.generate_paper_predictions(self.db)
        signals = self.db.query(PaperSignal).all()
        self.assertEqual(result["model_version"], MODEL_VERSION)
        self.assertGreater(result["recorded"], 0)
        self.assertEqual(second_run["recorded"], 0)
        self.assertTrue(signals)
        self.assertTrue(all(signal.prior_probability_positive is not None for signal in signals))
        self.assertTrue(all(signal.validation_status == "paper" for signal in signals))
        self.assertIsNone(published_signal(self.db, "GTCO"))

    def test_paper_prediction_job_ignores_unverified_market_rows(self):
        today = date.today()
        self.db.add(MarketDailyBar(
            exchange="NGX",
            symbol="SAMPLE",
            trade_date=today,
            currency="NGN",
            close=100,
            source="sample fixture",
            source_as_of=datetime.combine(today, datetime.min.time()),
            provider_verified=False,
        ))
        self.db.commit()
        with patch.dict(os.environ, {"NGX_DATA_API_TOKEN": "test-token", "NGX_MARKET_DATA_USE_APPROVED": "true"}):
            result = generate_paper_predictions.generate_paper_predictions(self.db)
        self.assertEqual(result["reason"], "no_verified_history")
        self.assertEqual(self.db.query(PaperSignal).count(), 0)

    def test_release_requires_backtest_and_paper_gates_and_current_session_signal(self):
        backtest = {
            "validation_status": "review_required",
            "exchange": "NGX",
            "model_version": MODEL_VERSION,
            "primary_horizon_sessions": 10,
            "round_trip_cost_bps": 100,
            "horizons": [{
                "horizon_sessions": 10,
                "status": "review_required",
                "signal_samples": 45,
                "brier_score": 0.19,
                "prior_baseline_brier_score": 0.24,
                "mean_net_excess_vs_matched_benchmark_pct": 0.35,
            }],
        }
        paper = {
            "validation_status": "paper_only_review_required",
            "round_trip_cost_bps": 100,
            "groups": {f"NGX:GTCO:10:{MODEL_VERSION}": {
                "samples": 40,
                "baseline_samples": 40,
                "directional_hit_rate": 0.6,
                "brier_score": 0.18,
                "baseline_matched_brier_score": 0.18,
                "prior_baseline_brier_score": 0.24,
                "mean_net_directional_return_pct": 1.2,
            }},
        }
        with self.assertRaises(ValueError):
            approve_model.approve_model(
                self.db,
                backtest=backtest,
                paper=paper,
                exchange="NGX",
                symbol="GTCO",
                model_version=MODEL_VERSION,
                reviewer="tester",
                minimum_paper_samples=60,
            )
        approval = approve_model.approve_model(
            self.db,
            backtest=backtest,
            paper=paper,
            exchange="NGX",
            symbol="GTCO",
            model_version=MODEL_VERSION,
            reviewer="research reviewer",
            minimum_paper_samples=30,
        )
        today = date.today()
        bar = MarketDailyBar(
            exchange="NGX", symbol="GTCO", trade_date=today, currency="NGN", close=80,
            source="official", source_as_of=datetime.combine(today, datetime.min.time()), provider_verified=True,
        )
        self.db.add(bar)
        self.db.commit()
        with patch.dict(os.environ, {"NGX_DATA_API_TOKEN": "token", "NGX_MARKET_DATA_USE_APPROVED": "true"}):
            with self.assertRaises(ValueError):
                publish_signal.publish_signal(
                    self.db,
                    symbol="GTCO",
                    direction="positive",
                    probability_positive=0.62,
                    model_version="unapproved-model",
                    evidence="unapproved test",
                )
            signal = publish_signal.publish_signal(
                self.db,
                symbol="GTCO",
                direction="positive",
                probability_positive=0.62,
                model_version=MODEL_VERSION,
                evidence="reviewed evidence",
            )
        eligible = published_signal(self.db, "GTCO", current_bar=bar)
        self.assertIsNotNone(eligible)
        serialized = signal_as_dict(eligible, bar, approval)
        self.assertEqual(serialized["validation"]["reviewer"], "research reviewer")
        self.assertEqual(serialized["validation"]["paper_samples"], 40)
        from src.api.schemas import ForecastResponse, InsightsResponse

        user = User(first_name="Signal", last_name="Tester", username="signal", email="signal@example.com", password_hash="hash")
        self.db.add(user)
        self.db.commit()
        with patch.dict(os.environ, {"NGX_DATA_API_TOKEN": "token", "NGX_MARKET_DATA_USE_APPROVED": "true"}):
            forecast = main.get_forecast("GTCO", "NGX", self.db, user)
            insights = main.get_insights("GTCO", "NGX", self.db, user)
        ForecastResponse.model_validate(forecast)
        InsightsResponse.model_validate(insights)
        self.assertTrue(forecast["signal"]["available"])
        self.assertEqual(insights["data"]["signal"]["validation"]["paper_samples"], 40)
        signal.signal_date = today - timedelta(days=1)
        self.db.commit()
        self.assertIsNone(published_signal(self.db, "GTCO", current_bar=bar))

    def test_missing_validation_never_produces_a_directional_signal(self):
        today = date.today()
        bar = MarketDailyBar(
            exchange="NGX", symbol="GTCO", trade_date=today, currency="NGN", close=80,
            source="official", source_as_of=datetime.combine(today, datetime.min.time()), provider_verified=True,
        )
        result = signal_as_dict(None, bar)
        self.assertFalse(result["available"])
        self.assertIsNone(result["direction"])
        self.assertEqual(result["status"], "not_validated")

    def test_swing_targets_use_5_10_20_sessions_and_leave_future_unlabeled(self):
        close = np.arange(1.0, 61.0)
        frame = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=len(close)), "close": close, "volume": 100})
        result = add_swing_features(frame)
        self.assertAlmostEqual(result.loc[0, "ForwardReturnPct_10"], ((11 / 1) - 1) * 100)
        self.assertEqual(int(result.loc[0, "Target_10"]), 1)
        for horizon in (5, 10, 20):
            self.assertTrue(result[f"Target_{horizon}"].tail(horizon).isna().all())

    def test_feature_export_keeps_latest_twenty_inference_rows(self):
        count = 260
        closes = 100 * np.exp(np.cumsum(np.random.default_rng(4).normal(0.001, 0.01, count)))
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "market.csv")
            output = os.path.join(directory, "features.csv")
            pd.DataFrame({
                "date": pd.date_range("2025-01-01", periods=count),
                "ticker": "GTCO",
                "close": closes,
                "volume": 1000,
            }).to_csv(source, index=False)
            with patch.object(feature_engineering, "INPUT_PATH", source), patch.object(feature_engineering, "OUTPUT_PATH", output):
                result = feature_engineering.add_technical_indicators()
        self.assertEqual(result.tail(20)["Target_20"].isna().sum(), 20)
        self.assertEqual(result.tail(10)["Target_10"].isna().sum(), 10)
        self.assertTrue(result.iloc[-1][list(FEATURE_COLUMNS)].notna().all())

    def test_backtest_is_chronological_and_never_self_publishes(self):
        count = 320
        dates = pd.date_range("2023-01-01", periods=count, freq="B")
        rng = np.random.default_rng(17)
        close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, count)))
        features = add_swing_features(pd.DataFrame({"date": dates, "close": close, "volume": rng.integers(100, 500, count)}))
        benchmark_close = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, count)))
        benchmark = pd.DataFrame({"date": dates, "close": benchmark_close})
        report = evaluate_horizon(features, benchmark, 10, 100)
        self.assertEqual(report["status"], "review_required")
        self.assertIn("prior_baseline_brier_score", report)
        self.assertIn("mean_net_matched_benchmark_return_pct", report)
        self.assertEqual(report["publication_gate"], "manual_review_required; no signal is published by this report")
        self.assertTrue(all(pd.Timestamp(fold["train_end"]) < pd.Timestamp(fold["test_start"]) for fold in report["folds"]))

    def test_invitation_is_one_time_and_expiring_and_portfolio_is_private(self):
        main.JWT_SECRET_KEY = "test-secret-key-with-at-least-thirty-two-characters"
        with patch.dict(os.environ, {"INVITED_USER_EMAILS": "testerallowed@example.com"}):
            allowlisted = main.register_user(self._new_user(None, suffix="allowed"), self.db)
        self.assertEqual(allowlisted["status"], "success")

        invite = "tester-invitation-code-long-enough-123"
        self.db.add(
            InviteToken(
                token_hash=main._hash(invite),
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1),
            )
        )
        self.db.commit()
        with self.assertRaises(HTTPException) as invalid:
            main.register_user(self._new_user("no-invite-code-long-enough"), self.db)
        self.assertEqual(invalid.exception.status_code, 403)

        registered = main.register_user(self._new_user(invite), self.db)
        self.assertEqual(registered["status"], "success")
        with self.assertRaises(HTTPException) as reused:
            main.register_user(self._new_user(invite, suffix="2"), self.db)
        self.assertEqual(reused.exception.status_code, 403)

        user_b = User(first_name="Other", last_name="Tester", username="other", email="other@example.com", password_hash="hash")
        self.db.add(user_b)
        self.db.commit()
        user_a = self.db.query(User).filter(User.username == "tester1").one()
        user_b = self.db.query(User).filter(User.username == "other").one()
        token = main.create_access_token(user_a)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        current_user = main.get_current_user(credentials, self.db)
        with self.assertRaises(HTTPException) as private:
            main.get_user_assets(user_b.id, self.db, current_user)
        self.assertEqual(private.exception.status_code, 403)

    def test_expired_session_is_rejected(self):
        main.JWT_SECRET_KEY = "test-secret-key-with-at-least-thirty-two-characters"
        user = User(first_name="A", last_name="B", username="expired", email="expired@example.com", password_hash="hash")
        self.db.add(user)
        self.db.commit()
        import jwt

        token = jwt.encode({"sub": str(user.id), "user_id": user.id, "iat": datetime.now(timezone.utc) - timedelta(days=2), "exp": datetime.now(timezone.utc) - timedelta(days=1)}, main.JWT_SECRET_KEY, algorithm="HS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with self.assertRaises(HTTPException) as expired:
            main.get_current_user(credentials, self.db)
        self.assertEqual(expired.exception.status_code, 401)

    def test_manual_holding_can_be_added_without_a_market_quote(self):
        user = User(first_name="Manual", last_name="Holder", username="manual", email="manual@example.com", password_hash="hash")
        self.db.add(user)
        self.db.commit()
        request = main.PortfolioCreate(user_id=user.id, ticker="LOCALCO", quantity=10, average_buy_price=25)
        result = main.add_to_portfolio(request, self.db, user)
        self.assertEqual(result["status"], "success")
        with self.assertRaises(HTTPException) as duplicate:
            main.add_to_portfolio(request, self.db, user)
        self.assertEqual(duplicate.exception.status_code, 409)
        watch_result = main.add_to_watchlist(
            main.WatchlistCreate(user_id=user.id, ticker="LOCALCO"), self.db, user
        )
        self.assertEqual(watch_result["status"], "success")

    def test_market_endpoints_validate_against_typed_response_contracts(self):
        from src.api.schemas import ForecastResponse, InsightsResponse, MarketSummaryResponse

        user = User(first_name="Api", last_name="Tester", username="api", email="api@example.com", password_hash="hash")
        self.db.add(user)
        self.db.commit()
        with patch.dict(os.environ, {"NGX_DATA_API_TOKEN": "", "NGX_MARKET_DATA_USE_APPROVED": "false"}):
            summary = main.get_market_summary("NGX", self.db, user)
            forecast = main.get_forecast("GTCO", "NGX", self.db, user)
            insights = main.get_insights("GTCO", "NGX", self.db, user)
        MarketSummaryResponse.model_validate(summary)
        ForecastResponse.model_validate(forecast)
        InsightsResponse.model_validate(insights)

    def test_migration_and_conservative_rollback(self):
        migration_engine = create_engine("sqlite://", future=True)
        try:
            apply(migration_engine)
            inspector = __import__("sqlalchemy").inspect(migration_engine)
            self.assertIn("market_daily_bars", inspector.get_table_names())
            self.assertIn("tester_invites", inspector.get_table_names())
            self.assertIn("model_release_approvals", inspector.get_table_names())
            with self.assertRaises(ValueError):
                rollback(migration_engine)
            rollback(migration_engine, confirm_drop_data=True)
            inspector = __import__("sqlalchemy").inspect(migration_engine)
            self.assertNotIn("market_daily_bars", inspector.get_table_names())
            self.assertNotIn("model_release_approvals", inspector.get_table_names())
            self.assertIn("users", inspector.get_table_names())
            self.assertIn("portfolios", inspector.get_table_names())
        finally:
            migration_engine.dispose()

    def _new_user(self, invite_code: str | None, suffix: str = ""):
        return main.UserCreate(
            first_name="Tester",
            last_name="One",
            username=f"tester{suffix or '1'}",
            email=f"tester{suffix or '1'}@example.com",
            password="strong-pass-123",
            invite_code=invite_code,
        )


if __name__ == "__main__":
    unittest.main()
