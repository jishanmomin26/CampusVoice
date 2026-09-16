"""Deterministic build-time NLTK resource installer for CampusVoice.

Installs required NLTK resources (specifically 'stopwords') during build
and deployment phases without relying on runtime downloads.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
import nltk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("install_nltk_resources")


def install_resources(resources: list[str] | None = None) -> bool:
    """Download required NLTK resources deterministically to NLTK search paths.

    Args:
        resources: Optional list of NLTK resource identifiers. Defaults to ['stopwords'].

    Returns:
        bool: True if all resources are downloaded and verified successfully.
    """
    if not resources:
        resources = ["stopwords"]

    # Identify candidate installation directories
    backend_dir = Path(__file__).resolve().parent.parent
    repo_root = backend_dir.parent
    project_nltk_data = repo_root / "nltk_data"
    venv_nltk_data = Path(sys.prefix) / "nltk_data"

    logger.info("Starting deterministic NLTK resource installation...")
    logger.info("Target resources: %s", resources)
    logger.info("Active Python prefix: %s", sys.prefix)

    # Ensure search paths include venv and project directories
    for path_candidate in (venv_nltk_data, project_nltk_data):
        str_p = str(path_candidate)
        if str_p not in nltk.data.path:
            nltk.data.path.insert(0, str_p)

    all_success = True
    for res in resources:
        logger.info("Installing NLTK resource '%s'...", res)
        download_success = False

        # 1. Attempt download into active Python virtual environment
        try:
            logger.info("Attempting download to virtualenv directory: %s", venv_nltk_data)
            nltk.download(res, download_dir=str(venv_nltk_data), quiet=False)
            download_success = True
        except Exception as exc:
            logger.warning(
                "Direct download to %s failed: %s. Attempting fallback locations.",
                venv_nltk_data,
                exc,
            )

        # 2. Also download into project-local nltk_data directory if running in repo root
        try:
            logger.info("Ensuring resource in project directory: %s", project_nltk_data)
            nltk.download(res, download_dir=str(project_nltk_data), quiet=False)
            download_success = True
        except Exception as exc:
            logger.warning(
                "Direct download to %s failed: %s.", project_nltk_data, exc
            )

        # 3. Fallback to default NLTK download location
        if not download_success:
            try:
                logger.info("Attempting download to default NLTK location...")
                nltk.download(res, quiet=False)
                download_success = True
            except Exception as exc:
                logger.error("Failed to download resource '%s': %s", res, exc)
                all_success = False
                continue

        # 4. Verification
        corpus_path = (
            f"corpora/{res}"
            if not res.startswith("corpora/") and not res.startswith("tokenizers/")
            else res
        )
        try:
            found_path = nltk.data.find(corpus_path)
            logger.info(
                "Verified NLTK resource '%s' successfully found at: %s",
                res,
                found_path,
            )
        except (LookupError, OSError) as err:
            logger.error("Verification failed for resource '%s': %s", res, err)
            all_success = False

    return all_success


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministic build-time NLTK resource installer for CampusVoice."
    )
    parser.add_argument(
        "--resource",
        "-r",
        action="append",
        dest="resources",
        help="Specific NLTK resource to install (default: stopwords). Can be specified multiple times.",
    )
    args = parser.parse_args()

    success = install_resources(resources=args.resources)
    if not success:
        logger.error("NLTK resource installation failed.")
        sys.exit(1)

    logger.info("NLTK resource installation completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
