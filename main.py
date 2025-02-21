from src.file_reader import FileReader, process_md, LOGGER
from src.settings import MD_DIR_PATH, PROCESSED_DIR_PATH, CHUNK_SIZE
from pathlib import Path


md_paths = list(Path(MD_DIR_PATH).iterdir())
if md_paths:
    try:
        for filepath in md_paths:
            file_suffix = filepath.suffix
            # Only process for markdown files in the directory
            if file_suffix != ".md":
                continue
            LOGGER.info(filepath)
            with open(filepath, encoding="utf-8") as f:
                md = f.read()
            processed_md = process_md(md)
            filename = filepath.name
            LOGGER.info(filename)
            processed_md_path = str(Path(PROCESSED_DIR_PATH).joinpath(filename))
            with open(processed_md_path, "w", encoding="UTF-8") as f:
                f.write(processed_md)

    except Exception:
        LOGGER.exception("Markdown document parsing failed")
        raise

    LOGGER.info("Parsing and saving MD files completed succesfully")
else:
    LOGGER.info("No MD files found")

nodes = FileReader(input_dir=PROCESSED_DIR_PATH).load_data()
