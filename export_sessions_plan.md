# Plan: OpenCode Session Exporter

## Goal

Export OpenCode sessions to human-readable Markdown files, with both a CLI tool and a web UI.

## Two Interfaces

1. **CLI** — Import and use as Python module for batch export
2. **Web UI** — Standalone local web app for interactive use

---

# Project Structure

```
opencode_session_exporter/
├── app.py                 # FastAPI server (run with: python app.py)
├── exporter.py            # Shared export logic (CLI module)
├── requirements.txt       # fastapi, uvicorn, pydantic
├── test_app.py            # FastAPI endpoint tests
├── test_exporter.py       # Exporter function tests
├── static/
│   ├── index.html         # Main UI
│   ├── styles.css         # Styling
│   └── app.js             # Frontend interactivity
└── export/                # Output directory for exported Markdown files
```

---

# Part 1: CLI Module (exporter.py)

## Implementation

### Functions to Implement

```python
# Check if opencode CLI is available
def check_opencode_available() -> bool:
    """Run 'opencode --version' to verify opencode is installed."""

# List all sessions (uses JSON output from opencode)
def list_sessions(project_dir: str = None) -> List[SessionInfo]:
    """Run 'opencode session list --format json' and parse results."""

# Export a single session to dict
def export_session(session_id: str, project_dir: str = None) -> Optional[dict]:
    """Run 'opencode export [session_id]' and parse JSON output."""

# Convert session data to Markdown
def convert_to_markdown(data: dict) -> str:
    """Convert session data to human-readable Markdown format."""

# Save Markdown to file
def save_markdown(content: str, title: str, updated: str, output_dir: str) -> str:
    """Save Markdown content to file, return filename."""

# Convenience function for single session export
def export_single_session(session_id: str, output_dir: str = ".") -> Optional[str]:
    """Export one session and return filename."""
```

### Data Structures

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SessionInfo:
    id: str
    title: str
    updated: str  # YYYY-MM-DD HH:MM
    directory: str

@dataclass
class Message:
    role: str      # "user" or "assistant"
    text: str
    reasoning: List[str]
    tool_calls: List[str]
```

### Markdown Format

For each message in `data["messages"]`:

- If `role == "user"`:
  - Extract all parts where `type == "text"`
  - Format as `## Human\n\n[text content]\n\n---\n\n`
- If `role == "assistant"`:
  - Extract text parts (type == "text"), join with `\n\n`
  - Extract reasoning parts (type == "reasoning"), format as collapsed block:
    ```html
    <details>
    <summary>Reasoning</summary>

    > reasoning text here

    </details>
    ```
  - Extract tool call parts (type == "tool"), format as `Tool calls: [tool name]`
  - Format as `## AI\n\n[text]\n\n[reasoning]\n\n[tool summary]\n\n---\n\n`

### File Naming

1. Sanitize title: remove special chars, replace spaces with hyphens
2. Filename: `{date}_{time}_{sanitized_title}.md` (e.g., `2026-04-21_16-15_Session-Title.md`)

### YAML Frontmatter

```markdown
---
title: "{original_title}"
date: "{updated}"
directory: "{directory}"
session_id: "{session_id}"
---

# {original_title}

**Date:** {updated}
**Directory:** {directory}

---
```

### Error Handling

- If `opencode` command not found: return False/empty list/None
- If `opencode session list` returns non-zero: return empty list
- If JSON parse fails: return None
- If export times out (120s): return None
- Clean up temp files on failure

---

# Part 2: Web UI (app.py)

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla HTML/CSS/JS
- **Communication**: JSON API via fetch

## API Endpoints

### GET /

Return `static/index.html`.

### GET /api/sessions?project_path=/path/to/project

List all sessions. Uses `opencode session list --format json`.

**Response:**
```json
{
  "sessions": [
    {
      "id": "ses_xxx",
      "title": "Session Title",
      "updated": "2026-04-21 16:15",
      "directory": "/path/to/project"
    }
  ]
}
```

### GET /api/sessions/{session_id}?project_path=/path/to/project

Get full session details.

**Response:**
```json
{
  "id": "ses_xxx",
  "title": "Session Title",
  "updated": "2026-04-21 16:15",
  "directory": "/path/to/project",
  "messages": [...]
}
```

### POST /api/export

Export selected sessions to Markdown files.

**Request:**
```json
{
  "session_ids": ["ses_xxx", "ses_yyy"],
  "project_path": "/path/to/project"
}
```

**Response:**
```json
{
  "exported": ["session-title_2026-04-21.md"],
  "failed": []
}
```

### GET /api/directories?path=/path/to/parent

List subdirectories in a path (for project picker UI).

**Response:**
```json
{
  "directories": ["project1", "project2"],
  "exists": true
}
```

## UI Features

- Path input with dropdown for directory selection
- Search/filter sessions by title
- Checkbox selection for multiple sessions
- Preview modal showing full conversation
- Export selected sessions to Markdown
- Toast notifications for success/error feedback

### Main Page Layout

```
┌─────────────────────────────────────────────────────────┐
│ OpenCode Session Exporter                              │
├─────────────────────────────────────────────────────────┤
│ [path input with dropdown]  [search input]             │
├─────────────────────────────────────────────────────────┤
│ □ │ Title            │ Date       │ Directory          │
│───│─────────────────│────────────│────────────────────│
│ ☑ │ Session 1      │ 2026-04-21│ /path/to/project   │
│ □ │ Session 2      │ 2026-04-20│ /path/to/project   │
├─────────────────────────────────────────────────────────┤
│  [Preview]  [Export Selected (1)]                      │
└─────────────────────────────────────────────────────────┘
```

### Preview Modal

```
┌─────────────────────────────────────────────────────────┐
│ Session Title                              [✕ Close]   │
├─────────────────────────────────────────────────────────┤
│ Date: 2026-04-21 16:15                                 │
│ Directory: /path/to/project                            │
├─────────────────────────────────────────────────────────┤
│ ## Human                                              │
│ User message here...                                   │
│ ─────────────────────────────────────────────────     │
│ ## AI                                                 │
│ AI response here...                                    │
│ [Reasoning ▼] (collapsible)                           │
│ Tool calls: glob, read                                 │
│ ─────────────────────────────────────────────────     │
└─────────────────────────────────────────────────────────┘
```

## Error Handling

- If `opencode` command not found: return 500 with message "opencode command not found"
- If session export fails: return 404, log error, continue with other sessions
- If export directory creation fails: catch exception, mark session as failed
- CORS enabled for local development

---

# Step-by-Step Implementation

## Step 1: Create Project Structure

```
mkdir -p opencode_session_exporter/static opencode_session_exporter/export
```

## Step 2: Create requirements.txt

```
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
```

## Step 3: Implement exporter.py

Implement all functions: `check_opencode_available`, `list_sessions`, `export_session`, `convert_to_markdown`, `save_markdown`, `export_single_session`.

## Step 4: Implement app.py

Set up FastAPI with CORS middleware, implement all API endpoints, serve static files.

## Step 5: Create Frontend

- `static/index.html` — Main layout with path input, search, session table, preview modal
- `static/styles.css` — Styling for table, modal, buttons, toast notifications
- `static/app.js` — Fetch sessions, handle search, selection, preview, export

## Step 6: Write Tests

- `test_exporter.py` — Test convert_to_markdown, save_markdown, export_single_session
- `test_app.py` — Test all API endpoints with mocked opencode

## Step 7: Run and Verify

```bash
cd opencode_session_exporter
python app.py
# Open http://127.0.0.1:8000
```

Verify:
- Sessions list loads (if opencode is installed)
- Search filters sessions
- Preview shows full conversation
- Export saves valid `.md` files to `export/` directory
- Tests pass: `python -m pytest`

---

# Dependencies

- **Prerequisite**: OpenCode CLI must be installed and in PATH
- **Python**: 3.8+

---

# Verification

```bash
cd opencode_session_exporter

# Run the app
python app.py

# In another terminal, run tests
python -m pytest -v

# Open browser
open http://127.0.0.1:8000
```

Expected results:
- 21 tests pass
- Web UI loads and displays sessions (if opencode available)
- Export creates Markdown files in `export/` directory