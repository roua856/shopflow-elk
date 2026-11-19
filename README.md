# ShopFlow

Log monitoring and analysis platform for an e-commerce shop (ELK Stack, MongoDB, Redis, web interface).
IT Business School, mini-project ELK, NoSQL and web interface. Scenario A: E-commerce.
Advanced modules: G (Alerting) and L (Observability).

## Structure

| Folder | Content |
|---|---|
| `es/` | Elasticsearch index template and ILM policy |
| `logstash/` | 3 pipelines (CSV, JSON, TXT) |
| `mongo/` | MongoDB collections, indexes and examples |
| `redis/` | Redis use cases |
| `sample-data/` | Sample log files |
| `diagrams/` | Sequence diagrams |
| `wireframes/` | UI wireframes, design system, user journeys |
| `webapp/` | Web application (Flask) |
| `scripts/` | Utility scripts (Faker data generator) |
| `docs/` | Analysis, Conception and Architecture documents |

## Run (development)

    docker compose up -d

## Author

Roua Khribiche
