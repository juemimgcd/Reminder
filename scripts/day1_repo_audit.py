from pathlib import Path


class RepoAuditBuilder:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self._targets = [
            "main.py",
            "routers/documents.py",
            "services/document_service.py",
            "pipelines/document_index_pipeline.py",
            "services/memory_service.py",
            "clients/vector_store_client.py",
            "clients/neo4j_client.py",
            "Mneme_polish_v4.md",
            "company_target/day1-day20-summary.md",
        ]

    def build_target_paths(self) -> list[Path]:
        return [self.repo_root / item for item in self._targets]

    def classify_path(self, path: Path) -> str:
        normalized = str(path).replace("\\", "/")
        if normalized.endswith("main.py"):
            return "entry"
        if "/routers/" in normalized:
            return "router"
        if "/services/" in normalized:
            return "service"
        if "/pipelines/" in normalized:
            return "pipeline"
        if "/clients/" in normalized:
            return "client"
        if "/infra/" in normalized:
            return "infra"
        return "support"

    def build_markdown(self) -> str:
        lines = [
            "# Day 1 边界审计表",
            "",
            "## 当前主链路",
            "",
            "- 入口：`main.py`",
            "- 上传与索引入口：`routers/documents.py`",
            "- 任务提交与业务编排：`services/document_service.py`",
            "- 阶段执行链路：`pipelines/document_index_pipeline.py`",
            "- 记忆抽取：`services/memory_service.py`",
            "- 向量层：`clients/vector_store_client.py`",
            "- 图层：`clients/neo4j_client.py`",
            "",
            "## 重点文件分类",
            "",
        ]
        for path in self.build_target_paths():
            lines.append(f"- `{path.relative_to(self.repo_root)}` -> {self.classify_path(path)}")
        lines.extend(
            [
                "",
                "## Day 2 输入",
                "",
                "- 当前主链路已经存在，但需要明确分层收口",
                "- 需要把长期记忆、GraphRAG 和任务可靠性串成统一架构",
            ]
        )
        return "\n".join(lines)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    builder = RepoAuditBuilder(repo_root=repo_root)
    print(builder.build_markdown())


if __name__ == "__main__":
    main()