"""LangGraph 的人在回路确认工具.

本模块提供一个工具，在执行敏感操作前暂停图执行并请求用户确认.
"""

from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def ask_human(question: str) -> str:
    """暂停执行，并在继续之前向用户提问.

    在执行重要操作前需要澄清、确认或补充输入时使用此工具，
    例如删除数据、发送邮件、购买商品或执行任何不可逆操作.

    参数：
        question: 要向用户提出的问题.

    返回：
        str: 用户的回答.
    """
    user_response = interrupt(question)
    return str(user_response)
