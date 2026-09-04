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
- [ ] Long-running transaction without row-lock incident
- [ ] Disk pressure
- [ ] Table bloat / VACUUM
- [ ] Failed deployment migration
- [ ] Roles / privileges
- [ ] Backup and restore
- [ ] Replica lag
- [ ] Failover

## Phase 2.5 — Scenario authoring engine
- [x] Scenario-agnostic API routing
- [x] Declarative evaluation engine
- [x] Catalog validation at application startup
- [x] Declarative SQL/data setup
- [x] Generated service roles and learner grant/ownership setup
- [x] Reusable fault-injection primitives
- [x] Generic runtime connection/role teardown
- [ ] Scenario definitions loaded from YAML/JSON files
- [ ] Scenario authoring validation CLI
- [ ] Scenario versioning
- [ ] Scenario reset/replay
- [ ] Named reusable dataset templates
- [ ] Named workload templates

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

## Phase 3 — Learning engine
- [ ] User accounts and persistent progress
- [ ] Skill graph
- [ ] Prerequisites
- [ ] Adaptive difficulty
- [ ] Scenario recommendations
- [ ] Spaced repetition
- [ ] Personalized weak-area drills
- [ ] Progress history
- [ ] Evidence / portfolio report per completed lab

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
- [ ] Automatic expiry and teardown
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
