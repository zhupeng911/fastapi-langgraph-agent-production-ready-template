"""应用 LangGraph 图相关工具."""

import tiktoken
from langchain_core.messages import BaseMessage
from langchain_core.messages import trim_messages as _trim_messages

from app.core.config import settings
from app.core.logging import logger
from app.schemas import Message

# 在模块级缓存 tiktoken 编码，确保线程安全并可复用
try:
    _TIKTOKEN_ENCODING = tiktoken.encoding_for_model(settings.DEFAULT_LLM_MODEL)
except KeyError:
    _TIKTOKEN_ENCODING = tiktoken.get_encoding("cl100k_base")


def _count_tokens_tiktoken(messages: list) -> int:
    """使用 tiktoken 在本地统计令牌数，无需调用 API."""
    num_tokens = 0
    for message in messages:
        # 每条消息都包含角色或名称产生的额外令牌
        num_tokens += 4
        if isinstance(message, dict):
            for _, value in message.items():
                if isinstance(value, str):
                    num_tokens += len(_TIKTOKEN_ENCODING.encode(value))
        elif isinstance(message, BaseMessage):
            content = message.content
            if isinstance(content, str):
                num_tokens += len(_TIKTOKEN_ENCODING.encode(content))
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, str):
                        num_tokens += len(_TIKTOKEN_ENCODING.encode(block))
                    elif isinstance(block, dict) and "text" in block:
                        num_tokens += len(_TIKTOKEN_ENCODING.encode(block["text"]))
    num_tokens += 2  # 每个回复都以 assistant 角色作为开头
    return num_tokens


def dump_messages(messages: list[Message]) -> list[dict]:
    """将消息转换为字典列表.

    参数：
        messages (list[Message]): 要转换的消息.

    返回：
        list[dict]: 转换后的消息字典列表.
    """
    return [message.model_dump() for message in messages]


def extract_text_content(content: str | list) -> str:
    """从 LLM 内容值中提取纯文本.

    同时处理简单字符串格式和 GPT-5 / Responses API 模型返回的结构化内容块列表：
        [{'type': 'reasoning', ...}, {'type': 'text', 'text': '...'}]

    参数：
        content: LangChain BaseMessage 中的原始内容.

    返回：
        纯文本字符串；没有可提取内容时返回空字符串.
    """
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "reasoning":
                logger.debug(
                    "reasoning_block_received",
                    reasoning_id=block.get("id"),
                    has_summary=bool(block.get("summary")),
                )
    return "".join(parts)


def process_llm_response(response: BaseMessage) -> BaseMessage:
    """规范化原始 LLM 响应，使 ``response.content`` 始终为纯字符串，与提供方的内容格式无关.

    参数：
        response: LLM 返回的原始响应.

    返回：
        同一个 BaseMessage 实例，其 ``content`` 已设置为纯字符串.
    """
    if isinstance(response.content, list):
        response.content = extract_text_content(response.content)
        logger.debug(
            "processed_structured_content",
            content_block_count=len(response.content),
            extracted_length=len(response.content),
        )
    return response


def prepare_messages(messages: list[Message], system_prompt: str) -> list[Message]:
    """为 LLM 准备消息.

    参数：
        messages (list[Message]): 待准备的消息.
        system_prompt (str): 要使用的系统提示词.

    返回：
        list[Message]: 准备后的消息.
    """
    try:
        trimmed_messages = _trim_messages(
            dump_messages(messages),
            strategy="last",
            token_counter=_count_tokens_tiktoken,
            max_tokens=settings.MAX_TOKENS,
            start_on="human",
            include_system=False,
            allow_partial=False,
        )
    except ValueError as e:
        # 处理无法识别的内容块，例如 GPT-5 的 reasoning 内容块
        if "Unrecognized content block type" in str(e):
            logger.warning(
                "token_counting_failed_skipping_trim",
                error=str(e),
                message_count=len(messages),
            )
            # 跳过裁剪，返回全部消息
            trimmed_messages = messages
        else:
            raise

    return [Message(role="system", content=system_prompt)] + trimmed_messages
