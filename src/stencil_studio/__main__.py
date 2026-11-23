"""Stencil Studio seul, dans le navigateur : python -m stencil_studio [--port 9000] [--no-browser]."""
import sys

from .server import main

sys.exit(main())
