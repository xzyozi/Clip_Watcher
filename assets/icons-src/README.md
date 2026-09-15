# Icon sources

`pin.svg` is the editable source for the pinned-history icon.

Export it as `../icons/pin.png` with these settings before updating the runtime asset:

- Canvas: 24 × 24 px
- Format: PNG with RGBA transparency
- Keep the red gradients, highlight, shadow, and metallic needle
- Do not add a solid background

The application loads only the PNG at runtime. This keeps the desktop build free of SVG rendering dependencies while retaining an editable vector source.
