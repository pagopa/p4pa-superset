import io
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

    def import_dashboards(self, zip_file, zip_filename: str = "superset_full_export.zip"):
        if not self.is_authenticated:
            logger.error("Client not authenticated. Call authenticate() first.")
            sys.exit(1)

        size_kb = os.fstat(zip_file.fileno()).st_size / 1024
        logger.info(f"Sending ZIP to dashboard import API ({size_kb:.1f} KB)...")
        files = {"formData": (zip_filename, zip_file, "application/zip")}

        try:
            r = self.session.post(
                f"{self.base_url}/api/v1/dashboard/import/",
                files=files,
                data={"overwrite": "true"},
            )
            r.raise_for_status()
            logger.info("SUCCESS. Dashboard import completed.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during import: {e} — API response: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error during import: {e}")
            sys.exit(1)

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


def prepare_build(export_dir: str, intermediate_dir: str, creds: dict, build_dir: str) -> str:
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


def build_zip_to_tempfile(folder: str) -> tempfile.NamedTemporaryFile:
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
    # ── Arguments ─────────────
    if len(sys.argv) != 4:
        print("Usage: import.py <TAG> <MANIFESTS_DIR> <BUILD_DIR>")
        print("All Superset and DB credentials must be set as environment variables.")
        sys.exit(1)

    tag           = sys.argv[1]
    manifests_dir = sys.argv[2]
    build_dir     = sys.argv[3]

    # ── Env var credentials────────────────────────────────────────────────
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

    intermediate_dir = detect_intermediate_dir(manifests_dir)
    build_dir = prepare_build(manifests_dir, intermediate_dir, creds, build_dir)

    logger.info("Building ZIP to temp file from build folder...")

    with build_zip_to_tempfile(build_dir) as zip_file:
        client = SupersetClient(base_url, username, password)
        client.authenticate()
        client.import_dashboards(zip_file)

    logger.info(f"--- IMPORT COMPLETED (tag: {tag}) ---")


if __name__ == "__main__":
    main()