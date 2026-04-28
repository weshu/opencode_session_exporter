# Session Path Selector Design

## Overview
Replace the search input with a path selector that allows users to choose the folder where opencode looks for sessions.

## UI Changes

### index.html
- Replace `<input id="search">` with:
  - `<input id="path-display" class="path-input" readonly placeholder="Select folder...">`
  - `<button id="browse-btn" class="btn btn-secondary">Browse</button>`
- Keep search functionality (it filters the loaded sessions client-side)

### app.js
- Add click handler for Browse button:
  - Use `window.showDirectoryPicker()` (native folder picker API)
  - On selection, update path-display input and trigger session reload
- Modify `fetchSessions()`:
  - Accept optional `path` parameter
  - Call `/api/sessions?path=${encodeURIComponent(path)}`
- On path change, clear selected sessions and reload list

### Backend Changes

### app.py
- Modify `get_sessions()`:
  - Accept `path: str = None` query parameter
  - Pass path to `list_sessions(path)`