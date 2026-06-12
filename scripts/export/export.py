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

    def get_dashboard_ids_by_tag(self, tag_name: str) -> list[int]:
        """
        Returns the list of dashboard IDs associated with the given tag,
        using the /api/v1/tag/get_objects/ endpoint.
        Includes pre-validation to avoid downloading all dashboards if the tag is empty or invalid.
        """
        
        # 1. Controllo di sicurezza: se non viene passato alcun tag (o è una stringa vuota), esci.
        if not tag_name or not tag_name.strip():
            logger.error("Nessun tag fornito (stringa vuota o assente). Esportazione annullata.")
            return []

        try:
            # 2. Verifica preventiva: controlliamo se il tag esiste a sistema
            # Usiamo l'API dei tag filtrando per nome
            check_tag_query = f"(filters:!((col:name,opr:eq,value:'{tag_name}')))"
            r_check_tag = self.session.get(
                f"{self.base_url}/api/v1/tag/",
                params={"q": check_tag_query}
            )

            if r_check_tag.status_code == 200:
                tags_found = r_check_tag.json().get("result", [])
                # Se la lista è vuota, il tag non esiste nel DB di Superset
                if not tags_found:
                    logger.error(f"Tag '{tag_name}' does not exists in Superset. Nothing exported")
                    return []
            else:
                logger.error(f"Error during tag validation: {r_check_tag.text}")
                r_check_tag.raise_for_status()

            # 3. Se il tag esiste, procediamo con la logica originale per ottenere le dashboard associate
            rison_params = f"(tags:!('{tag_name}'))"
            r = self.session.get(
                f"{self.base_url}/api/v1/tag/get_objects/",
                params={"q": rison_params}
            )

            if r.status_code != 200:
                logger.error(f"Error fetching objects by tag: {r.text}")
                r.raise_for_status()

            all_objects = r.json().get("result", [])

            dashboard_ids = [
                obj["id"]
                for obj in all_objects
                if obj.get("type") == "dashboard"
            ]

            if not dashboard_ids:
                logger.warning(f"Tag '{tag_name}' exists, but has no linked dashboard.")
                return []

            logger.info(f"Found {len(dashboard_ids)} dashboard(s) with tag '{tag_name}': {dashboard_ids}")
            return dashboard_ids

        except Exception as e:
            logger.error(f"Error fetching dashboards by tag '{tag_name}': {e}")
            return []

    def export_dashboards_by_tag(self, tag_name: str, extract_dir: str):
        """
        Fetches all dashboards associated with the given tag, exports them as a ZIP
        via /api/v1/dashboard/export/, and extracts the contents into extract_dir.
        """
        if not self.is_authenticated:
            logger.error("Client not authenticated. Call authenticate() first.")
            sys.exit(1)

        # 1. Resolve dashboard IDs for the tag
        dashboard_ids = self.get_dashboard_ids_by_tag(tag_name)
        if not dashboard_ids:
            logger.error(f"No dashboards to export for tag '{tag_name}'. Aborting.")
            sys.exit(1)

        os.makedirs(extract_dir, exist_ok=True)

        # 2. Request the export ZIP for those specific IDs
        ids_rison = "!(" + ",".join(str(i) for i in dashboard_ids) + ")"
        logger.info(f"Exporting dashboards with IDs {dashboard_ids} ...")

        try:
            r = self.session.get(
                f"{self.base_url}/api/v1/dashboard/export/",
                params={"q": ids_rison},
                stream=True,
            )
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

        # 3. Extract ZIP contents directly from memory into the output folder
        try:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir, exist_ok=True)
            logger.info(f"Extracting into: {extract_dir}")

            with zipfile.ZipFile(zip_buffer, "r") as zf:
                name_list = zf.namelist()
                if not name_list:
                    logger.warning("ZIP file is empty.")
                    return

                # Detect the original intermediate directory name (first component of the first path)
                original_root = name_list[0].split('/')[0]
                logger.info(f"Removing intermediate directory '{original_root}' from extracted paths")

                for member in zf.infolist():
                    relative_path = member.filename
                    if not relative_path or relative_path.endswith("/"):
                        continue

                    # Remove the original root component
                    if relative_path.startswith(original_root + "/"):
                        new_relative_path = relative_path[len(original_root) + 1:]
                    elif relative_path == original_root:
                        continue
                    else:
                        new_relative_path = relative_path

                    dest_path = os.path.join(extract_dir, new_relative_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with zf.open(member) as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())

            logger.info(f"Extraction complete into {extract_dir}/")

        except Exception as e:
            logger.error(f"Error during ZIP extraction: {e}")
            sys.exit(1)


def main():
    if len(sys.argv) < 5:
        print("Usage: export.py <SUPERSET_URL> <SUPERSET_USER> <SUPERSET_PASSWORD> <TAG>")
        sys.exit(1)

    base_url   = sys.argv[1]
    username   = sys.argv[2]
    password   = sys.argv[3]
    tag        = sys.argv[4]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(script_dir))
    extract_dir = os.path.join(root_dir, "manifests", tag, "assets_export")

    client = SupersetClient(base_url, username, password)

    logger.info(f"--- STARTING EXPORT FOR TAG '{tag}' ---")
    client.authenticate()
    client.export_dashboards_by_tag(tag_name=tag, extract_dir=extract_dir)
    logger.info("--- EXPORT COMPLETED ---")


if __name__ == "__main__":
    main()