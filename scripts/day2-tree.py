from pathlib import Path


class LayerMappingBuilder:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.target_dir = project_root / "company_target"

    def source_directories(self) -> list[str]:
        return [
            "routers",
            "schemas",
            "services",
            "pipelines",
            "clients",
            "infra",
            "tasks",
            "models",
            "crud",
        ]

    def target_layer_for(self, name: str) -> str:
        mapping = {
            "routers": "api/routes",
            "schemas": "api/schemas 或 domains/*/schemas.py",
            "services": "domains/*/service.py",
            "pipelines": "domains/*/pipeline.py 或 workflow/jobs",
            "clients": "infra/*",
            "infra": "core/* 或 infra/*",
            "tasks": "workflow/jobs",
            "models": "domains/*/models.py",
            "crud": "domains/*/repository.py",
        }
        return mapping.get(name, "待定")

    def reason_for(self, name: str) -> str:
        reasons = {
            "routers": "当前已经是入站层雏形，应继续收口为 API 层。",
            "schemas": "当前承担请求响应和 DTO 角色，后续按用途分流。",
            "services": "当前是业务入口与领域逻辑混层，后续要按领域回收。",
            "pipelines": "当前是主链编排雏形，后续再决定保留在领域侧还是下沉到 workflow。",
            "clients": "当前本质上是外部依赖适配层。",
            "infra": "当前是运行时能力集合，后续需要更清晰地区分核心规则和底层适配。",
            "tasks": "当前是异步任务入口，适合演进成 workflow jobs。",
            "models": "当前是主数据模型层，后续按领域收口更清晰。",
            "crud": "当前是数据访问层，后续适合演进成 repository 语义。",
        }
        return reasons.get(name, "待补充")

    def build_markdown(self) -> str:
        lines = [
            "# Day 2 分层映射表",
            "",
            "| 当前目录 | 目标落位 | 原因 |",
            "|---|---|---|",
        ]
        for name in self.source_directories():
            lines.append(
                f"| `{name}` | `{self.target_layer_for(name)}` | {self.reason_for(name)} |"
            )
        return "\n".join(lines)

    def output_path(self) -> Path:
        return self.target_dir / "day2_layer_mapping.md"

    def write(self) -> Path:
        self.target_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_path()
        path.write_text(self.build_markdown(), encoding="utf-8")
        return path


def main() -> None:
    builder = LayerMappingBuilder(Path.cwd())
    path = builder.write()
    print(path)


if __name__ == '__main__':
    main()