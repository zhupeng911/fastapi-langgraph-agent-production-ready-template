"""LangGraph 的 DuckDuckGo 搜索工具.

本模块提供可与 LangGraph 配合使用的 DuckDuckGo 搜索工具，最多返回 10 条搜索结果，
并对错误进行兼容处理.
"""

from langchain_community.tools import DuckDuckGoSearchResults

duckduckgo_search_tool = DuckDuckGoSearchResults(num_results=10, handle_tool_error=True)
