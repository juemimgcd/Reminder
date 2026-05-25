import re

from schemas.chat import QueryRouteDecision


GENERAL_CHAT_PATTERNS = [
    r"你是谁",
    r"你是做什么的",
    r"你能做什么",
    r"你可以做什么",
    r"怎么使用",
    r"如何使用",
    r"帮助",
    r"你好",
    r"hello",
    r"\bhi\b",
    r"谢谢",
]

ACTION_PATTERNS = [
    r"帮我.*(上传|删除|创建|新建|重建|导入|导出|修改|更新)",
    r"请.*(上传|删除|创建|新建|重建|导入|导出|修改|更新)",
    r"(上传|删除|创建|新建|重建|导入|导出|修改|更新).*(文档|知识库|索引|记忆|文件)",
]

PROFILE_PATTERNS = [
    r"画像",
    r"我.*(风格|偏好|特点|能力|标签|长期关注)",
    r"(总结|分析).*我.*(特点|风格|能力|偏好)",
]

ANALYSIS_PATTERNS = [
    r"成长报告",
    r"阶段总结",
    r"趋势",
    r"变化",
    r"(最近|近期).*(关注|进展|卡点|亮点|成长)",
    r"(分析|总结).*(最近|近期|阶段|成长)",
]

MEMORY_PATTERNS = [
    r"我之前",
    r"以前.*(说|提到|记录|写过)",
    r"记忆",
    r"回忆",
    r"(历史|过往).*(记录|内容|经历)",
]


def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def route_query(question: str) -> QueryRouteDecision:
    normalized = question.strip().lower()
    if not normalized:
        return QueryRouteDecision(
            query_type="general_chat",
            requires_retrieval=False,
            target_pipeline="general_chat",
            confidence="high",
            reason="empty query should not trigger retrieval",
        )

    if _matches_any(ACTION_PATTERNS, normalized):
        return QueryRouteDecision(
            query_type="action_request",
            requires_retrieval=False,
            target_pipeline="action_guidance",
            confidence="medium",
            reason="query asks the assistant to perform a system action",
        )

    if _matches_any(PROFILE_PATTERNS, normalized):
        return QueryRouteDecision(
            query_type="profile_query",
            requires_retrieval=False,
            target_pipeline="profile",
            confidence="medium",
            reason="query asks for a user/profile-level summary",
        )

    if _matches_any(ANALYSIS_PATTERNS, normalized):
        return QueryRouteDecision(
            query_type="analysis_query",
            requires_retrieval=False,
            target_pipeline="growth_analysis",
            confidence="medium",
            reason="query asks for trend, stage, or growth analysis",
        )

    if _matches_any(MEMORY_PATTERNS, normalized):
        return QueryRouteDecision(
            query_type="memory_query",
            requires_retrieval=True,
            target_pipeline="memory_rag",
            confidence="medium",
            reason="query asks about past memories or recorded facts",
        )

    if _matches_any(GENERAL_CHAT_PATTERNS, normalized):
        return QueryRouteDecision(
            query_type="general_chat",
            requires_retrieval=False,
            target_pipeline="general_chat",
            confidence="high",
            reason="query is assistant/help/greeting oriented",
        )

    return QueryRouteDecision(
        query_type="kb_qa",
        requires_retrieval=True,
        target_pipeline="evidence_rag",
        confidence="medium",
        reason="default knowledge-base answer path",
    )
