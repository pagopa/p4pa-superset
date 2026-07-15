import os
import sys
import shutil
import logging
import requests
import yaml
from sqlalchemy.engine.url import make_url

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RAW_GITHUB = "https://raw.githubusercontent.com"
GITHUB_OWNER_DEFAULT = "pagopa"
GITHUB_REPO_DEFAULT = "p4pa-superset"

# Core dependencies are always retrieved from develop.
CORE_DEPENDENCIES_BRANCH = "develop"

ASSET_TOP_FOLDERS = ("datasets", "charts", "dashboards", "databases")
DEPENDENCIES_FILENAME = "dependencies.txt"

DATASET_MANIFEST_DIRNAME = "manifests_dataset"
CHARTS_MANIFEST_DIRNAME = "manifests_charts"
DASHBOARDS_MANIFEST_DIRNAME = "manifests_dashboards"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        logger.error(f"Required environment variable '{name}' is not set.")
        sys.exit(1)
    return value


def relative_asset_path(remote_path: str) -> str:
    """
    Returns the path of a core dependency relative to assets_root, preserving
    its full subfolder structure.
    """
    parts = remote_path.replace("\\", "/").split("/")
    for i, part in enumerate(parts):
        if part in ASSET_TOP_FOLDERS:
            return "/".join(parts[i:])
    logger.warning(f"Could not determine relative placement for '{remote_path}', using filename only.")
    return parts[-1]


def fetch_file_raw_content(session: requests.Session, owner: str, repo: str, branch: str, path: str) -> bytes:
    """
    Fetches a single file's raw content directly from raw.githubusercontent.com.
    The core repo is public, so no auth is needed here, and no base64
    decoding is required (unlike the Contents API).
    """
    url = f"{RAW_GITHUB}/{owner}/{repo}/{branch}/{path}"
    r = session.get(url, timeout=30)
    if r.status_code == 404:
        raise FileNotFoundError(f"'{path}' not found in {owner}/{repo}@{branch}")
    r.raise_for_status()
    return r.content


def dependencies_file_path(manifests_dir: str) -> str:
    """
    The manifests/<TAG>/dependencies.txt file is ignored while building the import manifests.
    """
    return os.path.join(manifests_dir, DEPENDENCIES_FILENAME)


def materialize_dependencies(deps_path: str, assets_root: str, owner: str, repo: str) -> set:
    """
    Fetches each file referenced by the dependency ledger from the core repo
    (always from develop) and writes it back into assets_root. Only called
    when dependencies.txt exists for this tag. All fetches share one HTTP
    connection (Session) since they hit the same host.
    """
    materialized_paths = set()

    with open(deps_path, "r", encoding="utf-8") as f:
        references = [line.strip() for line in f if line.strip()]

    if not references:
        logger.info(f"{deps_path} is empty — nothing to fetch from core.")
        return materialized_paths

    logger.info(f"Fetching {len(references)} core dependenc(y/ies) from branch '{CORE_DEPENDENCIES_BRANCH}'.")

    fetched = missing = 0
    with requests.Session() as session:
        for ref_path in references:
            try:
                content = fetch_file_raw_content(session, owner, repo, CORE_DEPENDENCIES_BRANCH, ref_path)
            except Exception as e:
                logger.warning(f"  [MISSING] Could not fetch core dependency '{ref_path}': {e}. Continuing without it.")
                missing += 1
                continue

            rel_path = relative_asset_path(ref_path)
            dest_path = os.path.join(assets_root, *rel_path.split("/"))
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as out:
                out.write(content)
            materialized_paths.add(dest_path)
            logger.info(f"  [FETCHED] {ref_path} -> {rel_path}")
            fetched += 1

    logger.info(f"Core dependencies materialized: {fetched} fetched, {missing} missing/failed.")
    return materialized_paths


def detect_intermediate_dir(export_dir: str) -> str:
    entries = [
        e for e in os.scandir(export_dir)
        if not e.name.startswith(".") and e.name != DEPENDENCIES_FILENAME
    ]
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
    shutil.copytree(export_dir, build_dir, ignore=shutil.ignore_patterns(DEPENDENCIES_FILENAME))
    logger.info(f"Export copied into build folder: {build_dir}")
    return build_dir


def patch_database_credentials(assets_root: str, creds: dict):
    """
    Patches sqlalchemy_uri in every databases/*.yaml under assets_root with
    the target Analytics DB credentials. Runs after materialize_dependencies
    so a databases/*.yaml fetched back from core also gets patched.
    """
    patched_count = 0
    for root, _, files in os.walk(assets_root):
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


def collect_datasets_to_import(assets_root: str, core_paths: set) -> list:
    """
    Returns absolute paths of dataset YAML files that are NOT core
    dependencies.
    """
    datasets_dir = os.path.join(assets_root, "datasets")
    if not os.path.isdir(datasets_dir):
        logger.info("No datasets/ directory found.")
        return []

    to_import = []
    skipped = 0

    for root, _, files in os.walk(datasets_dir):
        for filename in files:
            if not filename.endswith(".yaml"):
                continue
            file_path = os.path.join(root, filename)
            if file_path in core_paths:
                logger.info(f"  [SKIP] Dataset materialized from core repo: {filename}")
                skipped += 1
            else:
                logger.info(f"  [ADD]  Dataset not in core repo: {filename}")
                to_import.append(file_path)

    logger.info(f"Datasets: {len(to_import)} to import, {skipped} skipped (core).")
    return to_import


def collect_charts_to_import(assets_root: str, tag: str) -> list:
    """
    Returns absolute paths of chart YAML files whose tags list contains
    exactly and only the given tag. Charts with any additional tag are skipped.
    """
    charts_dir = os.path.join(assets_root, "charts")
    if not os.path.isdir(charts_dir):
        logger.info("No charts/ directory found.")
        return []

    to_import = []
    skipped = 0

    for root, _, files in os.walk(charts_dir):
        for filename in files:
            if not filename.endswith(".yaml"):
                continue
            file_path = os.path.join(root, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            chart_tags = data.get("tags", [])
            if set(chart_tags) == {tag}:
                logger.info(f"  [ADD]  Chart with only tag '{tag}': {filename}")
                to_import.append(file_path)
            else:
                logger.info(f"  [SKIP] Chart skipped (tags={chart_tags}): {filename}")
                skipped += 1

    logger.info(f"Charts: {len(to_import)} to import, {skipped} skipped.")
    return to_import


def build_dataset_uuid_index(assets_root: str) -> dict:
    """
    Maps dataset uuid -> absolute file path for every dataset YAML under
    assets_root, regardless of whether it is a core (remote) dataset or not.
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
    Resolves each chart's dataset_uuid to its dataset YAML file (core or not),
    so it can be bundled into the same chart manifest.
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

    logger.info(f"Charts depend on {len(resolved)} dataset(s) (bundled into chart manifest).")
    if missing:
        logger.warning(f"{missing} chart(s) reference a dataset_uuid missing from the manifest.")

    return resolved


def copy_relative_files(files: list, src_root: str, dest_root: str):
    for file_path in files:
        rel_path = os.path.relpath(file_path, src_root)
        dest_path = os.path.join(dest_root, rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(file_path, dest_path)


def write_metadata_yaml(assets_root: str, dest_root: str, metadata_type: str = None):
    """
    Copies metadata.yaml into dest_root, overriding its 'type' field when
    metadata_type is given (the exported metadata.yaml is always "Dashboard").
    """
    metadata_path = os.path.join(assets_root, "metadata.yaml")
    if not os.path.isfile(metadata_path):
        logger.warning(f"metadata.yaml not found in {assets_root} — manifest will be incomplete.")
        return

    dest_path = os.path.join(dest_root, "metadata.yaml")
    if not metadata_type:
        shutil.copy2(metadata_path, dest_path)
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = yaml.safe_load(f)
    metadata["type"] = metadata_type
    with open(dest_path, "w", encoding="utf-8") as f:
        yaml.dump(metadata, f, sort_keys=False, allow_unicode=True)
    logger.info(f"metadata.yaml written to {dest_root} with type: {metadata_type}")


def copy_tags_file(assets_root: str, dest_root: str):
    src = os.path.join(assets_root, "tags.yaml")
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(dest_root, "tags.yaml"))


def copy_databases_folder(assets_root: str, dest_root: str):
    src = os.path.join(assets_root, "databases")
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(dest_root, "databases"))


def build_dataset_manifest(build_dir: str, assets_root: str, intermediate_dir: str, dataset_files: list) -> bool:
    if not dataset_files:
        logger.info("No datasets to import — manifests_dataset not created.")
        return False

    manifest_root = os.path.join(build_dir, DATASET_MANIFEST_DIRNAME)
    dest_root = os.path.join(manifest_root, intermediate_dir) if intermediate_dir else manifest_root
    os.makedirs(dest_root, exist_ok=True)

    write_metadata_yaml(assets_root, dest_root, metadata_type="SqlaTable")
    copy_tags_file(assets_root, dest_root)
    copy_databases_folder(assets_root, dest_root)
    copy_relative_files(dataset_files, assets_root, dest_root)

    logger.info(f"Dataset manifest ready: {dest_root} ({len(dataset_files)} dataset file(s))")
    return True


def build_charts_manifest(
    build_dir: str, assets_root: str, intermediate_dir: str, chart_files: list, chart_dataset_files: list
) -> bool:
    if not chart_files:
        logger.info("No charts to import — manifests_charts not created.")
        return False

    manifest_root = os.path.join(build_dir, CHARTS_MANIFEST_DIRNAME)
    dest_root = os.path.join(manifest_root, intermediate_dir) if intermediate_dir else manifest_root
    os.makedirs(dest_root, exist_ok=True)

    write_metadata_yaml(assets_root, dest_root, metadata_type="Slice")
    copy_tags_file(assets_root, dest_root)
    copy_databases_folder(assets_root, dest_root)
    copy_relative_files(chart_files + chart_dataset_files, assets_root, dest_root)

    logger.info(
        f"Charts manifest ready: {dest_root} "
        f"({len(chart_files)} chart file(s), {len(chart_dataset_files)} dependent dataset(s))"
    )
    return True


def main():
    if len(sys.argv) != 4:
        print("Usage: manifest_builder.py <TAG> <MANIFESTS_DIR> <BUILD_DIR>")
        print("Target Analytics DB credentials must be set as environment variables.")
        sys.exit(1)

    tag           = sys.argv[1]
    manifests_dir = sys.argv[2]
    build_dir     = sys.argv[3]

    # ── Core repo (public, no auth needed; owner/repo have defaults) ─────────
    github_owner  = os.environ.get("GITHUB_OWNER",  GITHUB_OWNER_DEFAULT)
    github_repo   = os.environ.get("GITHUB_REPO",   GITHUB_REPO_DEFAULT)

    # ── Target Analytics DB credentials, patched into every databases/*.yaml ─
    db_creds = {
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
    logger.info(f"--- BUILDING MANIFESTS (tag: {tag}) ---")

    # Wipe the whole build dir up front so a stale manifests_dataset/manifests_charts
    # from a previous run can never survive into this one and get imported.
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir, exist_ok=True)

    intermediate_dir = detect_intermediate_dir(manifests_dir)

    # ── Step 1: master copy, also the dashboards manifest (full, unfiltered) ─
    dashboards_root = os.path.join(build_dir, DASHBOARDS_MANIFEST_DIRNAME)
    copy_manifest_to_build(manifests_dir, dashboards_root)
    assets_root = os.path.join(dashboards_root, intermediate_dir) if intermediate_dir else dashboards_root

    deps_path = dependencies_file_path(manifests_dir)
    if os.path.isfile(deps_path):
        logger.info(f"Dependencies file found at {deps_path} — fetching shared assets from core repo.")
        core_paths = materialize_dependencies(deps_path, assets_root, github_owner, github_repo)
    else:
        logger.info(f"No dependencies file found at {deps_path} — building manifests from local assets only.")
        core_paths = set()
    patch_database_credentials(assets_root, db_creds)

    # ── Step 2: dataset manifest (exclude datasets already in core repo) ─────
    dataset_files = collect_datasets_to_import(assets_root, core_paths)
    build_dataset_manifest(build_dir, assets_root, intermediate_dir, dataset_files)

    # ── Step 3: charts manifest (only charts tagged exactly with TAG) ────────
    chart_files = collect_charts_to_import(assets_root, tag)
    dataset_uuid_index = build_dataset_uuid_index(assets_root)
    chart_dataset_files = resolve_chart_dataset_dependencies(chart_files, dataset_uuid_index)
    build_charts_manifest(build_dir, assets_root, intermediate_dir, chart_files, chart_dataset_files)

    logger.info(f"--- MANIFESTS READY FOR IMPORT (tag: {tag}): {build_dir} ---")


if __name__ == "__main__":
    main()
