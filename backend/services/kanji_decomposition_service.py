
from pathlib import Path
import re


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "cjkvi-ids"
    / "ids.txt"
)


# IDS operators and their number of children.
IDS_OPERATORS = {
    "⿰": 2,  # Left + right
    "⿱": 2,  # Above + below
    "⿲": 3,  # Left + middle + right
    "⿳": 3,  # Above + middle + below
    "⿴": 2,  # Full enclosure
    "⿵": 2,  # Surround from above
    "⿶": 2,  # Surround from below
    "⿷": 2,  # Surround from left
    "⿸": 2,  # Surround from upper-left
    "⿹": 2,  # Surround from upper-right
    "⿺": 2,  # Surround from lower-left
    "⿻": 2,  # Overlapping components
}


# --------------------------------------------------
# IDS Parser
# --------------------------------------------------

class IDSParser:
    """Parse Ideographic Description Sequences."""

    def parse(self, expression: str) -> dict:
        """
        Convert an IDS expression into a component tree.

        Example:
            ⿰亻木

        Result:
            {
                "character": None,
                "operator": "⿰",
                "components": [
                    {"character": "亻", ...},
                    {"character": "木", ...}
                ]
            }
        """

        expression = expression.strip()

        # Remove regional annotations such as [G], [TJK], etc.
        expression = re.sub(
            r"\[[A-Za-z]+\]",
            "",
            expression,
        )

        if not expression:
            raise ValueError("Empty IDS expression.")

        tokens = list(expression)
        position = 0

        def parse_node() -> dict:
            nonlocal position

            if position >= len(tokens):
                raise ValueError(
                    "Unexpected end of IDS expression."
                )

            token = tokens[position]
            position += 1

            if token in IDS_OPERATORS:

                child_count = IDS_OPERATORS[token]

                components = [
                    parse_node()
                    for _ in range(child_count)
                ]

                return {
                    "character": None,
                    "operator": token,
                    "components": components,
                }

            # Reject unrecognized IDS operators instead of
            # silently treating them as ordinary components.
            if 0x2FF0 <= ord(token) <= 0x2FFF:
                raise ValueError(
                    f"Unsupported IDS operator: {token}"
                )

            return {
                "character": token,
                "operator": None,
                "components": [],
            }

        tree = parse_node()

        if position != len(tokens):
            raise ValueError(
                f"Unexpected characters remaining in IDS expression: "
                f"{''.join(tokens[position:])}"
            )

        return tree


# --------------------------------------------------
# Kanji Decomposition Service
# --------------------------------------------------

class KanjiDecompositionService:
    """
    Load CJKVI IDS data and retrieve kanji decompositions.

    Supports:
    - Direct decomposition
    - Nested component expansion
    - Regional annotations
    - Unknown or indivisible components
    """

    def __init__(
        self,
        data_path: str | Path = DEFAULT_DATA_PATH,
    ):
        self.data_path = Path(data_path)

        self.entries = {}

        self.parser = IDSParser()

        self.load_dataset()

    # --------------------------------------------------
    # Dataset loading
    # --------------------------------------------------

    def load_dataset(self) -> None:
        """Load character decompositions from ids.txt."""

        if not self.data_path.exists():
            raise FileNotFoundError(
                f"CJKVI IDS dataset not found: {self.data_path}"
            )

        self.entries.clear()

        with self.data_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            for line_number, line in enumerate(file, start=1):

                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                parts = line.split()

                # Expected format:
                # Unicode codepoint, character, IDS expression
                if len(parts) < 3:
                    continue

                unicode_codepoint = parts[0]
                character = parts[1]
                expression = parts[2]

                if not unicode_codepoint.startswith("U+"):
                    continue

                # Keep the first decomposition for each character.
                # Alternative regional forms are not merged.
                if character not in self.entries:

                    self.entries[character] = {
                        "unicode": unicode_codepoint,
                        "character": character,
                        "expression": expression,
                        "line_number": line_number,
                    }

        print(
            f"Loaded {len(self.entries):,} IDS entries "
            f"from {self.data_path.name}"
        )

    # --------------------------------------------------
    # Direct decomposition
    # --------------------------------------------------

    def get_direct_decomposition(
        self,
        character: str,
    ) -> dict | None:
        """Retrieve the direct decomposition of a kanji."""

        entry = self.entries.get(character)

        if entry is None:
            return None

        expression = entry["expression"]

        tree = self.parser.parse(expression)

        tree["character"] = character
        tree["unicode"] = entry["unicode"]
        tree["expression"] = expression

        return tree

    # --------------------------------------------------
    # Recursive decomposition
    # --------------------------------------------------

    def _expand_component(
        self,
        node: dict,
        depth: int,
        max_depth: int,
        visited: set[str],
    ) -> dict:
        """
        Recursively expand components when their own
        IDS decomposition is available.
        """

        # Already a structural node.
        if node["operator"] is not None:

            node["components"] = [
                self._expand_component(
                    component,
                    depth,
                    max_depth,
                    visited,
                )
                for component in node["components"]
            ]

            return node

        character = node["character"]

        # Stop recursion when the maximum depth is reached.
        if depth >= max_depth:
            return node

        # Prevent circular decomposition.
        if character in visited:
            return node

        entry = self.entries.get(character)

        if entry is None:
            return node

        expression = entry["expression"]

        # A self-reference means this is an indivisible
        # component in the available dataset.
        if expression == character:
            return node

        expanded = self.parser.parse(expression)

        expanded["character"] = character
        expanded["unicode"] = entry["unicode"]
        expanded["expression"] = expression

        next_visited = visited | {character}

        expanded["components"] = [
            self._expand_component(
                component,
                depth + 1,
                max_depth,
                next_visited,
            )
            for component in expanded["components"]
        ]

        return expanded

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def get_decomposition(
        self,
        character: str,
        recursive: bool = True,
        max_depth: int = 3,
    ) -> dict | None:
        """
        Retrieve a kanji decomposition.

        Args:
            character: Kanji to inspect.
            recursive: Whether to expand nested components.
            max_depth: Maximum component expansion depth.

        Returns:
            Structured decomposition tree or None.
        """

        if len(character) != 1:
            raise ValueError(
                "Please provide exactly one character."
            )

        if max_depth < 0:
            raise ValueError(
                "max_depth cannot be negative."
            )

        tree = self.get_direct_decomposition(character)

        if tree is None:
            return None

        if not recursive:
            return tree

        visited = {character}

        tree["components"] = [
            self._expand_component(
                component,
                depth=1,
                max_depth=max_depth,
                visited=visited,
            )
            for component in tree["components"]
        ]

        return tree


# --------------------------------------------------
# Default service instance
# --------------------------------------------------

_default_service = None


def get_kanji_decomposition(
    character: str,
    recursive: bool = True,
    max_depth: int = 3,
) -> dict | None:
    """
    Convenient function for retrieving kanji decomposition.

    The dataset is loaded only once per Python process.
    """

    global _default_service

    if _default_service is None:
        _default_service = KanjiDecompositionService()

    return _default_service.get_decomposition(
        character=character,
        recursive=recursive,
        max_depth=max_depth,
    )
