import io
import os
import sys
import shutil
import logging
import zipfile
import requests
import yaml
from sqlalchemy.engine.url import make_url

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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

    def import_all_assets(self, zip_bytes: bytes, zip_filename: str = "superset_full_export.zip"):
        if not self.is_authenticated:
            logger.error("Client not authenticated. Call authenticate() first.")
            sys.exit(1)

        logger.info(f"Sending ZIP to API ({len(zip_bytes) / 1024:.1f} KB)...")
        files = {"bundle": (zip_filename, io.BytesIO(zip_bytes), "application/zip")}

        try:
            r = self.session.post(
                f"{self.base_url}/api/v1/assets/import/",
                files=files,
                # overwrite=true is required to overwrite existing assets..
                data={
                    "overwrite": "true",
                    "passwords": "{}",
                },
            )
            r.raise_for_status()
            logger.info("SUCCESS. Asset import completed.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during import: {e} — API response: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error during import: {e}")
            sys.exit(1)


def detect_intermediate_dir(export_dir: str) -> str:
    """
    Detects the single intermediate directory (e.g. 'assets_export' or timestamped)
    inside the export folder.

    Expected structure:
        export_dir/
            assets_export/
                metadata.yaml
                databases/
                ...

    Returns the name of the intermediate directory (not the full path).
    Falls back gracefully to a flat structure if no subdirectory is found.
    """
    entries = [e for e in os.scandir(export_dir) if not e.name.startswith(".")]
    dirs  = [e for e in entries if e.is_dir()]
    files = [e for e in entries if e.is_file()]

    if files:
        logger.warning(
            "No intermediate directory found in the export folder. "
            "Assuming a flat structure (metadata.yaml at root). "
            "Re-run the export to get the canonical nested structure."
        )
        return ""

    if len(dirs) != 1:
        names = [d.name for d in dirs]
        logger.error(
            f"Expected exactly 1 intermediate directory inside {export_dir}, found: {names}. "
            "Re-run the export or specify a different path."
        )
        sys.exit(1)

    intermediate = dirs[0].name
    logger.info(f"Intermediate directory detected: {intermediate}/")
    return intermediate


def prepare_build(export_dir: str, intermediate_dir: str, creds: dict, build_dir: str) -> str:
    """
    Copies the export folder into build_dir and patches sqlalchemy_uri in the
    database YAML found there. The intermediate directory structure is preserved.
    The original export folder is never modified.
    """
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    shutil.copytree(export_dir, build_dir)
    logger.info(f"Export copied into build folder: {build_dir}")

    assets_root = os.path.join(build_dir, intermediate_dir) if intermediate_dir else build_dir

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
        logger.info(f"Patched {patched_count} database YAML file(s) in {build_dir}.")

    return build_dir


def build_zip_from_folder(folder: str) -> bytes:
    """
    Walks the folder and builds a ZIP in memory.
    """
    out_buffer = io.BytesIO()
    entries = []

    with zipfile.ZipFile(out_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder):
            for filename in files:
                file_path = os.path.join(root, filename)
                arcname = os.path.relpath(file_path, folder).replace(os.sep, "/")
                zf.write(file_path, arcname)
                entries.append(arcname)

    top_level = sorted({e.split("/")[0] for e in entries})
    logger.info(f"ZIP contains {len(entries)} entries. Top-level entries: {top_level}")

    metadata_entries = [e for e in entries if e.endswith("metadata.yaml")]
    if not metadata_entries:
        logger.warning("metadata.yaml NOT found anywhere in the ZIP — Superset will reject the import!")
    else:
        logger.info(f"metadata.yaml found at: {metadata_entries}")

    return out_buffer.getvalue()


def main():
    # Expected arguments:
    #   1  SUPERSET_URL
    #   2  SUPERSET_USER
    #   3  SUPERSET_PASSWORD
    #   4  ANALYTICS_DB_USER
    #   5  ANALYTICS_DB_PASSWORD
    #   6  ANALYTICS_DB_HOST
    #   7  ANALYTICS_DB_PORT
    #   8  ANALYTICS_DB_NAME
    #   9  MANIFESTS_DIR   (absolute path to manifests/superset_full_export)
    #   10 BUILD_DIR       (absolute path to build/)
    if len(sys.argv) < 11:
        print(
            "Usage: import.py <SUPERSET_URL> <SUPERSET_USER> <SUPERSET_PASSWORD> "
            "<ANALYTICS_DB_USER> <ANALYTICS_DB_PASSWORD> <ANALYTICS_DB_HOST> "
            "<ANALYTICS_DB_PORT> <ANALYTICS_DB_NAME> "
            "<MANIFESTS_DIR> <BUILD_DIR>"
        )
        sys.exit(1)

    base_url      = sys.argv[1]
    username      = sys.argv[2]
    password      = sys.argv[3]
    db_user       = sys.argv[4]
    db_pass       = sys.argv[5]
    db_host       = sys.argv[6]
    db_port       = sys.argv[7]
    db_name       = sys.argv[8]
    manifests_dir = sys.argv[9]
    build_dir     = sys.argv[10]

    creds = {
        "db_user": db_user,
        "db_pass": db_pass,
        "db_host": db_host,
        "db_port": db_port,
        "db_name": db_name,
    }

    if not os.path.isdir(manifests_dir):
        logger.error(f"Manifests folder not found: {manifests_dir}. Run the export first.")
        sys.exit(1)

    logger.info(f"Using manifests folder: {manifests_dir}")
    logger.info("--- STARTING ASSET IMPORT ---")

    intermediate_dir = detect_intermediate_dir(manifests_dir)
    build_dir = prepare_build(manifests_dir, intermediate_dir, creds, build_dir)

    logger.info("Building ZIP in memory from build folder...")
    zip_bytes = build_zip_from_folder(build_dir)
    logger.info(f"ZIP built in memory ({len(zip_bytes) / 1024:.1f} KB)")

    client = SupersetClient(base_url, username, password)
    client.authenticate()
    client.import_all_assets(zip_bytes)

    logger.info("--- IMPORT COMPLETED ---")


if __name__ == "__main__":
    main()
