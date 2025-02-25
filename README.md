## Introduction
`md2chunks` is a Python project designed for context-enriched markdown chunking, particularly useful for Retrieval-Augmented Generation (RAG) tasks. It processes markdown files, splits them into manageable chunks, and enriches them with context to facilitate efficient information retrieval and processing.

## Features
- **Markdown Processing**: Converts markdown files to structured text.
- **Text Splitting**: Splits text into chunks based on token count, with special handling for URLs, decimals, and abbreviations.
- **Context Enrichment**: Adds context to each chunk to maintain the hierarchical structure of the original document.
- **Logging**: Provides detailed logging for debugging and monitoring.

## Setup

This environment is setup using UV. Board the UV train, life is easier.

1. [Install UV](https://docs.astral.sh/uv/getting-started/installation/#uninstallation)
2. Build Virtual Environment: `uv sync`
3. `source .venv/bin/activate`

Note: You can alternatively add the following alias to your .zshrc or .bashrc:
```
alias activate="source .venv/bin/activate"
```
That way, all you have to do is run: 
3. `activate`

## Usage

4. In `src/settings.py` enter your Markdown directory path in `MD_DIR_PATH` and add your markdown files inside it.
5. Create a folder to store processed markdown files (so that original files remain intact) and provide that path in the `PROCESSED_DIR_PATH` inside `src/settings.py`
Note: This is an intermediate file and is only useful for debugging purposes.
6. Run `python main.py`

Note: `main.py` only returns the chunks to a variable and quits the program. You are free to extend it your usecase.
Incase you want to visualise the chunks, refer to `visualisation.ipynb`. To look at the chunks run the notebook instead of step 5.
6. logs can be found inside the `logs` folder
7. Post use run `deactivate`

## Acknowledgements

The idea of TextNodes in `src/nodes.py` is inspired from [LlamaIndex](https://github.com/run-llama/llama_index)

## License
Please refer to [LICENSE](https://github.com/verloop/md2chunks/blob/master/LICENSE)

