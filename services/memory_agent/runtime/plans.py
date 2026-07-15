from services.memory_agent.runtime.contracts import RetrievalPlan

MODE_PLANS = {
    "kb_qa": RetrievalPlan(document=True, memory=True, profile=False, relations=False, max_expansions=1),
    "memory_query": RetrievalPlan(document=False, memory=True, profile=False, relations=False, max_expansions=1),
    "profile_query": RetrievalPlan(document=False, memory=True, profile=True, relations=False, max_expansions=0),
    "analysis_query": RetrievalPlan(document=True, memory=True, profile=True, relations=True, max_expansions=1),
    "general_chat": RetrievalPlan(document=False, memory=False, profile=False, relations=False, max_expansions=0),
}
