import os
import sys
import zipfile
import shutil
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SupersetClient:
    def __init__(self, base_url, username, password):
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

    def export_all_assets(self, output_dir="exports"):
        """
        Exports all assets via /api/v1/assets/export/ and saves the result as a ZIP file.
        Also extracts the ZIP contents for change tracking.
        """
        if not self.is_authenticated:
            logger.error("Client not authenticated. Call authenticate() first.")
            sys.exit(1)

        target_path = os.path.join(os.getcwd(), output_dir)
        os.makedirs(target_path, exist_ok=True)

        zip_filename = f"superset_full_export.zip"
        zip_filepath = os.path.join(target_path, zip_filename)
        extract_dir  = os.path.join(target_path, f"superset_full_export")

        logger.info("Starting full asset export via /api/v1/assets/export/ ...")

        try:
            r = self.session.get(f"{self.base_url}/api/v1/assets/export/", stream=True)
            r.raise_for_status()

            with open(zip_filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            size = os.path.getsize(zip_filepath)
            if size <= 500:
                logger.warning(
                    f"ZIP file is very small ({size} bytes). "
                    "The environment may contain no assets."
                )

            logger.info(f"ZIP saved: {zip_filename} ({size} bytes)")

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during export: {e} — Response: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error during export: {e}")
            sys.exit(1)

        # Extract ZIP contents into a subfolder with the same name as the archive.
        # The inner root folder produced by Superset (e.g. assets_export_20260310T112859/)
        # is stripped so the extracted structure starts directly from databases/, charts/, etc.
        try:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            logger.info(f"Extracting ZIP into: {extract_dir}")
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(zip_filepath, "r") as zf:
                members = zf.infolist()

                # Detect and strip the common root folder added by Superset
                root_prefix = ""
                first_parts = {m.filename.split("/")[0] for m in members if "/" in m.filename}
                if len(first_parts) == 1:
                    root_prefix = first_parts.pop() + "/"

                for member in members:
                    relative_path = member.filename
                    if root_prefix:
                        relative_path = relative_path[len(root_prefix):]
                    if not relative_path or relative_path.endswith("/"):
                        continue

                    dest_path = os.path.join(extract_dir, relative_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with zf.open(member) as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())

            extracted_files = sum(len(files) for _, _, files in os.walk(extract_dir))
            logger.info(f"Extraction complete: {extracted_files} files extracted into {extract_dir}")

        except Exception as e:
            logger.error(f"Error during ZIP extraction: {e}")
            sys.exit(1)


def main():
    base_url = os.getenv("SUPERSET_URL")
    username = os.getenv("SUPERSET_USER")
    password = os.getenv("SUPERSET_PASSWORD")

    client = SupersetClient(base_url, username, password)

    logger.info("--- STARTING FULL ASSET EXPORT ---")
    client.authenticate()
    client.export_all_assets()
    logger.info("--- EXPORT COMPLETED ---")


if __name__ == "__main__":
    main()