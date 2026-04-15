import os
import sys
import io
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

    def export_all_assets(self, output_dir: str):
        """
        Exports all assets via /api/v1/assets/export/ and extracts them directly
        into output_dir (absolute path expected).
        """
        if not self.is_authenticated:
            logger.error("Client not authenticated. Call authenticate() first.")
            sys.exit(1)

        os.makedirs(output_dir, exist_ok=True)

        extract_dir = os.path.join(output_dir, "superset_full_export")

        logger.info("Starting full asset export via /api/v1/assets/export/ ...")

        try:
            r = self.session.get(f"{self.base_url}/api/v1/assets/export/", stream=True)
            r.raise_for_status()

            # Read the ZIP response directly into memory — no zip file saved to disk
            zip_buffer = io.BytesIO()
            for chunk in r.iter_content(chunk_size=8192):
                zip_buffer.write(chunk)
            zip_buffer.seek(0)

            size = zip_buffer.getbuffer().nbytes
            if size <= 500:
                logger.warning(
                    f"ZIP response is very small ({size} bytes). "
                    "The environment may contain no assets."
                )
            else:
                logger.info(f"ZIP received in memory ({size} bytes)")

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during export: {e} — Response: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error during export: {e}")
            sys.exit(1)

        # Extract ZIP contents directly from memory into the output folder.
        try:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir, exist_ok=True)
            logger.info(f"Extracting into: {extract_dir}")

            with zipfile.ZipFile(zip_buffer, "r") as zf:
                # Rename top-level directory to a fixed name 'assets_export' to avoid git diff noise.
                name_list = zf.namelist()
                if not name_list:
                    logger.warning("ZIP file is empty.")
                    return

                # Detect the original intermediate directory name (first component of the first path)
                original_root = name_list[0].split('/')[0]
                fixed_root = "assets_export"
                logger.info(f"Renaming intermediate directory from '{original_root}' to '{fixed_root}'")

                for member in zf.infolist():
                    relative_path = member.filename
                    if not relative_path or relative_path.endswith("/"):
                        continue

                    # Replace the original root component with the fixed one
                    if relative_path.startswith(original_root + "/"):
                        new_relative_path = fixed_root + relative_path[len(original_root):]
                    elif relative_path == original_root:
                        # Skip the root directory itself if it's explicitly in the ZIP
                        continue
                    else:
                        # Should not happen with standard Superset exports
                        new_relative_path = relative_path

                    dest_path = os.path.join(extract_dir, new_relative_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with zf.open(member) as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())

            logger.info(f"Extraction complete into {extract_dir}/{fixed_root}/")

        except Exception as e:
            logger.error(f"Error during ZIP extraction: {e}")
            sys.exit(1)


def main():
    if len(sys.argv) < 5:
        print("Usage: export.py <SUPERSET_URL> <SUPERSET_USER> <SUPERSET_PASSWORD> <OUTPUT_DIR>")
        sys.exit(1)

    base_url   = sys.argv[1]
    username   = sys.argv[2]
    password   = sys.argv[3]
    output_dir = sys.argv[4]

    client = SupersetClient(base_url, username, password)

    logger.info("--- STARTING FULL ASSET EXPORT ---")
    client.authenticate()
    client.export_all_assets(output_dir)
    logger.info("--- EXPORT COMPLETED ---")


if __name__ == "__main__":
    main()