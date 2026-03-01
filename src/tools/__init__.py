"""Tools for retrieval and block extraction."""

from tools.call_graph_builder import MainCalleesContext, build_main_callees
from tools.tags_lookup import tags_lookup
from tools.deduplicate_blocks import deduplicate_blocks

# grep imports agents; keep it on grep submodule to avoid circular import
__all__ = [
    "MainCalleesContext",
    "build_main_callees",
    "tags_lookup",
    "deduplicate_blocks",
]
