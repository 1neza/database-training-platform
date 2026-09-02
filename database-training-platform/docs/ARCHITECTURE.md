# Architecture

## Control plane

The FastAPI application stores session metadata in `platform-db`.

## Lab plane

`lab-db` is deliberately separate. Every training session receives:
- a unique database
- a unique PostgreSQL role
- a generated password

The API has an administrative connection used only for provisioning, deterministic evaluation and teardown.

## Production evolution

For public deployment, replace the shared `lab-db` with disposable isolated lab environments:

```text
API
 |
Lab Orchestrator
 |
 +-- session namespace/container
 |      PostgreSQL
 |      workload-generator
 |      metrics-agent
 |
 +-- session namespace/container
        PostgreSQL
        fault-injector
```

This creates strong tenant isolation and allows destructive DBA scenarios safely.
