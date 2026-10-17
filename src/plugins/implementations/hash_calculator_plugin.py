from __future__ import annotations

import hashlib
import logging
import tkinter as tk
from tkinter import Event, ttk
from typing import TYPE_CHECKING

from src.core.config import defaults as config
from src.gui.base.base_frame_gui import BaseFrameGUI
from src.plugins.gui_plugin import GuiPlugin as Plugin

if TYPE_CHECKING:
    from src.core.bootstrap.base_application import BaseApplication


MAX_HASH_INPUT_LENGTH = 1_000_000  # 1MB: メモリ枯渇・DoS防止のための入力長制限 (#127)
DEFAULT_SHAKE_DIGEST_LENGTH = 32  # SHAKE系XOFの既定出力長（バイト）(#127)


# The GUI Component implementation, moved from gui/components
class HashCalculatorComponent(BaseFrameGUI):
    """
    A GUI component for calculating hash values of text.
    """

    def __init__(self, master: tk.Misc, app_instance: BaseApplication) -> None:
        super().__init__(master, app_instance)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing HashCalculatorComponent.")

        self.hash_algorithms = sorted(hashlib.algorithms_available)
        self.algorithm_var = tk.StringVar(value="sha256")
        self._debounce_timer: str | None = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        # Input frame
        input_frame = ttk.LabelFrame(self, text="Input Text")
        input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.input_text = tk.Text(input_frame, wrap=tk.WORD, height=10)
        self.input_text.pack(fill=tk.BOTH, expand=True)

        # Control frame
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(control_frame, text="Algorithm:").pack(side=tk.LEFT, padx=(0, 5))
        algorithm_combo = ttk.Combobox(
            control_frame,
            textvariable=self.algorithm_var,
            values=self.hash_algorithms,
            width=15,
            state="readonly",
        )
        algorithm_combo.pack(side=tk.LEFT)
        algorithm_combo.bind("<<ComboboxSelected>>", self._on_algorithm_change)

        calculate_button = ttk.Button(
            control_frame, text="Calculate", command=self._calculate_hash
        )
        calculate_button.pack(side=tk.LEFT, padx=5)

        self.input_text.bind("<KeyRelease>", self._on_text_change)

        # Output frame
        output_frame = ttk.LabelFrame(self, text="Hash Output")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.output_text = tk.Text(
            output_frame, wrap=tk.WORD, height=5, state=tk.DISABLED
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)

    def _set_output(self, text: str) -> None:
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", text)
        self.output_text.config(state=tk.DISABLED)

    def _on_algorithm_change(self, event: Event | None = None) -> None:
        self._cancel_debounce()
        self._calculate_hash()

    def _on_text_change(self, event: Event | None = None) -> None:
        self._cancel_debounce()
        # 300ms デバウンス制御によるキーストローク時のDoS防止 (#127)
        self._debounce_timer = self.after(300, self._calculate_hash)

    def _cancel_debounce(self) -> None:
        if self._debounce_timer is not None:
            self.after_cancel(self._debounce_timer)
            self._debounce_timer = None

    def _calculate_hash(self, event: Event | None = None) -> None:
        self._cancel_debounce()
        raw_text = self.input_text.get("1.0", "end-1c")

        if len(raw_text) > MAX_HASH_INPUT_LENGTH:
            self.logger.warning(
                "ハッシュ計算入力長が上限（%d文字）を超過しているため中断します (現在: %d文字)",
                MAX_HASH_INPUT_LENGTH,
                len(raw_text),
            )
            self._set_output(
                f"Error: Input text exceeds maximum allowed size ({MAX_HASH_INPUT_LENGTH:,} characters)."
            )
            return

        algorithm = self.algorithm_var.get()
        if not algorithm:
            return

        input_data = raw_text.encode("utf-8")

        try:
            hasher = hashlib.new(algorithm)
            hasher.update(input_data)
            # SHAKE系XOFアルゴリズムはhexdigestにlength指定が必須 (#127)
            if algorithm.startswith("shake_"):
                hash_result = hasher.hexdigest(DEFAULT_SHAKE_DIGEST_LENGTH)  # type: ignore[call-arg]
            else:
                hash_result = hasher.hexdigest()

            self._set_output(hash_result)
        except (ValueError, TypeError) as e:
            self.logger.warning("Error calculating hash (%s): %s", algorithm, e)
            self._set_output(f"Error: {e}")


# The Plugin definition
class HashCalculatorPlugin(Plugin):
    """
    Plugin wrapper for the Hash Calculator GUI tool.
    """

    @property
    def name(self) -> str:
        return "Hash Calculator"

    @property
    def description(self) -> str:
        return "A GUI tool to calculate hash values of text."

    def has_gui_component(self) -> bool:
        return True

    def create_gui_component(
        self, parent: ttk.Notebook, app_instance: BaseApplication
    ) -> ttk.Frame | None:
        # Create a container frame with padding, similar to the original implementation
        tool_frame = ttk.Frame(parent, padding=config.FRAME_PADDING)

        # Create the actual component inside the container frame
        component = HashCalculatorComponent(tool_frame, app_instance)
        component.pack(fill=tk.BOTH, expand=True)

        # Return the container frame, which will be added as a tab
        return tool_frame
