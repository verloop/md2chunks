from typing import List
import pytest
from src.text_splitter import TextSplitter

def test_sentence_splitter_initialization():
    splitter = TextSplitter()
    assert splitter.chunk_size == 256
    assert splitter.paragraph_separator == "\n\n\n"
    assert splitter.character_separator == ["\n\n", "\n", ".", " "]

def test_token_counting():
    splitter = TextSplitter()
    text = "Hello world"
    assert splitter.token_count(text) > 0

def test_special_case_handlers():
    splitter = TextSplitter()
    
    # Test URL handling
    url_text = "Check out https://example.com/path"
    processed = splitter.special_case_handler(url_text, True)
    assert "@-@" in processed
    restored = splitter.special_case_handler(processed, False)
    assert restored == url_text
    
    # Test decimal handling
    decimal_text = "The value is 3.14159"
    processed = splitter.special_case_handler(decimal_text, True)
    assert "#-#" in processed
    restored = splitter.special_case_handler(processed, False)
    assert restored == decimal_text

def test_basic_text_splitting():
    splitter = TextSplitter(chunk_size=50)
    text = """This is a long paragraph that should be split into multiple chunks.
    It contains multiple sentences and should be handled appropriately by the splitter.
    Let's see how it performs with this input.
    This is a long paragraph that should be split into multiple chunks.
    It contains multiple sentences and should be handled appropriately by the splitter.
    Let's see how it performs with this input.
    """
    
    chunks = splitter.split_text(text, None, False)
    assert isinstance(chunks, list)
    assert len(chunks) > 1
    
def test_markdown_splitting():
    splitter = TextSplitter(chunk_size=50)
    md_text = """# Heading 1
    
    This is some content under heading 1.
    
    ## Heading 2
    
    This is content under heading 2."""
    
    chunks = splitter.split_text(md_text, None, True)
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert "# Heading" in chunks[0]

def test_with_metadata():
    splitter = TextSplitter(chunk_size=50)
    text = "This is sample content"
    metadata = "Source: test document"
    
    chunks = splitter.split_text(text, metadata, False)
    assert isinstance(chunks, list)
    assert len(chunks) > 0

def test_edge_cases():
    splitter = TextSplitter()
    
    # Test empty string
    assert splitter.split_text("", None, False) == []
    
    # Test very long text
    long_text = "word " * 1000
    chunks = splitter.split_text(long_text, None, False)
    assert isinstance(chunks, list)
    assert len(chunks) > 1

if __name__ == "__main__":
    pytest.main([__file__])