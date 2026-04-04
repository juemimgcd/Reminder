from collections import defaultdict


def group_entries_by_type(entries: list[dict]) -> dict[str, list[str]]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)

    for item in entries:
        grouped[item["entry_type"]].append(item["entry_name"])

    return dict(grouped)


def build_timeline(entries: list[dict]) -> list[dict]:
    sorted_entries = sorted(entries, key=lambda x: x["created_at"])

    return [
        {
            "entry_id": item["id"],
            "entry_name": item["entry_name"],
            "entry_type": item["entry_type"],
            "summary": item["summary"],
            "created_at": item["created_at"],
        }
        for item in sorted_entries
    ]


def build_theme_groups(entries: list[dict]) -> list[dict]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for item in entries:
        grouped[item["entry_name"]].append(item["summary"])

    result: list[dict] = []

    for theme_name,related_entries in grouped.items():
        result.append(
            {
                "theme_name": theme_name,
                "entries": related_entries,
                "count": len(related_entries),
            }
        )

    return sorted(result, key=lambda x: x["count"], reverse=True)








def build_memory_library(entries: list[dict]) -> dict:
    return {
        "timeline": build_timeline(entries),
        "by_type": group_entries_by_type(entries),
        "by_theme": build_theme_groups(entries),
    }











