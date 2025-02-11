

# Text Splitter configurations

CHUNK_SIZE = 256
CHUNK_OVERLAP_BUFFER = (
    1.4  # Note: This buffer defines the upper limit and has to be above 1
)
abbreviations = ["eg.", "i.e.", "vs.", "Dr.", "Mr.", "Ms."]
CHARACTER_SEPARATOR = ["\n\n", "\n", ".", " "]
PARAGRAPH_SEPARATOR = "\n\n\n"
BREAK_SEPARATOR = "\n---\n"
tokenizer = "gpt-3.5-turbo"
