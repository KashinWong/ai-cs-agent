"""LangGraph 薄层装配（可替换）。US2 接线（T050）：

  START → noise_filter →(噪音)END
                       →(正常) retrieve → grade →(escalate)END
                                                  →(正常) generate → END

不设独立 rerank 节点（RRF 属 retrieval 内部）；tool 节点为第二期占位不入活动路径。
仅 generate 调用模型，故 astream_events 的 token 流只在 generate 阶段产生。
"""
from langgraph.graph import END, START, StateGraph

from app.engine.nodes.generate import generate_node
from app.engine.nodes.grade import grade_node
from app.engine.nodes.noise_filter import noise_filter_node
from app.engine.nodes.retrieve import retrieve_node
from app.engine.state import GraphState


def _after_noise(state: GraphState) -> str:
    return "end" if state.get("noise") else "retrieve"


def _after_grade(state: GraphState) -> str:
    return "end" if state.get("escalate_reason") else "generate"


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("noise_filter", noise_filter_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("grade", grade_node)
    g.add_node("generate", generate_node)

    g.add_edge(START, "noise_filter")
    g.add_conditional_edges("noise_filter", _after_noise, {"end": END, "retrieve": "retrieve"})
    g.add_edge("retrieve", "grade")
    g.add_conditional_edges("grade", _after_grade, {"end": END, "generate": "generate"})
    g.add_edge("generate", END)
    return g.compile()


graph = build_graph()
