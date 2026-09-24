"""会话自动命名功能.

新会话收到第一条消息时，本模块会：
  1. 在 Postgres 中原子占用会话，避免并发请求和多个 uvicorn Worker 重复调用 LLM.
  2. 根据用户消息写入占位名称，即使后续 LLM 调用失败，会话也始终有合理名称.
  3. 启动后台 asyncio 任务，调用快速 nano 模型生成正式标题并覆盖占位名称.
"""

import asyncio

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import (
    Session as DBSession,
    col,
    update,
)

from app.core.logging import logger
from app.core.metrics import session_names_generated_total
from app.core.prompts import SESSION_TITLE_PROMPT
from app.models.session import Session as ChatSession
from app.schemas.chat import SessionTitle
from app.services.database import database_service
from app.services.llm import llm_service

_PLACEHOLDER_MAX = 40

_background_tasks: set[asyncio.Task] = set()


def _build_placeholder(user_message: str) -> str:
    cleaned = " ".join(user_message.split())
    return cleaned[:_PLACEHOLDER_MAX].rstrip() or "New chat"


def _claim_session(session_id: str, placeholder: str) -> bool:
    """判断当前调用方是否成功原子占用 Postgres 中的会话.

    通过一次往返执行 ``UPDATE ... WHERE name = ''``，确保并发调用方中只有一个获得 rowcount == 1.
    """
    with DBSession(database_service.engine) as db:
        stmt = (
            update(ChatSession)
            .where(col(ChatSession.id) == session_id, col(ChatSession.name) == "")
            .values(name=placeholder)
        )
        result = db.exec(stmt)
        db.commit()
        return (result.rowcount or 0) == 1


async def _persist_session_name(session_id: str, user_message: str) -> None:
    try:
        result = await llm_service.call(
            [
                SystemMessage(content=SESSION_TITLE_PROMPT),
                HumanMessage(content=user_message[:500]),
            ],
            model_name="gpt-5.4-nano",
            response_format=SessionTitle,
            reasoning={"effort": "low"},
            max_tokens=32,
            temperature=0.3,
        )
        await database_service.update_session_name(session_id, result.title)
        session_names_generated_total.labels(status="success").inc()
        logger.info("session_name_generated", session_id=session_id, name=result.title)
    except Exception:
        session_names_generated_total.labels(status="error").inc()
        logger.exception("session_name_generation_failed", session_id=session_id)


def maybe_name_session(session_id: str, session_name: str, messages: list) -> None:
    """会话未命名时触发自动命名.

    可从任意聊天接口安全调用；同一会话的并发调用会通过 Postgres 占用机制去重.
    """
    if session_name:
        return
    first_user_msg = next((m.content for m in messages if m.role == "user"), None)
    if not first_user_msg:
        return
    if _claim_session(session_id, _build_placeholder(first_user_msg)):
        task = asyncio.create_task(_persist_session_name(session_id, first_user_msg))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
