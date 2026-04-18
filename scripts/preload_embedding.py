import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clients.embedding_client import get_embeddings, resolve_embedding_source


def main() -> None:
    model_source, local_files_only = resolve_embedding_source()
    get_embeddings()
    source_kind = "local" if local_files_only else "remote"
    print(f"embedding ready from {source_kind}: {model_source}")


if __name__ == "__main__":
    main()
