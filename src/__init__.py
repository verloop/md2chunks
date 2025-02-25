import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path


def setup_logging(
    log_file: str = "app.log",
    max_size: int = 1024 * 1024,  # 1MB
    backup_count: int = 5,
):
    try:
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Rotating File Handler
        file_handler = RotatingFileHandler(
            log_dir / log_file, maxBytes=max_size, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    except Exception as e:
        print(f"Error setting up logging: {str(e)}")
        raise


LOGGER = setup_logging()
