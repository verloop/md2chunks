from typing import Dict, Union


class NodeRelationship:
    SOURCE = "source"
    PREVIOUS = "previous"
    NEXT = "next"


class TextNode:
    def __init__(
        self,
        text: str,
        metadata: Dict[str, Union[str, int, float]],
        relationships: Dict[str, "TextNode"] = None,
    ):
        self.text = text
        self.metadata = metadata
        self.relationships = relationships if relationships else {}

    def as_related_node_info(self):
        return {
            "text": self.text,
            "metadata": self.metadata,
        }
