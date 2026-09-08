import os
import sys
import logging
import zipfile
import tempfile
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# (build subfolder, Superset import endpoint, label, zip filename), in import order.
MANIFEST_STEPS = (
    ("manifests_dataset",    "/api/v1/dataset/import/",   "dataset",   "superset_datasets.zip"),
    ("manifests_charts",     "/api/v1/chart/import/",     "chart",     "superset_charts.zip"),
    ("manifests_dashboards", "/api/v1/dashboard/import/", "dashboard", "superset_full_export.zip"),
)


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

    def import_assets(self, zip_file, endpoint: str, zip_filename: str, label: str):
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


def build_zip(folder: str) -> tempfile.NamedTemporaryFile:
    """
    Zips the entire content of folder as-is. manifest_builder.py has already
    selected, patched and laid out everything that belongs in it.
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

    metadata_entries = [e for e in entries if e.endswith("metadata.yaml")]
    if not metadata_entries:
        logger.warning("metadata.yaml NOT found anywhere in the ZIP — Superset will reject the import!")

    size_kb = os.path.getsize(tmp.name) / 1024
    logger.info(f"ZIP built: {len(entries)} entries ({size_kb:.1f} KB)")

    tmp.seek(0)
    return tmp


def main():
    if len(sys.argv) != 3:
        print("Usage: import.py <TAG> <BUILD_DIR>")
        print("BUILD_DIR must already contain the manifests produced by manifest_builder.py.")
        print("Superset credentials must be set as environment variables.")
        sys.exit(1)

    tag       = sys.argv[1]
    build_dir = sys.argv[2]

    base_url = _require_env("SUPERSET_URL")
    username = _require_env("SUPERSET_USER")
    password = _require_env("SUPERSET_PASSWORD")

    if not os.path.isdir(build_dir):
        logger.error(f"Build folder not found: {build_dir}")
        sys.exit(1)

    logger.info(f"--- STARTING ASSET IMPORT (tag: {tag}) ---")

    client = SupersetClient(base_url, username, password)
    client.authenticate()

    for subdir, endpoint, label, zip_filename in MANIFEST_STEPS:
        manifest_path = os.path.join(build_dir, subdir)
        logger.info(f"--- STEP: {label.upper()} IMPORT ---")

        if not os.path.isdir(manifest_path):
            logger.info(f"No '{subdir}' manifest found — skipping {label} import.")
            continue

        with build_zip(manifest_path) as zip_file:
            client.import_assets(zip_file, endpoint, zip_filename, label)

    logger.info(f"--- IMPORT COMPLETED (tag: {tag}) ---")


if __name__ == "__main__":
    main()
