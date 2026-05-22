# -*- coding: utf-8 -*-
"""
WhatsApp Chat Parser Module
Parses WhatsApp chat exports in format: [DD/MM/YYYY HH:MM:SS] Contacto: Mensaje
Generates Obsidian-compatible Markdown with media embeds.
"""

import re
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import yaml


# Pattern: [DD/MM/YYYY HH:MM:SS] Contacto: Mensaje
# Supports both single and multi-line messages
WAMESSAGE_PATTERN = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+):\s*(.*)$",
    re.DOTALL | re.UNICODE,
)

# System messages: "SecureApp encryption" note or deleted messages
SYSTEM_PATTERNS = [
    re.compile(r"Mensaje\s+borrado", re.IGNORECASE),
    re.compile(r"Tu contacto\s+", re.IGNORECASE),
    re.compile(r"Messages are end-to-end encrypted", re.IGNORECASE),
]

# Media file extensions
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
AUDIO_EXTS = {".mp3", ".opus", ".ogg", ".m4a", ".aac", ".wav", ".amr"}
VIDEO_EXTS = {".mp4", ".3gp", ".mkv", ".avi", ".mov", ".webm"}


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """Create a safe filename for Obsidian."""
    # Remove/replace unsafe characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name[:max_length]
    return name if name else "untitled"


def detect_file_type(filename: str) -> Optional[str]:
    """Detect if a file is image, audio, video, or None."""
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    elif ext in AUDIO_EXTS:
        return "audio"
    elif ext in VIDEO_EXTS:
        return "video"
    return None


class Message:
    """Represents a single WhatsApp message."""

    def __init__(
        self,
        date: str,
        time: str,
        sender: str,
        content: str,
        is_system: bool = False,
    ):
        self.date = date
        self.time = time
        self.sender = sender.strip()
        self.content = content
        self.is_system = is_system
        self.media_file: Optional[str] = None

    @property
    def timestamp(self) -> str:
        return f"{self.date} {self.time}"

    def to_obsidian(self) -> str:
        """Convert message to Obsidian block."""
        # System messages — plain italic text
        if self.is_system:
            return f"*{self.content}*"

        # Media messages
        if self.media_file:
            file_type = detect_file_type(self.media_file)
            ext = Path(self.media_file).suffix.lower()
            filename = os.path.basename(self.media_file)

            if file_type == "image":
                return f"![{filename}](media/{filename})"
            elif file_type == "audio":
                return f"[🎤 {filename}](media/{filename})"
            elif file_type == "video":
                return f"[🎬 {filename}](media/{filename})"
            else:
                # Fallback: attached file as link
                return f"[📎 {filename}](media/{filename})"

        # Text message
        return self.content.strip()


class ChatSession:
    """Represents a parsed WhatsApp chat session."""

    def __init__(self, contact_name: str):
        self.contact_name = sanitize_filename(contact_name)
        self.messages: list[Message] = []
        self.export_date: Optional[str] = None
        self.stats = {
            "total": 0,
            "text": 0,
            "images": 0,
            "audio": 0,
            "video": 0,
            "system": 0,
        }

    def add_message(self, msg: Message):
        self.messages.append(msg)
        self.stats["total"] += 1
        if msg.is_system:
            self.stats["system"] += 1
        elif msg.media_file:
            ft = detect_file_type(msg.media_file)
            if ft == "image":
                self.stats["images"] += 1
            elif ft == "audio":
                self.stats["audio"] += 1
            elif ft == "video":
                self.stats["video"] += 1
        else:
            self.stats["text"] += 1

    def to_markdown(self) -> str:
        """Generate full Obsidian Markdown document."""
        lines = []

        # Frontmatter YAML
        frontmatter = {
            "title": f"Chat {self.contact_name}",
            "date": self.export_date or datetime.now().strftime("%Y-%m-%d"),
            "contact": self.contact_name,
            "tags": ["whatsapp", "chat", "importado"],
        }
        lines.append("---")
        lines.append(yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False).strip())
        lines.append("---")
        lines.append("")
        lines.append(f"# Chat {self.contact_name}")
        lines.append("")
        lines.append("## Mensajes")
        lines.append("")

        # Messages in chronological order
        for msg in self.messages:
            obsidian_block = msg.to_obsidian()
            if obsidian_block:
                lines.append(f"- **[{msg.timestamp}]** {msg.sender}: {obsidian_block}")

        lines.append("")
        lines.append("---")
        lines.append("*Generado automáticamente — WhatsApp Chat Importer*")

        return "\n".join(lines)


def _is_system_message(text: str) -> bool:
    """Check if the message is a system/informational message."""
    text = text.strip()
    for pattern in SYSTEM_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _extract_media_from_content(content: str) -> tuple[str, Optional[str]]:
    """
    Extract media file reference from message content.
    WhatsApp format: 'Foto', 'Audio', 'Video', 'GIF animado', '<Media omitted>'
    Returns (cleaned_content, media_filename_or_None)
    """
    content = content.strip()

    media_patterns = [
        (re.compile(r"^Foto(?:\s*\(.*?\))?\s*$"), "photo"),
        (re.compile(r"^Audio(?:\s*\(.*?\))?\s*$"), "audio"),
        (re.compile(r"^Video(?:\s*\(.*?\))?\s*$"), "video"),
        (re.compile(r"^GIF animado(?:\s*\(.*?\))?\s*$"), "video"),
        (re.compile(r"^<Media omitted>\s*$", re.IGNORECASE), "media"),
    ]

    for pattern, media_type in media_patterns:
        if pattern.match(content):
            # Return placeholder filename
            suffix = {"photo": ".jpg", "audio": ".mp3", "video": ".mp4", "media": ".bin"}.get(
                media_type, ".bin"
            )
            placeholder = f"media_{media_type}{suffix}"
            return "", placeholder

    return content, None


def parse_single_message(line: str) -> Optional[Message]:
    """
    Try to parse a single line as a WhatsApp message header.
    Returns Message object or None.
    """
    line = line.strip()
    if not line or line.startswith("---"):
        return None

    match = WAMESSAGE_PATTERN.match(line)
    if match:
        date, time, sender, content = match.groups()
        content, media_file = _extract_media_from_content(content)
        is_system = _is_system_message(content) if not media_file else False

        msg = Message(date, time, sender, content, is_system=is_system)
        msg.media_file = media_file
        return msg

    return None


def parse_chat_text(text: str) -> list[ChatSession]:
    """
    Parse full WhatsApp chat export text.
    Groups messages by contact (sender).
    Returns list of ChatSession objects.
    """
    sessions: dict[str, ChatSession] = {}
    current_message: Optional[Message] = None
    lines = text.split("\n")

    for raw_line in lines:
        line = raw_line.rstrip("\n")

        # Try to detect a new message header
        msg = parse_single_message(line)
        if msg:
            # Save previous message if exists
            if current_message:
                if current_message.sender not in sessions:
                    sessions[current_message.sender] = ChatSession(current_message.sender)
                sessions[current_message.sender].add_message(current_message)

            current_message = msg
        elif current_message and raw_line.startswith(" "):
            # Continuation of multi-line message (starts with space)
            current_message.content += "\n" + raw_line
        elif current_message:
            # Multi-line continuation without leading space
            # Only add if the previous line ended mid-sentence (no period/exclamation)
            prev = current_message.content.rstrip()
            if prev and prev[-1] not in ".!?。" and len(raw_line.strip()) > 0:
                current_message.content += " " + raw_line.strip()

    # Don't forget the last message
    if current_message:
        if current_message.sender not in sessions:
            sessions[current_message.sender] = ChatSession(current_message.sender)
        sessions[current_message.sender].add_message(current_message)

    return list(sessions.values())


def discover_chat_files(extracted_dir: str) -> dict[str, list[str]]:
    """
    Discover chat .txt files and media files in the extracted directory.
    Returns dict with keys: 'chats', 'images', 'audio', 'video'
    """
    result = {"chats": [], "images": [], "audio": [], "video": []}

    for root, _dirs, files in os.walk(extracted_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            ext = Path(fname).suffix.lower()

            if ext == ".txt":
                result["chats"].append(fpath)
            elif ext in IMAGE_EXTS:
                result["images"].append(fpath)
            elif ext in AUDIO_EXTS:
                result["audio"].append(fpath)
            elif ext in VIDEO_EXTS:
                result["video"].append(fpath)

    return result