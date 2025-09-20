
# New Sphinx Structure

This folder was generated to match your requested structure.

## Build
```bash
# from repo root (same level as docs/)
make html
```

## Autodoc
If your Python package is in ./src, run:
```bash
make apidoc
make html
```

## Notes
- Markdown sources were converted to .rst with a simple converter.
- Some advanced MyST directives may need manual clean-up.
- The theory pages aggregate related presentation docs.
