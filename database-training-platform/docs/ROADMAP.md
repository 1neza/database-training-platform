# Product Roadmap

## Phase 1 — PostgreSQL DBA MVP
- [x] Scenario catalog
- [x] Timed sessions
- [x] Dedicated database + learner login per session
- [x] Synthetic datasets
- [x] Slow-query / indexing scenario
- [x] Deterministic evaluator
- [x] Declarative grading checks
- [x] Hints
- [x] 100-point scorecard
- [x] Selectable learner scenario UI
- [x] Lab teardown and return-to-catalog flow
- [x] GitHub Actions with real PostgreSQL integration tests

## Phase 2 — Real DBA incidents
- [x] Lock contention / stale transaction
- [x] Connection-pool exhaustion
- [x] Deadlock
- [x] Long-running transaction without row-lock incident
- [ ] Disk pressure
- [x] Table bloat / VACUUM
- [x] Failed deployment migration
- [x] Roles / privileges
- [x] Backup and restore
- [ ] Replica lag
- [ ] Failover

Implemented labs:
1. Slow Checkout Query — difficulty 2/5
2. Blocked Payment Transaction — difficulty 3/5
3. Connection Pool Exhaustion — difficulty 3/5
4. Deadlocking Transfer Procedures — difficulty 4/5
5. Stale Reporting Transaction — difficulty 2/5
6. Excessive Analytics Privileges — difficulty 3/5
7. Failed Deployment Migration — difficulty 3/5
8. Table Bloat and VACUUM — difficulty 3/5
9. Logical Backup Restore — difficulty 3/5

## Phase 2.5 — Scenario authoring engine
- [x] Scenario-agnostic API routing
- [x] Declarative evaluation engine
- [x] Catalog validation at application startup
- [x] Declarative SQL/data setup
- [x] Generated service roles and learner grant/ownership setup
- [x] Reusable fault-injection primitives
- [x] Generic runtime connection/role teardown
- [x] Scenario definitions loaded from JSON files
- [x] Scenario authoring validation CLI
- [x] Scenario semantic versioning
- [x] Immutable scenario snapshot per learner attempt
- [x] Attempt finish/replay lifecycle
- [x] Named reusable dataset templates
- [x] Named workload templates
- [x] Validated scenario skill/prerequisite metadata
- [x] Validated scenario difficulty metadata (1–5)

Current scenario authoring flow:
1. Add or edit `backend/scenarios/<slug>.json`.
2. Declare skills, prerequisite skills and difficulty.
3. Reference versioned assets from `backend/datasets/` and `backend/workloads/` when appropriate.
4. Bump the scenario semantic version when its behavior/learning semantics change.
5. Run `python -m app.validate_scenarios`.
6. CI repeats validation, compiles the backend and runs the real PostgreSQL integration suite.

Current reusable fault primitives:
- persistent idle transaction / row lock
- runaway connection pool
- concurrent deadlock reproduction

Current reusable grading primitives:
- index prefix
- query plan uses index
- row count
- session count
- scalar SQL equality
- query succeeds under lock timeout
- concurrent SQL completes without deadlock

Current reusable assets:
- dataset: `ecommerce-orders-medium@1.0.0`
- workload: `checkout-customer-history@1.0.0`

## Phase 3 — Learning engine
- [x] Lightweight durable learner profile / browser identity
- [ ] Authenticated user accounts and account recovery
- [x] Persistent attempt history UI/API
- [x] Progress summary per scenario
- [x] Skill mastery summary
- [x] Skill graph
- [x] Prerequisites and locked/ready/completed states
- [x] API-level prerequisite enforcement for identified learners
- [x] Deterministic scenario recommendations
- [x] Weak-skill detection and retry prioritization
- [x] Adaptive difficulty targeting
- [x] Spaced repetition / review-due scheduling
- [x] Deterministic portfolio/evidence generation engine
- [ ] Learner-facing portfolio API/UI/export
- [ ] Dedicated weak-area drill scenarios / generated drills

Current recommendation priorities are deterministic and explainable:
1. unresolved failed attempts
2. weak-skill practice
3. overdue spaced-repetition reviews
4. scenarios close to the learner's target difficulty
5. untouched ready scenarios

Current adaptive difficulty scale:
- 1/5 — future onboarding/fundamentals
- 2/5 — foundational production incidents
- 3/5 — intermediate operational incidents
- 4/5 — advanced concurrency/reliability incidents
- 5/5 — future failover/DR/high-complexity incidents

## Phase 4 — AI layer
- [ ] AI engineering manager
- [ ] AI developer/customer messages
- [ ] Socratic hints
- [ ] Incident postmortem feedback
- [ ] Natural-language scenario authoring
- [ ] Generated synthetic schema/data configuration

AI should assist with teaching, role-play and explanation. Deterministic infrastructure checks remain the primary technical grading mechanism.

## Phase 5 — Data engineering
- [ ] Kafka
- [ ] Debezium CDC
- [ ] Airflow
- [ ] Data quality checks
- [ ] Consumer lag
- [ ] Schema evolution
- [ ] Broken pipelines
- [ ] Warehouse / analytics incidents

## Phase 6 — Production isolation
- [ ] Container per lab
- [ ] Kubernetes namespace or equivalent isolation per session
- [ ] CPU/memory quotas
- [ ] Network policies
- [ ] Automatic expiry and teardown worker
- [ ] Secret vault
- [ ] Audit logs
- [ ] Lab snapshot / fast reset

## Phase 7 — B2B
- [ ] Company-defined scenarios
- [ ] Sanitized internal datasets
- [ ] Team dashboards
- [ ] Onboarding tracks
- [ ] Interview / assessment mode
- [ ] Candidate reports
- [ ] SSO
- [ ] LMS integration
