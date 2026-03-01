"""Ingestion pipeline: parse tags.md and routines.md into indexes."""

from ingestion.tag_index import TagEntry, TagIndex, load_tag_index, load_tag_index_from_json

__all__ = ["TagEntry", "TagIndex", "load_tag_index", "load_tag_index_from_json"]
