import sys
from pathlib import Path


class Root:
    @staticmethod
    def internal(*relative_parts: str) -> str:
        if hasattr(sys, "_MEIPASS"):
            base_dir = Path(sys._MEIPASS)
        else:
            base_dir = Path.cwd()
        return str(base_dir.joinpath(*relative_parts))

    @staticmethod
    def external(*relative_parts: str) -> str:
        if hasattr(sys, "_MEIPASS"):
            base_dir = Path(sys.executable).resolve().parent
        else:
            base_dir = Path.cwd()
        return str(base_dir.joinpath(*relative_parts))
