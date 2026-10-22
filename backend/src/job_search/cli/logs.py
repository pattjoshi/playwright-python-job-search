"""Log setup shared by the commands."""

import logging

NOISY_LOGGERS = ("httpx", "openai", "pdfminer", "uvicorn.access")


def setup_logging(level: int = logging.INFO, datefmt: str = "%H:%M:%S", handlers: list | None = None) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)-7s %(message)s", datefmt=datefmt, handlers=handlers)
    # Keep third-party HTTP chatter out of normal output.
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
