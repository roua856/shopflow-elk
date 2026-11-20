# ShopFlow: technology choices

| Technology | Role in ShopFlow | Why we chose it | Alternative considered |
|---|---|---|---|
| Elasticsearch 8.15.3 | Stores and searches logs (shopflow-logs-*, shopflow-failures-*) | Full-text search and fast aggregations (errors per hour, top IPs). ILM deletes data after 30 days. Required by the brief. | PostgreSQL: slow for text search and time aggregations on logs. |
| Logstash 8.15.3 | Parses CSV, JSON and TXT files (csv, json, grok, date, geoip filters) and routes parse failures | One pipeline per file format. Failed lines go to a separate index instead of being lost. Same stack as Elasticsearch. | Filebeat with ingest pipelines: less flexible for 3 formats and failure routing. |
| Kibana 8.15.3 | Observability dashboards (module L) | Built for Elasticsearch, no code needed, same version as Elasticsearch. | Grafana: one more service to deploy. |
| MongoDB 7 | Users, files, searches, alert rules, alerts | Flexible documents (alert rules have different conditions). Unique indexes on keys. NoSQL is required by the brief. | PostgreSQL: rigid schema for varied alert rules. |
| Redis 7 | Sessions, cache, rate limit, ingest status, alert cooldown | Keys with TTL, atomic INCR for rate limits, SET NX EX for alert cooldown. Shared by all web workers. | In-process Python dictionary: not shared between gunicorn workers, lost on restart. |
| Flask + gunicorn (Python 3.11) | Web application: upload, search, alert rules | Lightweight. Official clients for Elasticsearch, MongoDB and Redis. Same language as the Faker generator. | Django: heavier than needed. |
| Docker Compose | Deployment of the 6 services with one command | Reproducible. Healthchecks and depends_on give the start order. Fits one machine. | Kubernetes: too heavy for a single-host project. |
| Faker (Python) | Generates test logs: funnel traffic, 14:00 payment incident, fraud patterns | Realistic, seeded data (same seed, same logs). | Hand-written sample files: too few lines to show an incident. |
| Git, GitHub, Jira | Versioned code and tracked work | One commit per ticket (key in the message), the professor can follow the history. | None. |

## Decisions and limits

- All Elastic products use the same version (8.15.3) to avoid compatibility problems.
- One Elasticsearch node, 1 shard, 0 replicas: enough for the project, no high availability.
- Elasticsearch security is disabled (xpack.security.enabled=false) for the local environment. In production we would enable TLS and role-based access.
- The disk watermark check is disabled because the development laptop has limited disk space.
