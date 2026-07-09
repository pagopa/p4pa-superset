import os
import sys
import shutil
import logging
import zipfile
import tempfile
import requests
import yaml
from sqlalchemy.engine.url import make_url

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        logger.error(f"Required environment variable '{name}' is not set.")
        sys.exit(1)
    return value


class SupersetClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.is_authenticated = False

    def authenticate(self):
        try:
            r = self.session.post(
                f"{self.base_url}/api/v1/security/login",
                json={"username": self.username, "password": self.password,
                      "provider": "db", "refresh": True},
            )
            r.raise_for_status()
            self.session.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})

            r_csrf = self.session.get(f"{self.base_url}/api/v1/security/csrf_token/")
            r_csrf.raise_for_status()
            self.session.headers.update({"X-CSRFToken": r_csrf.json()["result"]})

            self.is_authenticated = True
            logger.info(f"Authenticated on: {self.base_url}")
        except Exception as e:
            logger.error(f"Authentication failed on {self.base_url}: {e}")
            sys.exit(1)

    def _import_assets(self, zip_file, endpoint: str, zip_filename: str, label: str):
        if not self.is_authenticated:
            logger.error("Client not authenticated. Call authenticate() first.")
            sys.exit(1)

        size_kb = os.fstat(zip_file.fileno()).st_size / 1024
        logger.info(f"Sending ZIP to {label} import API ({size_kb:.1f} KB)...")
        files = {"formData": (zip_filename, zip_file, "application/zip")}

        try:
            r = self.session.post(
                f"{self.base_url}{endpoint}",
                files=files,
                data={"overwrite": "true"},
            )
            r.raise_for_status()
            logger.info(f"SUCCESS. {label} import completed.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during {label} import: {e} — API response: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error during {label} import: {e}")
            sys.exit(1)

    def import_datasets(self, zip_file, zip_filename: str = "superset_datasets.zip"):
        self._import_assets(zip_file, "/api/v1/dataset/import/", zip_filename, "dataset")

    def import_charts(self, zip_file, zip_filename: str = "superset_charts.zip"):
        self._import_assets(zip_file, "/api/v1/chart/import/", zip_filename, "chart")

    def import_dashboards(self, zip_file, zip_filename: str = "superset_full_export.zip"):
        self._import_assets(zip_file, "/api/v1/dashboard/import/", zip_filename, "dashboard")


def detect_intermediate_dir(export_dir: str) -> str:
    entries = [e for e in os.scandir(export_dir) if not e.name.startswith(".")]
    dirs  = [e for e in entries if e.is_dir()]
    files = [e for e in entries if e.is_file()]

    if files:
        logger.warning(
            "No intermediate directory found in the export folder. "
            "Assuming a flat structure (metadata.yaml at root)."
        )
        return ""

    if len(dirs) != 1:
        names = [d.name for d in dirs]
        logger.error(
            f"Expected exactly 1 intermediate directory inside {export_dir}, found: {names}."
        )
        sys.exit(1)

    intermediate = dirs[0].name
    logger.info(f"Intermediate directory detected: {intermediate}/")
    return intermediate


def copy_manifest_to_build(export_dir: str, build_dir: str) -> str:
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    shutil.copytree(export_dir, build_dir)
    logger.info(f"Export copied into build folder: {build_dir}")
    return build_dir


def patch_database_credentials(assets_root: str, creds: dict):
    patched_count = 0
    for root, dirs, files in os.walk(assets_root):
        if os.path.basename(root) != "databases":
            continue
        for filename in files:
            if not filename.endswith(".yaml"):
                continue

            file_path = os.path.join(root, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            original_uri = data.get("sqlalchemy_uri")
            if not original_uri:
                logger.warning(f"{filename}: no sqlalchemy_uri found, skipping.")
                continue

            url = make_url(original_uri)
            url = url.set(
                username=creds["db_user"],
                password=creds["db_pass"],
                host=creds["db_host"],
                port=int(creds["db_port"]),
                database=creds["db_name"],
            )
            patched_uri = url.render_as_string(hide_password=False)

            if original_uri == patched_uri:
                logger.warning(f"{filename}: URI unchanged after patch — check your credentials.")
            else:
                logger.info(f"Credentials injected into sqlalchemy_uri of: {filename}")

            data["sqlalchemy_uri"] = patched_uri

            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

            patched_count += 1

    if patched_count == 0:
        logger.warning("No database YAML files were patched. Check the export folder structure.")
    else:
        logger.info(f"Patched {patched_count} database YAML file(s) in {assets_root}.")


def collect_datasets_to_import(assets_root: str) -> list:
    """
    Returns absolute paths of all dataset YAML files under assets_root.
    The manifest is self-contained, so every dataset it contains is imported.
    """
    datasets_dir = os.path.join(assets_root, "datasets")
    if not os.path.isdir(datasets_dir):
        logger.info("No datasets/ directory found.")
        return []

    to_import = []
    for root, _, files in os.walk(datasets_dir):
        for filename in files:
            if not filename.endswith(".yaml"):
                continue
            file_path = os.path.join(root, filename)
            logger.info(f"  [ADD]  Dataset: {filename}")
            to_import.append(file_path)

    logger.info(f"Datasets: {len(to_import)} to import.")
    return to_import


def collect_charts_to_import(assets_root: str) -> list:
    """
    Returns absolute paths of all chart YAML files under assets_root.
    The manifest is self-contained, so every chart it contains is imported.
    """
    charts_dir = os.path.join(assets_root, "charts")
    if not os.path.isdir(charts_dir):
        logger.info("No charts/ directory found.")
        return []

    to_import = []
    for root, _, files in os.walk(charts_dir):
        for filename in files:
            if not filename.endswith(".yaml"):
                continue
            file_path = os.path.join(root, filename)
            logger.info(f"  [ADD]  Chart: {filename}")
            to_import.append(file_path)

    logger.info(f"Charts: {len(to_import)} to import.")
    return to_import


def build_dataset_uuid_index(assets_root: str) -> dict:
    """
    Maps dataset uuid -> absolute file path for every dataset YAML under assets_root.
    """
    datasets_dir = os.path.join(assets_root, "datasets")
    index = {}
    if not os.path.isdir(datasets_dir):
        return index

    for root, _, files in os.walk(datasets_dir):
        for filename in files:
            if not filename.endswith(".yaml"):
                continue
            file_path = os.path.join(root, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            uuid_value = data.get("uuid")
            if uuid_value:
                index[uuid_value] = file_path

    return index


def resolve_chart_dataset_dependencies(chart_files: list, dataset_uuid_index: dict) -> list:
    """
    Resolves each chart's dataset_uuid to its dataset YAML file, so it can be
    bundled in the same ZIP (required by the chart import API).
    """
    resolved = []
    seen = set()
    missing = 0

    for chart_path in chart_files:
        with open(chart_path, "r", encoding="utf-8") as f:
            chart_data = yaml.safe_load(f)

        dataset_uuid = chart_data.get("dataset_uuid")
        if not dataset_uuid:
            continue

        dataset_path = dataset_uuid_index.get(dataset_uuid)
        if not dataset_path:
            logger.warning(
                f"  [WARN] Chart {os.path.basename(chart_path)}: dataset_uuid "
                f"{dataset_uuid} not found among manifest datasets."
            )
            missing += 1
            continue

        if dataset_path not in seen:
            seen.add(dataset_path)
            resolved.append(dataset_path)

    logger.info(f"Charts depend on {len(resolved)} dataset(s) (bundled into chart ZIP).")
    if missing:
        logger.warning(f"{missing} chart(s) reference a dataset_uuid missing from the manifest.")

    return resolved


def build_selective_zip(
    build_dir: str,
    assets_root: str,
    selected_files: list,
    metadata_type: str = None,
) -> tempfile.NamedTemporaryFile:
    """
    Build a ZIP containing:
      - always: tags.yaml and all files under databases/
      - selected: the asset files passed in selected_files
    metadata_type: when provided (e.g. "Dataset", "Chart"), the 'type' field in
    metadata.yaml is overridden so the target import endpoint accepts the ZIP
    (the exported metadata.yaml is always "Dashboard").
    """
    other_base_files = []

    for always_file in ["tags.yaml"]:
        p = os.path.join(assets_root, always_file)
        if os.path.isfile(p):
            other_base_files.append(p)

    db_dir = os.path.join(assets_root, "databases")
    if os.path.isdir(db_dir):
        for root, _, files in os.walk(db_dir):
            for f in files:
                if f.endswith(".yaml"):
                    other_base_files.append(os.path.join(root, f))

    all_files = other_base_files + selected_files
    entries = []

    metadata_path = os.path.join(assets_root, "metadata.yaml")

    tmp = tempfile.NamedTemporaryFile(suffix=".zip", prefix="superset_import_", delete=True)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            if os.path.isfile(metadata_path):
                metadata_arcname = os.path.relpath(metadata_path, build_dir).replace(os.sep, "/")
                if metadata_type:
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        metadata = yaml.safe_load(f)
                    metadata["type"] = metadata_type
                    zf.writestr(metadata_arcname, yaml.dump(metadata, sort_keys=False, allow_unicode=True))
                    logger.info(f"metadata.yaml written with type: {metadata['type']}")
                else:
                    zf.write(metadata_path, metadata_arcname)
                entries.append(metadata_arcname)

            for file_path in all_files:
                arcname = os.path.relpath(file_path, build_dir).replace(os.sep, "/")
                zf.write(file_path, arcname)
                entries.append(arcname)
    except Exception:
        tmp.close()
        raise

    size_kb = os.path.getsize(tmp.name) / 1024
    logger.info(f"ZIP built: {len(entries)} entries ({size_kb:.1f} KB)")

    tmp.seek(0)
    return tmp


def build_full_zip(folder: str) -> tempfile.NamedTemporaryFile:
    """
    Build a ZIP of the entire folder.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", prefix="superset_import_", delete=True)
    entries = []

    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(folder):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    arcname = os.path.relpath(file_path, folder).replace(os.sep, "/")
                    zf.write(file_path, arcname)
                    entries.append(arcname)
    except Exception:
        tmp.close()
        raise

    top_level = sorted({e.split("/")[0] for e in entries})
    logger.info(f"ZIP contains {len(entries)} entries. Top-level entries: {top_level}")

    metadata_entries = [e for e in entries if e.endswith("metadata.yaml")]
    if not metadata_entries:
        logger.warning("metadata.yaml NOT found anywhere in the ZIP — Superset will reject the import!")
    else:
        logger.info(f"metadata.yaml found at: {metadata_entries}")

    size_kb = os.path.getsize(tmp.name) / 1024
    logger.info(f"ZIP written to temp file: {tmp.name} ({size_kb:.1f} KB)")

    tmp.seek(0)
    return tmp


def main():
    if len(sys.argv) != 4:
        print("Usage: import.py <TAG> <MANIFESTS_DIR> <BUILD_DIR>")
        print("All Superset and DB credentials must be set as environment variables.")
        sys.exit(1)

    tag           = sys.argv[1]
    manifests_dir = sys.argv[2]
    build_dir     = sys.argv[3]

    base_url = _require_env("SUPERSET_URL")
    username = _require_env("SUPERSET_USER")
    password = _require_env("SUPERSET_PASSWORD")

    creds = {
        "db_user": _require_env("ANALYTICS_DB_USER"),
        "db_pass": _require_env("ANALYTICS_DB_PASSWORD"),
        "db_host": _require_env("ANALYTICS_DB_HOST"),
        "db_port": _require_env("ANALYTICS_DB_PORT"),
        "db_name": _require_env("ANALYTICS_DB_NAME"),
    }

    if not os.path.isdir(manifests_dir):
        logger.error(f"Manifests folder not found for tag '{tag}': {manifests_dir}")
        sys.exit(1)

    logger.info(f"Using manifests folder: {manifests_dir}")
    logger.info(f"--- STARTING ASSET IMPORT (tag: {tag}) ---")

    # ── Prepare build dir (copy manifests) ────────────────────────────────────
    intermediate_dir = detect_intermediate_dir(manifests_dir)
    build_dir = copy_manifest_to_build(manifests_dir, build_dir)
    assets_root = os.path.join(build_dir, intermediate_dir) if intermediate_dir else build_dir

    # ── Patch DB credentials on every databases/*.yaml ────────────────────────
    patch_database_credentials(assets_root, creds)

    client = SupersetClient(base_url, username, password)
    client.authenticate()

    # ── Step 1: import datasets ────────────────────────────────────────────────
    logger.info("--- STEP 1: DATASET IMPORT ---")
    dataset_files = collect_datasets_to_import(assets_root)
    if dataset_files:
        with build_selective_zip(build_dir, assets_root, dataset_files, metadata_type="SqlaTable") as zip_file:
            client.import_datasets(zip_file)
    else:
        logger.info("No datasets to import.")

    # ── Step 2: import charts (with their referenced datasets bundled) ────────
    logger.info("--- STEP 2: CHART IMPORT ---")
    chart_files = collect_charts_to_import(assets_root)
    if chart_files:
        dataset_uuid_index = build_dataset_uuid_index(assets_root)
        chart_dataset_files = resolve_chart_dataset_dependencies(chart_files, dataset_uuid_index)
        with build_selective_zip(build_dir, assets_root, chart_files + chart_dataset_files, metadata_type="Slice") as zip_file:
            client.import_charts(zip_file)
    else:
        logger.info("No charts to import.")

    # ── Step 3: import dashboards (full ZIP) ───────────────────────────────────
    logger.info("--- STEP 3: DASHBOARD IMPORT ---")
    with build_full_zip(build_dir) as zip_file:
        client.import_dashboards(zip_file)

    logger.info(f"--- IMPORT COMPLETED (tag: {tag}) ---")


if __name__ == "__main__":
    main()
