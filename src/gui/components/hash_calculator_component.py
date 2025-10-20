import tkinter as tk
from tkinter import ttk
import hashlib
import logging

from src.gui.base_frame_gui import BaseFrameGUI

class HashCalculatorComponent(BaseFrameGUI):
    """
    A GUI component for calculating hash values of text.
    """
    def __init__(self, master, app_instance):
        super().__init__(master, app_instance)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing HashCalculatorComponent.")

        self.hash_algorithms = sorted(hashlib.algorithms_available)
        self.algorithm_var = tk.StringVar(value='sha256')

        self._create_widgets()

    def _create_widgets(self):
        # Input frame
        input_frame = ttk.LabelFrame(self, text="Input Text")
        input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.input_text = tk.Text(input_frame, wrap=tk.WORD, height=10)
        self.input_text.pack(fill=tk.BOTH, expand=True)

        # Control frame
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(control_frame, text="Algorithm:").pack(side=tk.LEFT, padx=(0, 5))
        algorithm_combo = ttk.Combobox(control_frame, textvariable=self.algorithm_var, values=self.hash_algorithms, width=15)
        algorithm_combo.pack(side=tk.LEFT)
        algorithm_combo.bind("<<ComboboxSelected>>", self._calculate_hash)

        calculate_button = ttk.Button(control_frame, text="Calculate", command=self._calculate_hash)
        calculate_button.pack(side=tk.LEFT, padx=5)
        
        self.input_text.bind("<KeyRelease>", self._on_text_change)


        # Output frame
        output_frame = ttk.LabelFrame(self, text="Hash Output")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.output_text = tk.Text(output_frame, wrap=tk.WORD, height=5, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True)

    def _on_text_change(self, event=None):
        self._calculate_hash()

    def _calculate_hash(self, event=None):
        input_data = self.input_text.get("1.0", "end-1c").encode('utf-8')
        algorithm = self.algorithm_var.get()

        if not algorithm:
            return

        try:
            hasher = hashlib.new(algorithm)
            hasher.update(input_data)
            hash_result = hasher.hexdigest()

            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", hash_result)
            self.output_text.config(state=tk.DISABLED)
        except ValueError as e:
            self.logger.error(f"Error calculating hash: {e}")
            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", f"Error: {e}")
            self.output_text.config(state=tk.DISABLED)
