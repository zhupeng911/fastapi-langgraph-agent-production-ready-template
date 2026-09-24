"""用于增强语言模型能力的 LangGraph 工具.

本模块包含可供 LangGraph 使用的自定义工具，用于扩展语言模型能力，
目前包括网页搜索和其他外部集成工具.
"""

from langchain_core.tools.base import BaseTool

from .ask_human import ask_human
from .duckduckgo_search import duckduckgo_search_tool

tools: list[BaseTool] = [duckduckgo_search_tool, ask_human]
