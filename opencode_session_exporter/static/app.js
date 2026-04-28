function debounce(fn, delay) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), delay);
    };
}
let selectedIds = new Set();
let currentPath = null;
const MAX_RECENT_PATHS = 5;

function getRecentPaths() {
    try {
        return JSON.parse(localStorage.getItem("recentPaths")) || [];
    } catch {
        return [];
    }
}

function saveRecentPath(path) {
    if (!path) return;
    const paths = getRecentPaths().filter((p) => p !== path);
    paths.unshift(path);
    const trimmed = paths.slice(0, MAX_RECENT_PATHS);
    localStorage.setItem("recentPaths", JSON.stringify(trimmed));
}

function renderPathDropdown(items) {
    const dropdown = document.getElementById("path-dropdown");
    if (!items || items.length === 0) {
        dropdown.classList.add("hidden");
        return;
    }
    dropdown.innerHTML = items
        .map((item) => {
            const path = typeof item === 'string' ? item : item.path;
            const isDirectory = typeof item === 'object' && item.type === 'directory';
            const display = isDirectory ? path : path;
            return `<div class="path-dropdown-item" data-path="${escapeHtml(path)}">${escapeHtml(display)}</div>`;
        })
        .join("");
    dropdown.classList.remove("hidden");
}

async function fetchSessions(path = null) {
    let url = "/api/sessions";
    if (path) {
        url += `?project_path=${encodeURIComponent(path)}`;
    }
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error("Failed to fetch sessions");
    }
    const data = await response.json();
    return data.sessions;
}

async function fetchDirectories(path = null) {
    if (!path) return [];
    try {
        const url = `/api/directories?path=${encodeURIComponent(path)}`;
        const response = await fetch(url);
        if (!response.ok) return [];
        const data = await response.json();
        return data.directories || [];
    } catch {
        return [];
    }
}

async function fetchSessionDetail(sessionId) {
    let url = `/api/sessions/${sessionId}`;
    if (currentPath) {
        url += `?path=${encodeURIComponent(currentPath)}`;
    }
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error("Failed to fetch session");
    }
    return response.json();
}

function renderSessions(list) {
    const tbody = document.getElementById("session-list");
    const searchTerm = document.getElementById("search").value.toLowerCase();

    const filtered = list.filter((s) => {
        const searchText = (s.title + s.directory).toLowerCase();
        return searchText.includes(searchTerm);
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr class="loading-row"><td colspan="4">No sessions found</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered
        .map((s) => {
            const date = s.updated.split(" ")[0];
            return `
        <tr data-id="${s.id}" data-title="${date}_${escapeHtml(s.title)}">
            <td class="col-select" onclick="event.stopPropagation()">
                <input type="checkbox" ${selectedIds.has(s.id) ? "checked" : ""} onchange="toggleSelect('${s.id}', this.checked)">
            </td>
            <td class="col-title truncate" title="${date}_${escapeHtml(s.title)}">${date}_${escapeHtml(s.title)}</td>
            <td class="col-date">${s.updated}</td>
            <td class="col-directory truncate" title="${s.directory}">${s.directory}</td>
        </tr>
    `;
        })
        .join("");

    tbody.querySelectorAll("tr[data-id]").forEach((row) => {
        row.addEventListener("click", () => {
            const id = row.dataset.id;
            openPreview(id);
        });
    });
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function toggleSelect(id, checked) {
    if (checked) {
        selectedIds.add(id);
    } else {
        selectedIds.delete(id);
    }
    updateButtons();
}

function toggleSelectAll(checked) {
    const filtered = getFilteredSessions();
    if (checked) {
        filtered.forEach((s) => selectedIds.add(s.id));
    } else {
        filtered.forEach((s) => selectedIds.delete(s.id));
    }
    document.querySelectorAll('#session-list input[type="checkbox"]').forEach((cb) => {
        cb.checked = checked;
    });
    updateButtons();
}

function getFilteredSessions() {
    const searchTerm = document.getElementById("search").value.toLowerCase();
    return sessions.filter((s) => {
        const searchText = (s.title + s.directory).toLowerCase();
        return searchText.includes(searchTerm);
    });
}

function updateButtons() {
    const previewBtn = document.getElementById("preview-btn");
    const exportBtn = document.getElementById("export-btn");
    const countSpan = document.getElementById("selected-count");

    const count = selectedIds.size;
    if (countSpan) {
        countSpan.textContent = count;
    }

    previewBtn.disabled = count !== 1;
    exportBtn.disabled = count === 0;
}

async function openPreview(sessionId) {
    const response = await fetch(`/api/sessions/${sessionId}${currentPath ? '?project_path=' + encodeURIComponent(currentPath) : ''}`);
    if (!response.ok) {
        showToast("Failed to load session", "error");
        return;
    }

    const data = await response.json();
    const modal = document.getElementById("preview-modal");
    const modalTitle = document.getElementById("modal-title");
    const modalMeta = document.getElementById("modal-meta");
    const modalMessages = document.getElementById("modal-messages");

    modalTitle.textContent = data.title;
    modalMeta.innerHTML = `
        <p><strong>ID:</strong> ${data.id}</p>
        <p><strong>Date:</strong> ${data.updated}</p>
        <p><strong>Directory:</strong> ${data.directory}</p>
    `;

    modalMessages.innerHTML = data.messages
        .map((msg) => {
            let content = "";
            let reasoning = "";
            let toolCalls = [];

            for (const part of msg.parts) {
                if (part.type === "text") {
                    content += part.text;
                } else if (part.type === "reasoning") {
                    reasoning += part.text;
                } else if (part.type === "tool") {
                    toolCalls.push(part.name);
                }
            }

            const roleLabel = (msg.info?.role ?? msg.role) === "user" ? "Human" : "AI";

            let html = `
                <div class="message" data-role="${msg.info?.role ?? msg.role}">
                    <div class="message-role">${roleLabel}</div>
                    <div class="message-content">${escapeHtml(content)}</div>
            `;

            if (reasoning) {
                html += `
                    <details class="reasoning">
                        <summary>Reasoning</summary>
                        <div class="message-content">${escapeHtml(reasoning)}</div>
                    </details>
                `;
            }

            if (toolCalls.length > 0) {
                html += `
                    <div class="tool-calls">Tool calls: ${toolCalls.join(", ")}</div>
                `;
            }

            html += `</div>`;
            return html;
        })
        .join("");

    modal.classList.remove("hidden");
}

function closePreview() {
    const modal = document.getElementById("preview-modal");
    modal.classList.add("hidden");
}

async function exportSelected() {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;

    const exportBtn = document.getElementById("export-btn");
    exportBtn.disabled = true;
    exportBtn.textContent = "Exporting...";

    try {
        let url = "/api/export";
        if (currentPath) {
            url += `?project_path=${encodeURIComponent(currentPath)}`;
        }
        const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_ids: ids }),
        });

        const result = await response.json();

        if (result.exported.length > 0) {
            showToast(`Exported ${result.exported.length} session(s)`, "success");
            selectedIds.clear();
            updateButtons();
            renderSessions(sessions);
        }

        if (result.failed.length > 0) {
            showToast(`Failed to export ${result.failed.length} session(s)`, "error");
        }
    } catch (err) {
        showToast("Export failed", "error");
        console.error("Export error:", err);
    } finally {
        if (exportBtn) {
            exportBtn.disabled = false;
            exportBtn.textContent = 'Export Selected (0)';
        }
        updateButtons();
    }
}

function showToast(message, type = "") {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = "toast";
    if (type) toast.classList.add(type);
    toast.classList.remove("hidden");

    setTimeout(() => {
        toast.classList.add("hidden");
    }, 3000);
}

document.addEventListener("DOMContentLoaded", async () => {
    const pathDisplay = document.getElementById("path-display");
    const searchInput = document.getElementById("search");
    const previewBtn = document.getElementById("preview-btn");
    const exportBtn = document.getElementById("export-btn");
    const modalClose = document.getElementById("modal-close");

    async function loadSessions(path = null) {
        console.log("loadSessions called with path:", path);
        if (path) {
            path = path.replace(/\/+$/, '');
        }
        try {
            sessions = await fetchSessions(path);
            console.log("fetched sessions:", sessions.length);
            currentPath = path;
            selectedIds.clear();
            renderSessions(sessions);
            updateButtons();
        } catch (err) {
            console.error("loadSessions error:", err);
            document.getElementById("session-list").innerHTML = `
                <tr class="loading-row"><td colspan="4">Error loading sessions: ${err.message}</td></tr>
            `;
        }
    }

    try {
        await loadSessions(currentPath);
    } catch (err) {
        document.getElementById("session-list").innerHTML = `
            <tr class="loading-row"><td colspan="4">Error loading sessions: ${err.message}</td></tr>
        `;
    }

    const pathDropdown = document.getElementById("path-dropdown");
    const recentPaths = getRecentPaths();

    async function findExistingParent(path) {
        if (!path.startsWith('/')) return null;
        
        const parts = path.split('/').filter(p => p);
        
        for (let i = 1; i < parts.length; i++) {
            const testPath = '/' + parts.slice(0, i).join('/');
            try {
                const response = await fetch(`/api/directories?path=${encodeURIComponent(testPath)}`);
                const data = await response.json();
                if (!data.exists) {
                    const parentPath = '/' + parts.slice(0, i - 1).join('/');
                    return parentPath || null;
                }
            } catch {
                return null;
            }
        }
        
        return '/' + parts.slice(0, parts.length - 1).join('/');
    }

    async function filterPaths(searchText) {
        const results = [];
        
        const matchingRecent = recentPaths.filter(p => 
            p.toLowerCase().includes(searchText.toLowerCase())
        );
        results.push(...matchingRecent.map(p => ({ path: p, type: 'recent' })));
        
        if (searchText && searchText.startsWith('/')) {
            const trimmed = searchText.replace(/\/+$/, '');
            if (trimmed) {
                try {
                    const response = await fetch(`/api/directories?path=${encodeURIComponent(trimmed)}`);
                    const data = await response.json();
                    
                    if (data.exists) {
                        const matchingDirs = data.directories;
                        results.push(...matchingDirs.map(d => ({ 
                            path: trimmed + '/' + d, 
                            type: 'directory' 
                        })));
                        return results;
                    }
                    
                    const parentPath = await findExistingParent(trimmed);
                    if (parentPath) {
                        try {
                            const response = await fetch(`/api/directories?path=${encodeURIComponent(parentPath)}`);
                            const data = await response.json();
                            const baseName = trimmed.split('/').pop();
                            const searchLower = baseName.toLowerCase();
                            const matchingDirs = data.directories.filter(d => 
                                d.toLowerCase().includes(searchLower)
                            );
                            results.push(...matchingDirs.map(d => ({ 
                                path: parentPath + '/' + d, 
                                type: 'directory' 
                            })));
                        } catch (e) {}
                    }
                } catch (e) {}
            }
        }
        
        return results;
    }

    const debouncedPathInput = debounce(async (searchText) => {
        const filtered = await filterPaths(searchText);
        renderPathDropdown(filtered);
    }, 200);

    pathDisplay.addEventListener("input", async () => {
        const searchText = pathDisplay.value.trim();
        debouncedPathInput(searchText);
    });

    pathDisplay.addEventListener("focus", async () => {
        const searchText = pathDisplay.value.trim();
        const filtered = await filterPaths(searchText);
        renderPathDropdown(filtered);
    });

    pathDisplay.addEventListener("blur", () => {
        setTimeout(() => {
            pathDropdown.classList.add("hidden");
        }, 200);
    });

    pathDropdown.addEventListener("click", async (e) => {
        if (e.target.classList.contains("path-dropdown-item")) {
            let path = e.target.dataset.path;
            path = path.replace(/\/+$/, '');
            pathDisplay.value = path;
            pathDropdown.classList.add("hidden");
            saveRecentPath(path);
            await loadSessions(path);
        }
    });

    pathDisplay.addEventListener("keydown", async (e) => {
        if (e.key === "Enter") {
            let path = pathDisplay.value.trim();
            if (path) {
                path = path.replace(/\/+$/, '');
                saveRecentPath(path);
                await loadSessions(path);
            }
        }
    });

    searchInput.addEventListener("input", () => {
        renderSessions(sessions);
    });

    previewBtn.addEventListener("click", () => {
        const id = Array.from(selectedIds)[0];
        if (id) openPreview(id);
    });

    exportBtn.addEventListener("click", exportSelected);

    modalClose.addEventListener("click", closePreview);

    document.getElementById("preview-modal").addEventListener("click", (e) => {
        if (e.target.id === "preview-modal") {
            closePreview();
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closePreview();
        }
    });
});
