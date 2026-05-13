from pathlib import Path


class ArchitectureSnapshotBuilder:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def current_chain(self) -> list[str]:
        return [
            "Document",
            "Chunk",
            "Embedding",
            "Vector Retrieval",
            "RAG Answer",
        ]

    def target_chain(self) -> list[str]:
        return [
            "Document",
            "Chunk",
            "MemoryEntry",
            "CanonicalMemory / Snapshot",
            "Chunk + Memory + Graph Retrieval",
            "Evidence-based Answer",
        ]

    def build_markdown(self) -> str:
        current = " -> ".join(self.current_chain())
        target = " -> ".join(self.target_chain())
        return "\n".join(
            [
                "# Day 1 架构快照",
                "",
                "## 当前主链路",
                "",
                f"`{current}`",
                "",
                "## 目标主链路",
                "",
                f"`{target}`",
                "",
                "## Day 2 要接住的事情",
                "",
                "- 把目标链路拆成阶段",
                "- 把当前仓库映射到未来分层",
                "- 明确哪些位置先不改，只做收口设计",
            ]
        )


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    builder = ArchitectureSnapshotBuilder(repo_root=repo_root)
    print(builder.build_markdown())


if __name__ == "__main__":
    main()