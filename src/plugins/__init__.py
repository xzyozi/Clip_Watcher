"""
This package dynamically loads all converter plugins from the implementations subdirectory.
"""

from .base_plugin import Plugin

__all__ = [
    "Plugin",
]
