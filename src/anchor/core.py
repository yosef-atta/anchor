"""Core domain logic for Anchor operations."""

import json
import re
from pathlib import Path
from typing import Any, Dict
from anchor.db import init_database
from anchor.templates import ANCHOR_BLOCK_START, ANCHOR_BLOCK_END, ANCHOR_FULL_BLOCK


def update_or_create_doc_file(file_path: Path) -> None:
    """
    Update or create a documentation file (AGENTS.md / CLAUDE.md)
    ensuring only the Anchor-managed block is replaced or added,
    leaving any other content untouched.
    """
    if not file_path.exists():
        file_path.write_text(ANCHOR_FULL_BLOCK, encoding="utf-8")
        return

    content = file_path.read_text(encoding="utf-8")
    
    # Pattern to match existing anchor block
    pattern = re.compile(
        rf"{re.escape(ANCHOR_BLOCK_START)}.*?{re.escape(ANCHOR_BLOCK_END)}",
        re.DOTALL,
    )
    
    if pattern.search(content):
        # Replace existing block
        new_content = pattern.sub(ANCHOR_FULL_BLOCK.strip(), content)
    else:
        # Append anchor block if not present
        if content.strip():
            new_content = f"{content.rstrip()}\n\n{ANCHOR_FULL_BLOCK}"
        else:
            new_content = ANCHOR_FULL_BLOCK

    file_path.write_text(new_content, encoding="utf-8")


def is_directory_existing_project(project_path: Path) -> bool:
    """Check if the directory contains files indicating an existing project."""
    ignored = {".git", ".anchor", "AGENTS.md", "CLAUDE.md", ".DS_Store", "Thumbs.db"}
    try:
        for item in project_path.iterdir():
            if item.name not in ignored:
                return True
    except FileNotFoundError:
        return False
    return False


def initialize_project(project_path: Path) -> Dict[str, Any]:
    """
    Initialize an Anchor project at the given path.
    Creates .anchor/anchor.db, AGENTS.md, CLAUDE.md, and initializes metadata.
    """
    project_path = project_path.resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    
    anchor_dir = project_path / ".anchor"
    db_path = anchor_dir / "anchor.db"
    
    is_existing = is_directory_existing_project(project_path)
    
    # Initialize SQLite database
    init_database(db_path, is_existing_project=is_existing)
    
    # Create or update AGENTS.md and CLAUDE.md
    update_or_create_doc_file(project_path / "AGENTS.md")
    update_or_create_doc_file(project_path / "CLAUDE.md")
        
    mcp_config = {
        "mcpServers": {
            "anchor": {
                "command": "anchor",
                "args": [
                    "mcp"
                ]
            }
        }
    }
    
    return {
        "project_path": str(project_path),
        "db_path": str(db_path),
        "is_existing": is_existing,
        "mcp_config": mcp_config,
    }
