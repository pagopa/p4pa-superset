import io
import os
import re
import sys
import glob
import logging
import argparse
import zipfile
import requests

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

    def import_all_assets(self, zip_bytes: bytes, original_filename: str):
        if not self.is_authenticated:
            logger.error("Client not authenticated. Call authenticate() first.")
            sys.exit(1)

        logger.info(f"Sending patched ZIP to API ({len(zip_bytes) / 1024:.1f} KB)...")
        files = {"bundle": (original_filename, io.BytesIO(zip_bytes), "application/zip")}

        try:
            r = self.session.post(
                f"{self.base_url}/api/v1/assets/import/",
                files=files,
                data={"passwords": "{}"},
            )
            r.raise_for_status()
            logger.info("SUCCESS. Asset import completed.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during import: {e} — API response: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error during import: {e}")
            sys.exit(1)


def inject_password_into_zip(zip_path: str) -> bytes:
    """
    Reads the ZIP, replaces the 'XXXXXXXXXX' placeholder in the target database
    YAML's sqlalchemy_uri with the target DB password (from DB_PASS),
    and returns the patched ZIP as bytes.
    """
    db_pass = os.getenv("ANALYTICS_DB_PASSWORD")
    if not db_pass:
        logger.error("Environment variable DB_PASS is missing.")
        sys.exit(1)

    out_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_path, "r") as zin, \
         zipfile.ZipFile(out_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zout:

        for item in zin.infolist():
            item_path = item.filename
            content = zin.read(item_path)

            if "/databases/" in item_path and item_path.endswith(".yaml"):
                yaml_filename = os.path.basename(item_path)
                original_yaml = content.decode("utf-8")
                patched_yaml = re.sub(
                    r'(sqlalchemy_uri:\s+\S+?)XXXXXXXXXX(\S*)',
                    lambda m: m.group(1) + db_pass + m.group(2),
                    original_yaml,
                )

                if patched_yaml == original_yaml:
                    logger.warning(f"{yaml_filename}: no 'XXXXXXXXXX' placeholder found in URI, importing as-is.")
                else:
                    logger.info(f"Password injected into sqlalchemy_uri of target database: {yaml_filename}")

                zout.writestr(item, patched_yaml.encode("utf-8"))
            else:
                zout.writestr(item, content)

    return out_buffer.getvalue()



def get_latest_export(folder: str = "exports") -> str | None:
    target_path = os.path.join(os.getcwd(), folder)
    if not os.path.exists(target_path):
        return None
        
    full_export = os.path.join(target_path, "superset_full_export.zip")
    if os.path.exists(full_export):
        return full_export
        
    return None


def main():
    parser = argparse.ArgumentParser(description="Superset full asset import")
    parser.add_argument("--file", help="ZIP file path. If omitted, uses the latest export in exports/")
    args = parser.parse_args()

    base_url = os.getenv("SUPERSET_URL")
    username = os.getenv("SUPERSET_USER")
    password = os.getenv("SUPERSET_PASSWORD")

    zip_file = args.file
    if not zip_file:
        logger.info("No ZIP file specified, looking for the latest export in exports/...")
        zip_file = get_latest_export()

    if not zip_file or not os.path.exists(zip_file):
        logger.error("No ZIP file found. Run the export first or specify --file <path>")
        sys.exit(1)

    logger.info("--- STARTING ASSET IMPORT ---")

    patched_zip_bytes = inject_password_into_zip(zip_file)

    client = SupersetClient(base_url, username, password)
    client.authenticate()
    client.import_all_assets(patched_zip_bytes, os.path.basename(zip_file))

    logger.info("--- IMPORT COMPLETED ---")


if __name__ == "__main__":
    main()