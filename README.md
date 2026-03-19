# p4pa-superset

This application represent the presentation layer of the analytics tool related to **Piattaforma Unitaria** product (PU).

It represents a customization of [Apache Superset](https://github.com/apache/superset).

See [PU Microservice Architecture](https://pagopa.atlassian.net/wiki/spaces/SPAC/pages/1405845916/Architettura+microservizi) for more details.

## 🧱 Role

* To implement and expose analytical dashboards on data handled by PU.

## 🔗 Dependencies

### 🗄️ Resources
* Redis
* Postgresql

### 🧩 Microservices
* [p4pa-auth](https://github.com/pagopa/p4pa-auth): To exchange PU token with superset session token


## 🔧 Configuration

See [Apache Superset documentation](https://github.com/apache/superset?tab=readme-ov-file#installation-and-configuration) for each configurable variable.

### 📌 Relevant configurations

#### 🔁 Integrations

##### 🗄️ Resources
| ENV                 | DESCRIPTION                                            | DEFAULT |
|---------------------|--------------------------------------------------------|---------|
| REDIS_HOST          | Redis server host                                      |         |
| REDIS_PORT          | Redis server port                                      |         |
| REDIS_PROTO         | The protocol used to connect to Redis                  |         |
| REDIS_SSL_CERT_REQS | The SSL cert to use if required (use `none` otherwise) |         |
| REDIS_USER          | Redis user                                             |         |
| REDIS_PASSWORD      | Redis password                                         |         |
| DB_HOST             | Postgresql server host                                 |         |
| DB_PORT             | Postgresql server port                                 |         |
| DB_NAME             | Postgresql database name                               |         |
| DB_USER             | Postgresql user                                        |         |
| DB_PASS             | Postgresql password                                    |         |


##### 🧩 Microservices
| ENV                                                  | DESCRIPTION                                                      | DEFAULT |
|------------------------------------------------------|------------------------------------------------------------------|---------|
| AUTH_BASE_URL                                        | Auth microservice URL                                            |         |
| DEBT_POSITIONS_BASE_URL                              | DebtPositions microservice URL                                   |         |
| ANALYTICS_DB_NAME                                    | Name of Analytics DB                                             |         |
| ANALYTICS_DB_SCHEMA_NAME                             | Name of Analytics DB datamart schema                             |         |

## 🛠️ Getting Started

### 📝 Prerequisites

Ensure the following tools are installed on your machine:

1. **Docker** (to build and run on an isolated environment, optional)

### 🐳 Build & run through Docker
```sh
docker build -t <APP_NAME> .
docker run --env-file <ENV_FILE> <APP_NAME>
```

## 📜 Scripts

Two utility scripts are provided in `scripts/` to manage Superset assets migration:

* **export/export.py** / **run_export.sh**: Exports all Superset assets into the `manifests/superset_full_export/` folder.
* **import/import.py** / **run_import.sh**: Patches the database credentials in the exported YAML files and imports the assets into the target Superset environment.

### `run_export.sh` — environment variables

| ENV               | DESCRIPTION                     | DEFAULT |
|-------------------|---------------------------------|---------|
| SUPERSET_URL      | Superset instance base URL      |         |
| SUPERSET_USER     | Superset admin username         |         |
| SUPERSET_PASSWORD | Superset admin password         |         |

Variables can be passed as positional arguments (in the order above) or pre-exported in the shell before running the script.

### `run_import.sh` — environment variables

| ENV                   | DESCRIPTION                                               | DEFAULT |
|-----------------------|-----------------------------------------------------------|---------|
| SUPERSET_URL          | Superset instance base URL                                |         |
| SUPERSET_USER         | Superset admin username                                   |         |
| SUPERSET_PASSWORD     | Superset admin password                                   |         |
| ANALYTICS_DB_PASSWORD | Password of the target Analytics PostgreSQL database      |         |
| ANALYTICS_DB_USER     | Username of the target Analytics PostgreSQL database      |         |
| ANALYTICS_DB_HOST     | Hostname of the target Analytics PostgreSQL database      |         |
| ANALYTICS_DB_PORT     | Port of the target Analytics PostgreSQL database          |         |
| ANALYTICS_DB_NAME     | Database name of the target Analytics PostgreSQL database |         |

Variables can be passed as positional arguments (in the order above) or pre-exported in the shell before running the script.

### PIPENV INSTALLATION

Install pipenv:
pip install pipenv

Create and enter the virtual environment:
pipenv shell

Install dependencies:
pipenv sync

Update dependencies:
pipenv run pip freeze > requirements.txt
pipenv install -r requirements.txt

