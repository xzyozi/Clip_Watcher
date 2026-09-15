# ClipWatcher 📋

> **A local clipboard history manager with text workflow automation, built with Python, Tkinter, and SQLite.**

[English](./README.md) | [日本語](./README.ja.md)

[![CI](https://github.com/xzyozi/Clip_Watcher/actions/workflows/ci.yml/badge.svg)](https://github.com/xzyozi/Clip_Watcher/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

## Overview

ClipWatcher monitors clipboard changes and keeps reusable text history locally. It provides fast search, pinned entries, phrase management, configurable themes, and extensible text-processing plugins.

## Features

- **Clipboard history** — Automatically records copied text in SQLite.
- **Search and filtering** — Finds history entries as you type.
- **Pinned entries** — Keeps frequently used items at the top and protects them from bulk deletion.
- **Phrase management** — Organizes reusable text by category and copies it quickly.
- **Plugins** — Supports text transformations and additional GUI tool tabs.
- **Undo/redo** — Encapsulates supported history changes through the command pattern.
- **Appearance and privacy settings** — Includes light/dark themes, always-on-top mode, history limits, and excluded applications.

## Requirements

- Python 3.10 or later
- Windows is the primary supported environment; `pywin32` is used for Windows clipboard integration.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python clip_watcher.py
```

For development tools, install the `dev` extra:

```powershell
python -m pip install -e ".[dev]"
```

## Quality Checks

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy .
python -m pytest
```

CI runs the equivalent lint, format, type-check, and test steps through `uv` on GitHub Actions.

## Documentation

See the [documentation guide](docs/README.md) for current design documents, development setup, how-to guides, reviews, and historical records.

## Privacy and Security

Clipboard history may contain sensitive text. Use excluded-application settings for password managers or any application whose clipboard contents must not be recorded. Local security policies can also restrict clipboard access.
