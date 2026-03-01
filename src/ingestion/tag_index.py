"""Parse tags.md and build TagIndex. Deterministic, no LLM."""

import json
from pathlib import Path

from pydantic import BaseModel, Field


class TagEntry(BaseModel):
    """Single tag: type, description, category. Name is the key in TagIndex."""

    type: str = Field(description="PLC type: BOOL, INT, DINT, TIMER, etc.")
    description: str = Field(description="Human-readable description of the tag.")
    category: str = Field(
        description="Section in tags.md: Inputs, Outputs, Internal State, Timers, Counters."
    )


class TagIndex(BaseModel):
    """
    Map tag_name -> { type, description, category }.
    No embeddings; exact names only.
    """

    root: dict[str, TagEntry] = Field(default_factory=dict, alias="tags")

    model_config = {"populate_by_name": True}

    def __getitem__(self, tag_name: str) -> TagEntry:
        return self.root[tag_name]

    def get(self, tag_name: str, default: TagEntry | None = None) -> TagEntry | None:
        return self.root.get(tag_name, default)

    def __contains__(self, tag_name: str) -> bool:
        return tag_name in self.root

    def __len__(self) -> int:
        return len(self.root)

    def keys(self):
        return self.root.keys()

    def items(self):
        return self.root.items()


# Section headers in tags.md that contain tag tables (exclude "Fault Codes").
TAG_CATEGORIES = ("Inputs", "Outputs", "Internal State", "Timers", "Counters")


def _parse_table_row(line: str) -> tuple[str, str, str] | None:
    """Parse a markdown table row into (tag_name, type, description). Returns None if not a data row."""
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        return None
    parts = [p.strip() for p in line.split("|")]
    # parts[0] and parts[-1] are empty; we want columns 1, 2, 3
    if len(parts) < 4:
        return None
    tag_name, type_val, description = parts[1], parts[2], parts[3]
    if not tag_name or tag_name == "Tag Name" or tag_name == "----------":
        return None
    return (tag_name, type_val, description)


def load_tag_index(path: Path | str) -> TagIndex:
    """
    Parse tags.md and build TagIndex.
    Expects sections ## Inputs, ## Outputs, etc. with markdown tables.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    built: dict[str, TagEntry] = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("## "):
            category = line.replace("##", "").strip()
            if category not in TAG_CATEGORIES:
                i += 1
                continue
            i += 1
            # Skip blank line and table header + separator
            while i < len(lines):
                row = lines[i]
                if not row.strip():
                    i += 1
                    continue
                if "|" in row and "Tag Name" in row:
                    i += 1
                    if i < len(lines) and "---" in lines[i]:
                        i += 1
                    break
                i += 1
            while i < len(lines):
                row = lines[i]
                parsed = _parse_table_row(row)
                if parsed is None:
                    if row.strip().startswith("|") and "---" not in row and "Fault_Code" not in row:
                        i += 1
                        continue
                    break
                tag_name, type_val, description = parsed
                built[tag_name] = TagEntry(
                    type=type_val,
                    description=description,
                    category=category,
                )
                i += 1
            continue
        i += 1

    return TagIndex(tags=built)


def load_tag_index_from_json(path: Path | str) -> TagIndex:
    """Load TagIndex from a JSON file (e.g. data/tag_index.json from run_ingestion)."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return TagIndex.model_validate(data)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    idx = load_tag_index(project_root / "docs" / "tags.md")
    out_dir = project_root / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "tag_index.json"
    out_path.write_text(json.dumps(idx.model_dump(by_alias=True), indent=2))
    print(f"Saved {len(idx)} tags to {out_path}")
