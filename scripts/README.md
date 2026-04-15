## 📜 Scripts

Two utility scripts are provided in `scripts/` to manage Superset assets migration:

*  **run_export.sh**: Executes the **export/export.py** script that exports all Superset assets into the `manifests/superset_full_export/` folder.
* **run_import.sh**: Executes the **import/import.py** script that patches the database credentials in the exported YAML files and imports the assets into the target Superset environment.

### `run_export.sh` — environment variables

| ENV               | DESCRIPTION                     | DEFAULT |
|-------------------|---------------------------------|---------|
| SUPERSET_URL      | Superset instance base URL      |         |
| SUPERSET_USER     | Superset admin username         | `admin` |
| SUPERSET_PASSWORD | Superset admin password         |         |

Variables can be passed as positional arguments (in the order above) or pre-exported in the shell before running the script.

### `run_import.sh` — environment variables

| ENV                   | DESCRIPTION                                               | DEFAULT     |
|-----------------------|-----------------------------------------------------------|-------------|
| SUPERSET_URL          | Superset instance base URL                                |             |
| SUPERSET_USER         | Superset admin username                                   | `admin`     |
| SUPERSET_PASSWORD     | Superset admin password                                   |             |
| ANALYTICS_DB_HOST     | Hostname of the target Analytics PostgreSQL database      |             |
| ANALYTICS_DB_PORT     | Port of the target Analytics PostgreSQL database          | `5432`      |
| ANALYTICS_DB_NAME     | Database name of the target Analytics PostgreSQL database | `analytics` |
| ANALYTICS_DB_USER     | Username of the target Analytics PostgreSQL database      | `analytics` |
| ANALYTICS_DB_PASSWORD | Password of the target Analytics PostgreSQL database      |             |

Variables can be passed as positional arguments (in the order above) or pre-exported in the shell before running the script.

> [!TIP]
> The **SUPERSET_PASSWORD** can be retrieved from the k8s secret **p4pa-superset-env** as **superset-admin-psw**.

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

