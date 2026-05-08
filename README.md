# p4pa-superset

This application represent the presentation layer of the analytics tool related to **Piattaforma Unitaria** product (PU).

It represents a customization of [Apache Superset](https://github.com/apache/superset).

See [PU Microservice Architecture](https://raw.githubusercontent.com/pagopa/p4pa-doc/refs/heads/main/reference/technical-docs/Architettura_microservizi.pdf) for more details.

See [p4pa-doc](https://github.com/pagopa/p4pa-doc) for further documentation.

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

## 📑 Superset manifests

The `manifests/` folder contains the exported Superset asset configurations, providing a version-controlled history of changes in the Superset environment 
The `scripts/` folder includes the utility tools used to perform these exports and imports between environments.