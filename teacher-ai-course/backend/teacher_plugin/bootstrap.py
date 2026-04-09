import sys
from pathlib import Path


def bootstrap_backend_common() -> None:
    backend_common = Path(__file__).resolve().parents[3] / "backend-common"
    backend_common_str = str(backend_common)
    if backend_common.exists() and backend_common_str not in sys.path:
        sys.path.insert(0, backend_common_str)


bootstrap_backend_common()
