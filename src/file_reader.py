import copy
import os
import re
from pathlib import Path
from typing import Dict, List, Union

from bs4 import BeautifulSoup
from src.nodes import NodeRelationship, TextNode
from markdown import markdown
from markdownify import MarkdownConverter

from src import LOGGER
from src.settings import CHUNK_SIZE
from src.text_splitter import TextSplitter



def md(soup: BeautifulSoup) -> str:
    """Convert a BeautifulSoup object to a Markdown string.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object to convert.

    Returns:
        str: The Markdown equivalent of the provided BeautifulSoup object.
    """
    return MarkdownConverter(
        **{
            "heading_style": "ATX",
            "escape_misc": False,
        }
    ).convert_soup(soup)


class FileReader:
    """FileReader class for loading and parsing text/md files from a directory.

    This class can be used to load text data from a directory containing text files
    and markdown files. It parses the content of the files and creates
    :class:`llama_index.schema.TextNode` objects with the extracted text and metadata.

    Methods:
        load_data() -> List[TextNode]: Loads text data from the input directory
            and returns a list of :class:`llama_index.schema.TextNode` objects.
    """

    def __init__(
        self,
        input_dir: str,
    ):
        """Initialize FileReader with directory path, filesystem, tags, and document name-id mapping.

        Args:
            input_dir (str): Directory path to read files from.
        """
        self.inp_dir = input_dir
        self.text_splitter = TextSplitter(chunk_size=CHUNK_SIZE)
        

    def load_data(self) -> List[TextNode]:
        """Load data from files in the specified directory.

        Supports both `.txt` and `.md` file formats.

        Returns:
            List[TextNode]: List of text nodes extracted from files.
        """
        all_nodes = []
        dirlist = os.listdir(self.inp_dir)
        try:
            for filepath in dirlist:
                file_suffix = Path(filepath).suffix
                if file_suffix == ".txt":
                    all_nodes.extend(
                        self._load_file(
                            os.path.join(self.inp_dir, filepath), is_md=False
                        )
                    )
                elif file_suffix == ".md":
                    all_nodes.extend(
                        self._load_file(
                            os.path.join(self.inp_dir, filepath), is_md=True
                        )
                    )
                else:
                    LOGGER.info(f"Ignoring non md or non txt file: {filepath.stem}")
        except:
            LOGGER.exception("FileReader load_data failed")
            raise

        return all_nodes

    def _load_file(self, filepath: str, is_md: bool) -> List[TextNode]:
        """Load and process a single file.

        Args:
            filepath (str): Path of the file to load.
            is_md (bool): Flag indicating if the file is a Markdown file.

        Returns:
            List[TextNode]: List of text nodes extracted from the file.
        """

        doc_name = Path(filepath).stem
        doc_type = Path(filepath).suffix
        doc_metadata = {
            "doc_name": doc_name,
            "doc_type": doc_type,
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": 1.4
        }

        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        if is_md:
            content = self._parse_md(content=content, doc_name=doc_metadata["doc_name"])

        source_node = TextNode(text=content, metadata=doc_metadata)
        # metadata_str is kept empty for now as we do not inject metadata into the text chunk
        text_splits = self.text_splitter.split_text(
            content=content, metadata_str="", is_md=is_md
        )
        nodes: List[TextNode] = []
        for split in text_splits:
            node = TextNode(
                text=split,
                metadata=doc_metadata,
                relationships={
                    NodeRelationship.SOURCE: source_node.as_related_node_info()
                },
            )
            nodes.append(node)

        # Add prev/next relationships
        for i, node in enumerate(nodes):
            if i > 0:
                node.relationships[NodeRelationship.PREVIOUS] = nodes[
                    i - 1
                ].as_related_node_info()
            if i < len(nodes) - 1:
                node.relationships[NodeRelationship.NEXT] = nodes[
                    i + 1
                ].as_related_node_info()

        return nodes

    def _parse_md(self, content: str, doc_name: str = "") -> str:
        """Parse Markdown content, clean it, and convert to structured text.

        The markdown file is first given a heading from its given document name (if it doesn't already have it).
        Then code snippets, images are removed and tables are parsed into the following format:
        Eg: column1: el-1 | column2: el-2 | column3: el-3\ncolumn1: el-4 | column2: el-5 | column3: el-6\n
        Then we use the headings within the markdown file to create a hierarchy of headings and use that as context
        and replace it at every spot where a heading (h1,h2,h3,h4) is present. This re-structured markdown is returned

        Args:
            content (str): Markdown content.
            doc_name (str, optional): Document name. Defaults to "".

        Returns:
            str: Structured text extracted from Markdown.
        """
        heading = re.match("^#.+?\n", content)
        heading_tags = ["h1", "h2", "h3", "h4"]
        if not heading:
            # A heading before any text is required for hierarchy extraction to work
            if doc_name:
                content = f"# {doc_name}\n\n" + content
            else:
                content = "# Context\n\n" + content

        html = markdown(content, extensions=["tables"])

        # remove code snippets
        html = re.sub(r"<pre>(.*?)</pre>", " ", html)
        html = re.sub(r"<code>(.*?)</code >", " ", html)
        # remove images
        html = re.sub(r"!{1}\[\[(.*)\]\]", "", html)

        # extract text
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            text = ""
            table_head = table.find("thead")
            headers = [el.text.strip() for el in table_head.find_all("th")]
            table_body = table.find("tbody")
            for row in table_body.find_all("tr"):
                elements = row.find_all("td")
                for header, element in zip(headers, elements):
                    text += f"{header}: {element.text.strip()} | "
                text += "\n"
            text += "\n\n"
            table.replace_with(text)

        h1s = soup.find_all("h1")
        for h1 in h1s:
            prev_sibling = "h1"
            h2, h3 = None, None
            for sibling in h1.next_siblings:
                if sibling.text == "\n":
                    continue
                elif sibling.name == "h1":
                    prev_sibling = "h1"
                    break
                elif sibling.name == "h2":
                    h2 = copy.copy(sibling)
                    if prev_sibling != "h1" and prev_sibling != "h2":
                        sibling.insert_before(copy.copy(h1), "\n")
                    prev_sibling = "h2"
                elif sibling.name == "h3":
                    h3 = copy.copy(sibling)
                    if prev_sibling != "h2" and prev_sibling != "h3":
                        if h2:
                            sibling.insert_before(
                                copy.copy(h1),
                                "\n",
                                copy.copy(h2),
                                "\n",
                            )
                        else:
                            sibling.insert_before(copy.copy(h1), "\n")
                    prev_sibling = "h3"
                elif sibling.name == "h4":
                    if prev_sibling != "h3" and prev_sibling != "h4":
                        if h2 and h3:
                            sibling.insert_before(
                                copy.copy(h1),
                                "\n",
                                copy.copy(h2),
                                "\n",
                                copy.copy(h3),
                                "\n",
                            )
                        elif h2:
                            sibling.insert_before(
                                copy.copy(h1), "\n", copy.copy(h2), "\n"
                            )
                        elif h3:
                            sibling.insert_before(
                                copy.copy(h1), "\n", copy.copy(h3), "\n"
                            )
                        else:
                            sibling.insert_before(copy.copy(h1), "\n")
                    prev_sibling = "h4"
                else:
                    # Add an extra newline between headings and rest of text
                    if prev_sibling in heading_tags:
                        sibling.insert_before("\n")
                    prev_sibling = "other"

        text = md(soup)
        # Replace the extra newline between the subheadings
        final_text = re.sub(
            r"#\s.+?\n{2,3}#",
            lambda match: match.group().replace("\n\n\n", "\n").replace("\n\n", "\n"),
            text,
        )
        final_text = re.sub(
            r"#\s.+?\n{3,4}",
            lambda match: match.group()
            .replace("\n\n\n\n", "\n\n")
            .replace("\n\n\n", "\n\n"),
            final_text,
        )

        return final_text


if __name__ == "__main__":
    import tiktoken

    md_dir = "/home/asha/verloop/ai_assist_chunking/train_docs"
    md_files = os.listdir(md_dir)
    processed_dir = os.path.join(md_dir, "processed")
    if not os.path.exists(md_dir):
        os.mkdir(md_dir)

    for md_file in md_files:
        md_filepath = os.path.join(md_dir, md_file)
        processed_filepath = os.path.join(processed_dir, md_file)
        if os.path.isdir(md_filepath):
            continue
        with open(md_filepath, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        html = markdown(content, extensions=["tables"])
        # remove code snippets
        html = re.sub(r"<pre>(.*?)</pre>", " ", html)
        html = re.sub(r"<code>(.*?)</code >", " ", html)
        # remove images
        html = re.sub(r"!{1}\[\[(.*)\]\]", "", html)
        # remove additional newlines
        html = re.sub(">\n{1,}<", "><", html)

        # extract text
        soup = BeautifulSoup(html, "html.parser")

        new_content = md(soup)
        with open(processed_filepath, "w", encoding="UTF-8") as f:
            f.write(new_content)

    file_reader = FileReader(
        input_dir=processed_dir
    )
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    nodes = file_reader.load_data()
    prev_metadata = ""
    start = True
    for node in nodes:
        inside_limit = False
        metadata_str: str = "\n".join(
            [f"{key}: {value}" for key, value in node.metadata.items()]
        )
        token_length = len(tokenizer.encode(node.text))
        if token_length < ((CHUNK_SIZE - len(tokenizer.encode(metadata_str))) * 1.4):
            inside_limit = True
        if prev_metadata == node.metadata or start:
            print(node.metadata)
            print(f"Length of tokens: {token_length}")
            print(f"Is chunk inside token limit?: {inside_limit}")
            print(node.text)
            print(100 * "-")
        else:
            print(100 * "=")
            print(100 * "=")
            print(node.metadata)
            print(f"Length of tokens: {token_length}")
            print(f"Is chunk inside token limit?: {inside_limit}")
            print(node.text)
            print(100 * "-")
        start = False
        prev_metadata = node.metadata
