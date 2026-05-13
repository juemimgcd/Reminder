from pathlib import Path


class TargetArchitectureBlueprintBuilder:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.target_dir = project_root / "company_target"

    def current_chain(self) -> list[str]:
        return [
            "main.py",
            "routers/documents.py",
            "services/document_service.py",
            "pipelines/document_index_pipeline.py",
            "services/query_service.py",
            "clients/vector_store_client.py",
            "answer",
        ]

    def target_chain(self) -> list[str]:
        return [
            "Document",
            "Chunk",
            "MemoryEntry",
            "CanonicalMemory / Profile Snapshot",
            "Hybrid Retrieval",
            "GraphRAG Expansion",
            "Evidence-based Answer",
            "Debug / Eval / Analysis",
        ]

    def stage_plan(self) -> list[tuple[str, str]]:
        return [
            ("Phase A", "Day 3 - Day 7：MemoryEntry、Evidence、Hybrid Retrieval"),
            ("Phase B", "Day 8 - Day 11：GraphRAG、Graph Projection、Outbox"),
            ("Phase C", "Day 12 - Day 14：CanonicalMemory、Snapshot、Timeline"),
            ("Phase D", "Day 15 - Day 17：Debug、Eval、DuckDB Analysis"),
            ("Phase E", "Day 18 - Day 20：thin entry、分层收口、LlamaIndex / MongoDB 减重"),
        ]

    def build_markdown(self) -> str:
        current = "\n".join(f"- {item}" for item in self.current_chain())
        target = "\n".join(f"- {item}" for item in self.target_chain())
        stages = "\n".join(f"- `{name}`：{desc}" for name, desc in self.stage_plan())
        return "\n".join(
            [
                "# Day 2 目标架构蓝图",
                "",
                "## 当前主链",
                current,
                "",
                "## 目标主链",
                target,
                "",
                "## 阶段顺序",
                stages,
                "",
                "## Day 3 要接住的事情",
                "- 把 `MemoryEntry` 正式拉进主链。",
                "- 不再让它只是附属分析结果。",
                "- 为后续 Evidence 和 GraphRAG 提供统一核心对象。",
            ]
        )

    def output_path(self) -> Path:
        return self.target_dir / "day2_target_blueprint.md"

    def write(self) -> Path:
        self.target_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_path()
        path.write_text(self.build_markdown(), encoding="utf-8")
        return path


def main() -> None:
    builder = TargetArchitectureBlueprintBuilder(Path.cwd())
    path = builder.write()
    print(path)


if __name__ == '__main__':
    main()