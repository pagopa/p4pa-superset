## 📜 Scripts

Two utility scripts are provided in `scripts/` to manage Superset assets migration:

* **run_export.sh**: Executes the **export/export.py** script that exports all Superset assets into the `manifests/superset_full_export/` folder.
* **run_import.sh**: Executes the **import/import.py** script that patches the database credentials in the exported YAML files and imports the assets into the target Superset environment. Assets are organized by tag under `manifests/<tag>/` and the script requires a tag as its only positional argument.

### `run_export.sh` — environment variables

| ENV               | DESCRIPTION                     | DEFAULT |
|-------------------|---------------------------------|---------|
| SUPERSET_URL      | Superset instance base URL      |         |
| SUPERSET_USER     | Superset admin username         | `admin` |
| SUPERSET_PASSWORD | Superset admin password         |         |

Variables can be passed as positional arguments (in the order above) or pre-exported in the shell before running the script.

### `run_import.sh` — usage

```bash
./run_import.sh <TAG>
```

`TAG` is the only positional argument and determines which folder under `manifests/` will be imported:

manifests/
└── <TAG>/          ← folder that will be imported
├── metadata.yaml
├── databases/
├── datasets/
├── charts/
└── dashboards/

All other configuration must be provided as environment variables:

| ENV                   | DESCRIPTION                                               | DEFAULT     |
|-----------------------|-----------------------------------------------------------|-------------|
| SUPERSET_URL          | Superset instance base URL                                |             |
| SUPERSET_USER         | Superset admin username                                   | `admin`     |
| SUPERSET_PASSWORD     | Superset admin password                                   |             |
| ANALYTICS_DB_PASSWORD | Password of the target Analytics PostgreSQL database      |             |
| ANALYTICS_DB_USER     | Username of the target Analytics PostgreSQL database      | `analytics` |
| ANALYTICS_DB_HOST     | Hostname of the target Analytics PostgreSQL database      |             |
| ANALYTICS_DB_PORT     | Port of the target Analytics PostgreSQL database          | `5432`      |
| ANALYTICS_DB_NAME     | Database name of the target Analytics PostgreSQL database | `analytics` |

**Example:**

```bash
export SUPERSET_URL="https://analytics.internal.dev.p4pa.pagopa.it"
export SUPERSET_USER="admin"
export SUPERSET_PASSWORD="secret"
export ANALYTICS_DB_USER="analytics"
export ANALYTICS_DB_PASSWORD="dbsecret"
export ANALYTICS_DB_HOST="p4pa-d-itn-payhub-flexible-postgresql.postgres.database.azure.com"
export ANALYTICS_DB_PORT="5432"
export ANALYTICS_DB_NAME="analytics"

./run_import.sh core
```

> [!TIP]
> The **SUPERSET_PASSWORD** can be retrieved from the k8s secret **p4pa-superset-env** as **superset-admin-psw**.

> [!NOTE]
> Positional argument override for credentials has been removed. Environment variables must be set before running the script — passing credentials as positional arguments is no longer supported.

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