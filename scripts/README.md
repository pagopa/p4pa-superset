## 📜 Scripts

Four utility scripts are provided in `scripts/` to manage Superset assets migration:

* **run_export.sh**: Executes the **export/export.py** script that exports all Superset assets into the `manifests/<TAG>/` folder. The script requires a tag as its only positional argument.
* **run_export_core.sh**: Executes the **run_export.sh** script with the tag parameter set to **core**.
* **run_import.sh**: Runs the import pipeline for a given tag under `manifests/<TAG>/`, requiring the tag as its only positional argument.
* **run_import_core.sh**: Executes the **run_import.sh** script with the tag parameter set to **core**.

The import logic itself is split across two scripts, run in sequence by `run_import.sh`: **import/manifest_builder.py** builds the manifests (patching database credentials and resolving/filtering assets into a build folder), while **import/import.py** only performs the actual import of those already-built manifests into the target Superset environment.

### `run_export.sh` — usage

```bash
./run_export.sh <TAG>
```

`TAG` is the only positional argument. It determines which assets to export and the folder to save them in: `manifests/<TAG>/`

All other configuration must be provided as environment variables:

| ENV               | DESCRIPTION                     | DEFAULT |
|-------------------|---------------------------------|---------|
| SUPERSET_URL      | Superset instance base URL      |         |
| SUPERSET_USER     | Superset admin username         | `admin` |
| SUPERSET_PASSWORD | Superset admin password         |         |


**Example:**

```bash
export SUPERSET_URL="https://analytics.dev.p4pa.pagopa.it"
export SUPERSET_USER="admin"
export SUPERSET_PASSWORD="secret"

./run_export.sh core
```

> [!TIP]
> The **SUPERSET_PASSWORD** can be retrieved from the k8s secret **p4pa-superset-env** as **superset-admin-psw**.

> [!NOTE]
> Positional argument override for credentials has been removed. Environment variables must be set before running the script — passing credentials as positional arguments is no longer supported.

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
export SUPERSET_URL="https://analytics.dev.p4pa.pagopa.it"
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