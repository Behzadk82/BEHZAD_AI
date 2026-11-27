# BEHZAD_AI PROJECT MASTER STATE

Last verified update: 2026-11-27

## 1. Fixed Rules
- Project root must remain unchanged.
- Database/storage paths must not change.
- Do not create a parallel database.
- Do not delete existing data or project files.
- No ZIP delivery; provide code directly in chat.
- Work sequentially, one related module/task at a time.
- Inspect existing code before modifying.
- Run Syntax and relevant tests after modifications.
- Untested work must not be marked PASS.
- Do not repeat verified tests without a reason.
- Update project records after verified milestones.

## 2. Project Root
/storage/emulated/0/BEHZAD_AI

## 3. Existing Database
- Existing database: data/behzad_ai.db
- This is the existing database; do not create another.
- Database path/config was previously inspected and verified.
- Existing schema includes price_history, indicators, symbols and fetch_log.
- Actual symbols table has additional fields compared with the schema declaration.
- Preserve existing schema and data.

## 4. Project Goal
Build BEHZAD_AI with market data, historical data, incremental updates,
validation, technical indicators, analysis, scanners, backtesting,
risk management, paper trading, safe automated trading, API and website.

## 5. Verified Status

### Database
- database.py replacement was previously applied.
- User reported Syntax and Import checks passed.
- Full CRUD/integration verification: NOT TESTED.

### Historical Data
- history.py work and tests: 10 tests PASS (previously user-confirmed).
- Live market/API integration: NOT TESTED in this checkpoint.

### Incremental Data
- incremental.py safe update implementation provided/applied in current work.
- Normalization tests: PASS (user-confirmed).
- Live API/real database integration: NOT TESTED.

### Batch Indicators
File: src/data/batch_indicators.py
- Updated missing-history-date detection.
- Recomputes full symbol history when missing dates are detected.
- Upserts indicator rows.
- Saves warm-up dates even when indicator values are NULL.
- Syntax check: PASS (user-confirmed).
- Offline functional test: PASS.
- Test coverage confirmed:
  - Pending detection
  - Indicator computation
  - 60 synthetic history dates saved
  - Upsert duplicate protection
- Test used in-memory SQLite and synthetic data.
- Production database execution: NOT TESTED.

## 6. Phases

### Phase 1 - Data Infrastructure
- [x] History module tests (10 tests PASS)
- [x] Incremental normalization tests PASS
- [x] Batch indicator syntax PASS
- [x] Batch indicator offline functional tests PASS
- [ ] Database CRUD/integration tests
- [ ] Live API integration
- [ ] Existing DB history integration
- [ ] Incremental real-data integration
- [ ] Data-quality verification
- [ ] Retry/error handling verification
- [ ] End-to-end pipeline verification

### Phase 2 - Market Data
- [ ] Symbol metadata
- [ ] Market prices/volume
- [ ] Automated refresh
- [ ] Scheduling
- [ ] Connectivity recovery
- [ ] Error logging
- [ ] Data quality

### Phase 3 - Technical Indicators
- [ ] SMA/EMA/WMA/VWAP
- [ ] RSI/MACD
- [ ] Stochastic/Stochastic RSI
- [ ] CCI/ADX/ATR
- [ ] Bollinger/Keltner
- [ ] Ichimoku/Parabolic SAR
- [ ] OBV/MFI/CMF
- [ ] ROC/Momentum/Williams %R
- [ ] Fibonacci/Pivots/Supertrend
- [ ] Additional indicators

### Phase 4 - Analysis Engine
- [ ] Trend
- [ ] Momentum
- [ ] Volatility
- [ ] Volume
- [ ] Support/resistance
- [ ] Candlestick/chart patterns
- [ ] Multi-timeframe
- [ ] Market regime
- [ ] Signal scoring

### Phase 5 - Scanner
- [ ] Market scanner
- [ ] Bullish/bearish
- [ ] Breakout/volume/trend
- [ ] Oversold/overbought
- [ ] Custom filters
- [ ] Ranking

### Phase 6 - Backtesting
- [ ] Engine
- [ ] Fees/slippage
- [ ] Position sizing
- [ ] Stop loss/take profit
- [ ] Drawdown/win rate/profit factor
- [ ] Sharpe/equity curve
- [ ] Out-of-sample testing
- [ ] Look-ahead bias prevention

### Phase 7 - Risk Management
- [ ] Risk per trade
- [ ] Exposure/daily loss/drawdown limits
- [ ] Position sizing
- [ ] Risk/reward validation
- [ ] Stop-loss controls
- [ ] Emergency stop/trading lock
- [ ] Audit log

### Phase 8 - Trading
- [ ] Paper trading
- [ ] Order simulation
- [ ] Trade journal
- [ ] Execution monitoring
- [ ] Broker research
- [ ] Credential security
- [ ] Order validation/duplicate protection
- [ ] Kill switch
- [ ] Live trading disabled by default

### Phase 9 - API
- [ ] Authentication
- [ ] Data/indicator/analysis/scanner endpoints
- [ ] Backtest/trading endpoints
- [ ] Error handling/rate limits

### Phase 10 - Website
- [ ] Dark futuristic theme
- [ ] Gold/blue design
- [ ] User photo
- [ ] Book-style navigation
- [ ] Dashboard/charts
- [ ] Indicators/analysis/scanner
- [ ] Portfolio/backtest/settings
- [ ] Responsive mobile layout

### Phase 11 - Quality Assurance
- [ ] Unit/integration/API tests
- [ ] Data integrity
- [ ] Backtest verification
- [ ] Security review
- [ ] Performance
- [ ] Recovery
- [ ] Release checklist

## 7. Current Next Action
Inspect src/data/batch_downloader.py and its interaction with history,
incremental updates, database storage, checkpoints and error handling.
Do not run it against the live database yet.
After inspection, identify the next isolated improvement and test it safely.

## 8. Safety
No software is guaranteed error-free.
Automated/live trading must not be enabled until data integrity,
backtesting, paper trading, risk controls and execution safeguards
have been extensively validated.

## Batch Downloader - Verified Progress (2026-11-27)

File: src/data/batch_downloader.py

Completed and user-tested:
- API history record validation before completion.
- Invalid-only responses are marked failed.
- Completed/failed checkpoint state consistency.
- Duplicate failure replacement.
- Batch number preservation.

Offline network tests: 7 PASS.
History validation tests: 6 PASS.
Checkpoint state tests: 4 PASS.

Not yet verified:
- Full process_batch integration with isolated database.
- Recovery after partial database/raw-file save failures.
- Live TSETMC API operation.
- Production database integration.

Existing database and checkpoint paths remain unchanged.
Do not run live downloader yet.

FAILURE RECOVERY TEST: ALL PASSED

## LATEST VERIFIED MILESTONE
- Batch downloader failure recovery: PASS.
- Simulated raw JSON save failure after DB insert.
- DB record remained intact.
- Failed symbol persisted in isolated checkpoint.
- Retry completed successfully.
- Duplicate DB insertion prevented.
- Raw JSON and completed checkpoint persisted.
- Live API: NOT TESTED.
- Production DB integration: NOT TESTED.
- Existing production checkpoint and database were not modified.

CHECKPOINT RECOVERY TEST: ALL PASSED

## CHECKPOINT FAILURE RECOVERY
- Simulated checkpoint write failure after DB and raw JSON save.
- Database record preserved: PASS.
- Raw JSON preserved: PASS.
- Retry completed successfully: PASS.
- Duplicate DB insertion prevented: PASS.
- Final checkpoint completion persisted: PASS.
- Test used isolated temporary paths.

## NEW VERIFIED MILESTONE — PROCESS_BATCH INTEGRATION

- Permanent isolated test file: tools/test_batch_process.py
- User-confirmed test execution result: OK
- test_success_and_duplicate_retry: PASS
- test_sensitive_http_stop: PASS
- test_invalid_history_is_not_completed: PASS
- Raw JSON and checkpoint used isolated temporary paths.
- Production database: NOT MODIFIED.
- Production checkpoint: NOT MODIFIED.
- Live API: NOT TESTED.
- Production database integration: NOT TESTED.

Previous recovery tests remain verified and were not repeated.


## 2026-11-27 — Batch Data Integrity (VERIFIED)

- Updated `src/data/batch_downloader.py`.
- Added shared `_normalize_batch_record`.
- Unified record validation between `save_to_db` and `_count_valid_history_records`.
- Strict Gregorian date validation (YYYYMMDD).
- Rejected negative price/volume/value/trade fields.
- Allowed negative `priceChange`.
- Required at least one positive market price; applied price fallback.
- Rejected non-finite numeric values.
- Preserved `ON CONFLICT(ins_code, date) DO NOTHING`.
- Created source backup before modification.
- Syntax check: PASS.
- New test suite `tools/test_batch_data_integrity.py`: 15/15 PASS.
- Production DB was not used.
- Production checkpoint was not modified.


## 2026-11-27 — SQLite Save Integration (VERIFIED)

- New test: `tools/test_batch_save_to_db.py`
- SQLite integration tests: 5/5 PASS.
- Actual SQL insert tested against isolated temporary SQLite DB.
- Invalid records rejected.
- Actual inserted row count verified.
- Duplicate date insert prevented.
- Original record values preserved on duplicate.
- Price fallback verified in persisted rows.
- Mixed valid/invalid records verified.
- Production DB was NOT used.
- Production checkpoint was NOT changed.

## 2026-11-27 — DATABASE CRUD INTEGRATION VERIFIED

File:
- tools/test_database_crud.py

Result:
- 8 tests PASS
- Schema and table verification PASS
- Primary key and index verification PASS
- Insert and Read PASS
- Upsert/Update and duplicate protection PASS
- Missing symbol handling PASS
- List ordering and limit PASS
- Empty ins_code handling PASS
- Fetch log and stats PASS
- Delete in temporary DB PASS

All tests used an isolated temporary SQLite database.
Production DB and checkpoint were not accessed or modified.

NEXT:
Phase 1 — Data Quality Verification.
Design isolated data-quality tests using temporary data.
Do not repeat completed tests.
Do not run against production DB or live API.

**2026-11-27 — INCREMENTAL NORMALIZATION VERIFIED**

File:
- tools/test_incremental_normalization.py

Result:
- 13 tests PASS
- Date validation verified
- Numeric validation verified
- Negative values verified
- Price fallback verified
- NaN/Infinity handling verified
- No API or production DB access

NEXT:
Phase 1 — Data Quality Verification.
Review cross-module validation contracts.

2026-11-27 — CROSS-MODULE DATA QUALITY VERIFIED
File:
• tools/test_cross_module_quality.py
Result:
• 4/4 tests PASS
• Cross-module behavior verified across history.py, incremental.py, and batch_downloader.py
• Production DB and checkpoint untouched
