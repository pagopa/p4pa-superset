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
        Returns dashboard IDs tagged with tag_name.
        Uses /api/v1/dashboard/ with a tag filter.
        """
        if not tag_name or not tag_name.strip():
            logger.error("No tag provided (empty string). Export cancelled.")
            return []

        try:
            # ── Step 1: Validate tag existence ──────────────────────────────────
            check_tag_query = f"(filters:!((col:name,opr:eq,value:'{tag_name}')))"
            r_check = self.session.get(
                f"{self.base_url}/api/v1/tag/",
                params={"q": check_tag_query},
            )
            r_check.raise_for_status()
    
            tags_found = r_check.json().get("result", [])
            if not tags_found:
                logger.error(f"Tag '{tag_name}' does not exist in Superset. Nothing exported.")
                return []
    
            logger.info(f"Tag '{tag_name}' found (id={tags_found[0].get('id')}). Fetching dashboards...")
    
            # ── Step 2: Fetch dashboards via the dashboard list API ──────────────
            # The 'dashboard_tags' operator is natively supported and filters correctly.
            # Pagination is handled to cope with large environments.
            all_ids: list[int] = []
            page = 0
            page_size = 100
    
            while True:
                rison_filter = (
                    f"(filters:!((col:tags,opr:dashboard_tags,value:'{tag_name}')),"
                    f"page:{page},page_size:{page_size})"
                )
                r = self.session.get(
                    f"{self.base_url}/api/v1/dashboard/",
                    params={"q": rison_filter},
                )
    
                # Graceful fallback: if the operator is not supported by this Superset
                # version, log clearly and raise so the caller can decide.
                if r.status_code == 400:
                    logger.warning(
                        "'dashboard_tags' filter operator not supported by this Superset version. "
                        "Consider upgrading Superset (>= 2.1) or use the fallback method."
                    )
                    r.raise_for_status()
    
                r.raise_for_status()
                result = r.json()
    
                dashboards = result.get("result", [])
                if not dashboards:
                    break
    
                all_ids.extend(d["id"] for d in dashboards)
    
                # Stop when we have fetched all available records
                total_count = result.get("count", 0)
                if len(all_ids) >= total_count:
                    break
    
                page += 1
    
            if not all_ids:
                logger.warning(f"Tag '{tag_name}' exists but has no linked dashboards.")
                return []
    
            logger.info(f"Found {len(all_ids)} dashboard(s) with tag '{tag_name}': {all_ids}")
            return all_ids
    
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
        # 1. Resolve dashboard IDs for the tag
        dashboard_ids = self.get_dashboard_ids_by_tag(tag_name)
        if not dashboard_ids:
            logger.error(f"No dashboards to export for tag '{tag_name}'. Aborting.")
            sys.exit(1)

        os.makedirs(extract_dir, exist_ok=True)

        # 2. Request the export ZIP for those specific IDs
        ids_rison = "!(" + ",".join(str(i) for i in dashboard_ids) + ")"
        logger.info(f"Exporting dashboards with IDs {dashboard_ids} ...")
        # 2. Request the export ZIP for those specific IDs
        ids_rison = "!(" + ",".join(str(i) for i in dashboard_ids) + ")"
        logger.info(f"Exporting dashboards with IDs {dashboard_ids} ...")

        try:
            r = self.session.get(
                f"{self.base_url}/api/v1/dashboard/export/",
                params={"q": ids_rison},
                stream=True,
            )
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
    tag        = sys.argv[4]

    client = SupersetClient(base_url, username, password)

    logger.info(f"--- STARTING EXPORT FOR TAG '{tag}' ---")
    client.authenticate()
    client.export_dashboards_by_tag(tag_name=tag, extract_dir=extract_dir)
    logger.info("--- EXPORT COMPLETED ---")


if __name__ == "__main__":
    main()