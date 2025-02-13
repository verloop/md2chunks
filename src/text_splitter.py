import re
import traceback
from typing import List, Tuple

import tiktoken

from src import LOGGER
from src.settings import CHUNK_OVERLAP_BUFFER, CHUNK_SIZE, abbreviations
from src.settings import CHARACTER_SEPARATOR, PARAGRAPH_SEPARATOR, BREAK_SEPARATOR,tokenizer


class TextSplitter:
    """Class to split text into chunks of specified size, with special handling for specific cases
    like URLs, decimals, and abbreviations.

    Attributes:
        chunk_size (int): Maximum size of each chunk in terms of token count.
        paragraph_separator (List[str]): List of paragraph separators.
        character_separator (List[str]): List of character separators.
        tokenizer (str): Tokenizer to use for counting tokens and encoding.

    Methods:
        token_count(text): Returns the token count of the given text.
        special_case_handler(text, alter): Handles special cases in the text like URLs, decimals, and abbreviations.
        split_text(content, metadata_str, is_md): Splits the input text into chunks based on the configured chunk size.
    """

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        paragraph_separator: List[str] = PARAGRAPH_SEPARATOR,
        character_separator: List[str] = CHARACTER_SEPARATOR,
        tokenizer: str = tokenizer,
    ):
        """
        Initializes the SentenceSplitter with specified parameters.

        Args:
            chunk_size (int, optional): Maximum size of each chunk in terms of token count. Defaults to 256.
            paragraph_separator (List[str], optional): List of paragraph separators. Defaults to PARAGRAPH_SEPARATOR.
            character_separator (List[str], optional): List of character separators. Defaults to CHARACTER_SEPARATOR.
            tokenizer (str, optional): Tokenizer to use for counting tokens and encoding. Defaults to "gpt-3.5-turbo".
        """
        self.chunk_size = chunk_size
        self.paragraph_separator = paragraph_separator
        self.character_separator = character_separator

        self.special_case_handler_fn = [
            self._decimal_handler,
            self._url_handler,            
            self._abbreviation_handler,
        ]

        try:
            self.tokenizer = tiktoken.encoding_for_model(tokenizer)
        except Exception as e:
            except_info = traceback.format_exc()
            message = f"Tokenizer {tokenizer} not supported"
            LOGGER.error(event=message, exception=e, details=except_info)
            self.tokenizer = None

    def token_count(self, text: str) -> int:
        """
        Returns the token count of the given text.

        Args:
            text (str): Input text to count tokens for.

        Returns:
            int: Token count of the input text.
        """
        token_count = len(self.tokenizer.encode(text))
        return token_count

    def _abbreviation_handler(self, text: str, alter: bool) -> str:
        """Handles abbreviations in the text by replacing periods with a special marker.

        Args:
            text (str): Input text containing abbreviations.
            alter (bool): If True, replace periods with a special marker. If False, replace the special marker back with periods.

        Returns:
            str: Text with altered abbreviations.
        """
        if alter:
            for abbr in abbreviations:
                pattern = rf"\b{re.escape(abbr)}(?=\s|$)"
                replacement = abbr.replace(".", "*-*")
                text = re.sub(pattern, replacement, text)
        else:
            text = text.replace("*-*", ".")
        return text

    def _url_handler(self, text: str, alter: bool) -> str:
        """Handles URLs in the text by replacing periods with a special marker.

        Args:
            text (str): Input text containing URLs.
            alter (bool): If True, replace periods with a special marker. If False, replace the special marker back with periods.

        Returns:
            str: Text with altered URLs.
        """
        if alter:
            text = re.sub(
                r"[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
                lambda match: match.group().replace(".", "@-@"),
                text,
            )         
        else:
            text = text.replace("@-@", ".")
        return text

    def _decimal_handler(self, text: str, alter: bool) -> str:
        """Handles decimals in the text by replacing periods with a special marker.

        Args:
            text (str): Input text containing decimals.
            alter (bool): If True, replace periods with a special marker. If False, replace the special marker back with periods.

        Returns:
            str: Text with altered decimals.
        """
        if alter:
            text = re.sub(r"(?<=\d)\.(?=\d)", "#-#", text)
        else:
            text = text.replace("#-#", ".")
        return text

    def special_case_handler(self, text: str, alter: bool) -> str:
        """
        Handles special cases in the text like URLs, decimals, and abbreviations by applying
        the respective handlers.

        Args:
            text (str): Input text to handle special cases.
            alter (bool): If True, apply special case handlers to alter the text. If False, revert the alterations.

        Returns:
            str: Text with handled special cases.
        """
        text = self._abbreviation_handler(text, alter)
        text = self._decimal_handler(text, alter)
        text = self._url_handler(text, alter)
        return text

    def _merge(
        self, splits: List[Tuple[str, str]], chunk_size_limit: int
    ) -> List[Tuple[str, str]]:
        """
        Merges split texts into chunks without exceeding the effective chunk size.

        Called by character splits as that results in very small chunks of data. This method ensures
        that each chunk is within the buffer range of required chunk size. This is achieved by merging chunks

        Args:
            splits (List[Tuple[str, str]]): Previous context and split text
            chunk_size_limit (int): Effective size of each chunk in terms of token count.

        Returns:
            List[Tuple[str, str]]: Previous context and Merged chunks of text.
        """
        merged = False
        for idx, (context, chunk) in enumerate(splits):
            if idx == 0:
                continue

            prev_chunk_context = splits[idx - 1][0]
            prev_chunk = splits[idx - 1][1]
            prev_chunk_size = self.token_count(prev_chunk_context + prev_chunk)

            # If the header context is not the same, retain the context inside chunk
            if not prev_chunk_context == context:
                token_count = self.token_count(context + chunk)
                chunk = context + chunk
            else:
                token_count = self.token_count(chunk)

            # If the merged size of the chunks is lower than CHUNK_OVERLAP_BUFFER then merge
            if prev_chunk_size + token_count < int(
                chunk_size_limit * CHUNK_OVERLAP_BUFFER
            ):
                splits[idx - 1] = (prev_chunk_context, prev_chunk + chunk)
                splits.pop(idx)
                merged = True

        # Run until no more merge is possible
        if merged:
            splits = self._merge(splits, chunk_size_limit)

        return splits

    def _character_splits(
        self, context: str, content: str, chunk_size_limit: int, is_md: bool
    ) -> List[str]:
        """
        Splits text by characters and ensures no chunk exceeds the effective chunk size.

        Args:
            context (str): Previous header context (Used for markdown). Default is ""
            content (str): Input text to split.
            chunk_size_limit (int): Effective size of each chunk in terms of token count.
            is_md (bool): Whether the content is in markdown format.

        Returns:
            List[Tuple[str, str]]:  Previous context and split text.
        """
        chunks: List[Tuple[str, str]] = [(context, content)]
        for separator in self.character_separator:  # ["/n", ","]
            is_split_more = False
            char_splits = []
            for context, chunk in chunks:
                token_size = self.token_count(context + chunk)

                # If token size is greater than CHUNK_OVERLAP_BUFFER then split the paragraph
                if token_size > chunk_size_limit * CHUNK_OVERLAP_BUFFER:
                    chunk_splits = []
                    splits = chunk.split(separator)
                    len_splits = len(splits)
                    # Make sure to retain the context and the separator
                    for i, split in enumerate(splits):
                        if i != len_splits:
                            chunk_splits.append(context + split + separator)
                        else:
                            chunk_splits.append(context + split)
                    char_splits.extend(chunk_splits)
                    is_split_more = True
                else:
                    char_splits.append(context + chunk)

                # Process the new markdown chunks for appropriate header context assignment
                if is_md:
                    processed_splits = self._md_chunk_treatment(chunks=char_splits)
                else:
                    processed_splits = [("", split) for split in splits]

            if is_split_more:
                chunks: List[Tuple[str, str]] = self._merge(
                    processed_splits, chunk_size_limit
                )
            else:
                return processed_splits

        return chunks

    def _md_chunk_treatment(self, chunks: List[str]) -> List[Tuple[str, str]]:
        """
        Treats markdown chunks by placing context where required.

        Checks if the beginning of the chunk has context. If it does then it separates that context and returns with it.
        Else, it takes last context from previous chunk and returns with it. This ensures every new adjusted
        chunk has heading hierarcy context.

        Args:
            chunks (List[str]): List of markdown chunks.

        Returns:
            List[Tuple[str, str]]: Previous header contexts and Adjusted markdown chunks.
        """
        context = ""
        new_chunks: List[Tuple[str, str]] = []
        for chunk in chunks:
            matches = re.findall(r"(?s)#\s.+?\n\n(?!#)", chunk)
            if not matches:
                new_chunks.append((context, chunk))
            else:
                if re.match("^#.+?\n", chunk):
                    chunk = re.sub(r"(?s)^#\s.+?\n\n(?!#)", "", chunk)
                    new_chunks.append((matches[0], chunk))
                else:
                    new_chunks.append((context, chunk))
                context = matches[-1]

        return new_chunks

    def _paragraph_splits(
        self, content: str, is_md: bool
    ) -> List[Tuple[str, str, int]]:
        """
        Splits text by paragraphs and calculates token count for each paragraph. In case of markdown,
        separates/creates context for each chunk

        Args:
            content (str): Input text to split.
            is_md (bool): Whether the content is in markdown format.

        Returns:
            List[Tuple[str, str, int]]: Previous context, paragraph and its respective token count.
        """
        chunks: List[Tuple[str, str, int]] = []
        para_splits = content.split(self.paragraph_separator)
        if is_md:
            para_splits = [
                (
                    split.strip("\n") + self.paragraph_separator
                    if i != len(para_splits)
                    else split
                )
                for i, split in enumerate(para_splits)
            ]
            splits = self._md_chunk_treatment(chunks=para_splits)
        else:
            splits = [("", split.strip("/n")) for split in para_splits]
        for context, split in splits:
            token_count = self.token_count(context + split)
            chunks.append((context, split, token_count))
        return chunks

    def split_text(self, content: str, metadata_str: str, is_md: bool) -> List[str]:
        """
        Splits the input text into chunks based on the configured chunk size, with options for metadata
        and markdown handling.

        Args:
            content (str): The content to be split into chunks.
            metadata_str (str): Metadata string to consider when calculating effective chunk size.
            is_md (bool): Whether the content is in markdown format.

        Returns:
            List[str]: List of text chunks.
        """
        if content == "":
            return []

        if metadata_str is not None:
            # NOTE: extra 2 newline chars for formatting when prepending in query
            num_extra_tokens = self.token_count(metadata_str)
            chunk_size_limit = self.chunk_size - num_extra_tokens

            if chunk_size_limit <= 0:
                raise ValueError(
                    "Effective chunk size is non positive after considering metadata"
                )
        else:
            chunk_size_limit = self.chunk_size

        token_size = self.token_count(content)
        all_chunks: List[Tuple[str, str]] = []
        if token_size < chunk_size_limit:
            return [content]
        else:
            content = self.special_case_handler(content, alter=True)
            big_splits = content.split(BREAK_SEPARATOR)
            chunks = []
            for split in big_splits:
                chunks.extend(self._paragraph_splits(split.strip("\n"), is_md))
            for context, split, token_size in chunks:
                if token_size > chunk_size_limit * CHUNK_OVERLAP_BUFFER:
                    chunk_split: List[Tuple[str, str]] = self._character_splits(
                        context, split, chunk_size_limit, is_md
                    )
                    all_chunks.extend(chunk_split)
                else:
                    all_chunks.append((context, split))

        # Check if final chunks can be merged
        all_chunks = self._merge(all_chunks, chunk_size_limit)

        final_chunks = []
        for context, chunk in all_chunks:
            chunk = chunk.strip()
            # replace pipes with semicolon as table column separators
            context = context.replace("|", ";")
            chunk = chunk.replace("|", ";")
            if chunk != "":
                chunk = self.special_case_handler(chunk, alter=False)
                final_chunks.append(context + chunk)

        return final_chunks
