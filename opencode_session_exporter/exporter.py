import subprocess
import json
import re
import os
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

APP_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class SessionInfo:
    id: str
    title: str
    updated: str
    directory: str


@dataclass
class Message:
    role: str
    text: str
    reasoning: List[str]
    tool_calls: List[str]


def check_opencode_available() -> bool:
    try:
        result = subprocess.run(
            ["opencode", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def list_sessions(project_dir: str = None) -> List[SessionInfo]:
    cmd = ["opencode", "session", "list", "--format", "json"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=project_dir)
    except subprocess.TimeoutExpired:
        return []
    except FileNotFoundError:
        return []

    if result.returncode != 0:
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    sessions = []

    for item in data:
        session_dir = item.get("directory", "")
        
        if project_dir and session_dir != project_dir:
            continue

        session_id = item.get("id", "")
        title = item.get("title", "Untitled")
        updated_ts = item.get("updated", 0)
        
        updated_date = datetime.fromtimestamp(updated_ts / 1000).strftime("%Y-%m-%d %H:%M") if updated_ts else ""

        sessions.append(SessionInfo(
            id=session_id,
            title=title,
            updated=updated_date,
            directory=session_dir
        ))

    return sessions


def export_session(session_id: str, project_dir: str = None) -> Optional[dict]:
    import tempfile

    try:
        tmp_path = None
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        cmd = f"opencode export {session_id} > {tmp_path} 2>/dev/null"
        result = subprocess.run(cmd, shell=True, timeout=120, cwd=project_dir)
        if result.returncode != 0:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return None

        with open(tmp_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        os.unlink(tmp_path)

        info = raw_data.get("info", {})
        messages = raw_data.get("messages", [])

        updated_ts = info.get("time", {}).get("updated", 0)
        updated_date = datetime.fromtimestamp(updated_ts / 1000).strftime("%Y-%m-%d %H:%M") if updated_ts else ""

        return {
            "id": info.get("id", session_id),
            "title": info.get("title", "Untitled"),
            "directory": info.get("directory", ""),
            "updated": updated_date,
            "messages": messages,
        }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return None


def convert_to_markdown(data: dict) -> str:
    session_id = data.get("id", "")
    title = data.get("title", "Untitled")
    updated = data.get("updated", "")
    directory = data.get("directory", "")
    messages = data.get("messages", [])

    sanitized_title = re.sub(r"[^\w\- ]", "", title)
    sanitized_title = re.sub(r" +", "-", sanitized_title)
    date_str = updated.split()[0] if updated else "unknown"

    lines = []
    lines.append("---")
    lines.append(f'title: "{title}"')
    lines.append(f'date: "{updated}"')
    lines.append(f'directory: "{directory}"')
    lines.append(f'session_id: "{session_id}"')
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Date:** {updated}")
    lines.append(f"**Directory:** {directory}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for msg in messages:
        role = msg.get("role", "") or msg.get("info", {}).get("role", "")
        parts = msg.get("parts", [])

        if role == "user":
            text_content = ""
            for part in parts:
                if part.get("type") == "text":
                    text_content += part.get("text", "")
            if text_content:
                lines.append("## Human")
                lines.append("")
                lines.append(text_content)
                lines.append("")
                lines.append("---")
                lines.append("")

        elif role == "assistant":
            text_content = ""
            reasoning_parts = []
            tool_calls = []

            for part in parts:
                if part.get("type") == "text":
                    text_content += part.get("text", "")
                elif part.get("type") == "reasoning":
                    reasoning_parts.append(part.get("text", ""))
                elif part.get("type") == "tool":
                    tool_name = part.get("name", "unknown")
                    tool_calls.append(tool_name)

            if text_content or reasoning_parts or tool_calls:
                lines.append("## AI")
                lines.append("")

                if text_content:
                    lines.append(text_content)
                    lines.append("")

                if reasoning_parts:
                    for reasoning in reasoning_parts:
                        lines.append("<details>")
                        lines.append("<summary>Reasoning</summary>")
                        lines.append("")
                        lines.append(f"> {reasoning}")
                        lines.append("")
                        lines.append("</details>")
                        lines.append("")

                if tool_calls:
                    lines.append(f"Tool calls: {', '.join(tool_calls)}")
                    lines.append("")

                lines.append("---")
                lines.append("")

    return "\n".join(lines)


def save_markdown(content: str, title: str, updated: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)

    sanitized_title = re.sub(r"[^\w\- ]", "", title)
    sanitized_title = re.sub(r" +", "-", sanitized_title)

    date_part = ""
    time_part = ""
    if updated:
        parts = updated.split()
        date_part = parts[0] if len(parts) > 0 else "unknown"
        if len(parts) > 1:
            time_str = parts[1]
            time_part = time_str.replace(":", "-")

    if date_part and time_part:
        filename = f"{date_part}_{time_part}_{sanitized_title}.md"
    elif date_part:
        filename = f"{date_part}_{sanitized_title}.md"
    else:
        filename = f"{sanitized_title}.md"

    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filename


def export_single_session(session_id: str, output_dir: str = ".") -> Optional[str]:
    data = export_session(session_id)
    if not data:
        return None

    title = data.get("title", "Untitled")
    updated = data.get("updated", "")

    content = convert_to_markdown(data)
    filename = save_markdown(content, title, updated, output_dir)

    return filename