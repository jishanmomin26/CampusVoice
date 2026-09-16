"""Deterministic build-time spaCy model installer for CampusVoice.

Installs and verifies required spaCy language models (specifically 'en_core_web_sm')
during build and deployment phases without relying on runtime downloads.
"""

import argparse
import logging
import sys
import spacy
import spacy.cli
import spacy.util

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("install_spacy_model")

DEFAULT_MODEL = "en_core_web_sm"


def install_and_verify_model(model_name: str = DEFAULT_MODEL) -> bool:
    """Check if the target spaCy model is installed; if missing, install it and verify.

    Args:
        model_name: Name of the spaCy model package (default: 'en_core_web_sm').

    Returns:
        bool: True if model is available and loads successfully, False otherwise.
    """
    logger.info("Starting deterministic spaCy model installation/verification...")
    logger.info("Target model: '%s'", model_name)
    logger.info("Active Python prefix: %s", sys.prefix)

    is_installed = spacy.util.is_package(model_name)
    if is_installed:
        logger.info("spaCy model '%s' is already installed as a package.", model_name)
    else:
        logger.info(
            "spaCy model '%s' is missing. Downloading during build phase...",
            model_name,
        )
        try:
            spacy.cli.download(model_name)
            logger.info("Download completed for model '%s'.", model_name)
        except Exception as exc:
            logger.error("Failed to download spaCy model '%s': %s", model_name, exc)
            return False

    # Verification: Ensure the model can be loaded with the required configuration
    logger.info("Verifying that spaCy model '%s' loads and functions properly...", model_name)
    try:
        nlp = spacy.load(model_name, disable=["ner"])
        # Validate core preprocessing capabilities: tokenization and lemmatization
        doc = nlp("The practical sessions are informative.")
        tokens = [token.text for token in doc]
        lemmas = [token.lemma_ for token in doc]

        if not tokens or not lemmas:
            logger.error("Verification failed: tokenization/lemmatization produced empty output.")
            return False

        logger.info(
            "Successfully loaded and verified spaCy model '%s' (active pipes: %s).",
            model_name,
            nlp.pipe_names,
        )
        return True
    except Exception as exc:
        logger.error("Failed to load and verify spaCy model '%s': %s", model_name, exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministic build-time spaCy model installer for CampusVoice."
    )
    parser.add_argument(
        "--model",
        "-m",
        default=DEFAULT_MODEL,
        help=f"Target spaCy model to install and verify (default: {DEFAULT_MODEL}).",
    )
    args = parser.parse_args()

    success = install_and_verify_model(model_name=args.model)
    if not success:
        logger.error("spaCy model installation/verification failed.")
        sys.exit(1)

    logger.info("spaCy model installation/verification completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
