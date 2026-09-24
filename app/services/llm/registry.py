"""预初始化 LLM 实例的模型注册表."""

from typing import (
    Any,
    Dict,
    List,
    cast,
)

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import settings
from app.core.logging import logger

_API_KEY = SecretStr(settings.OPENAI_API_KEY)

# 此处的模型均为推理模型.设置 `reasoning` 后，API 会因使用传统采样参数
# （`top_p`、`presence_penalty`、`frequency_penalty`）返回 400，应改用 `reasoning.effort` 调整质量.


class LLMRegistry:
    """包含预初始化实例的可用 LLM 模型注册表.

    该类维护 LLM 配置列表，并提供按名称获取模型及覆盖可选参数的方法.
    """

    # 按偏好排序：索引 0 是默认模型，也是循环回退链的起点，
    # 因此回退顺序为最新模型到成本最低模型.
    LLMS: List[Dict[str, Any]] = [
        {
            "name": "gpt-5.6-luna",
            "llm": ChatOpenAI(
                model="gpt-5.6-luna",
                api_key=_API_KEY,
                max_completion_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "medium"},
            ),
        },
        {
            "name": "gpt-5.4",
            "llm": ChatOpenAI(
                model="gpt-5.4",
                api_key=_API_KEY,
                max_completion_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "medium"},
            ),
        },
        {
            "name": "gpt-5.4-mini",
            "llm": ChatOpenAI(
                model="gpt-5.4-mini",
                api_key=_API_KEY,
                max_completion_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "low"},
            ),
        },
        {
            "name": "gpt-5.4-nano",
            "llm": ChatOpenAI(
                model="gpt-5.4-nano",
                api_key=_API_KEY,
                max_completion_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "low"},
            ),
        },
    ]

    @classmethod
    def get(cls, model_name: str, **kwargs) -> BaseChatModel:
        """按名称获取 LLM，并支持覆盖可选参数.

        提供 kwargs 时会返回应用这些覆盖参数的新 ChatOpenAI 实例，不修改注册表中的共享实例.

        参数：
            model_name: 要获取的模型名称.
            **kwargs: 用于覆盖默认模型配置的可选参数.

        返回：
            BaseChatModel 实例.

        异常：
            ValueError: model_name 不存在于 LLMS 时抛出.
        """
        model_entry = next((e for e in cls.LLMS if e["name"] == model_name), None)

        if not model_entry:
            available = ", ".join(e["name"] for e in cls.LLMS)
            raise ValueError(f"model '{model_name}' not found in registry. available models: {available}")

        if kwargs:
            # 使用注册项中的模型 ID，而不是直接复用注册表名称，
            # 避免名称与模型不一致时向 API 发送未知 ID.
            base_llm = cast(ChatOpenAI, model_entry["llm"])
            logger.debug(
                "creating_llm_with_custom_args",
                model_name=model_name,
                model=base_llm.model_name,
                custom_args=list(kwargs.keys()),
            )
            # 注意：这里保留令牌限制，但不携带每个注册项的 `reasoning`；
            # 如果调用方需要覆盖推理模型，应在此处补充该配置.
            return ChatOpenAI(
                model=base_llm.model_name,
                api_key=_API_KEY,
                max_completion_tokens=settings.MAX_TOKENS,
                **kwargs,
            )

        logger.debug("using_default_llm_instance", model_name=model_name)
        return model_entry["llm"]

    @classmethod
    def get_all_names(cls) -> List[str]:
        """按注册顺序返回全部模型名称.

        返回：
            List[str]: 模型名称列表.
        """
        return [e["name"] for e in cls.LLMS]

    @classmethod
    def get_model_at_index(cls, index: int) -> Dict[str, Any]:
        """返回指定索引处的模型注册项，索引越界时回到索引 0.

        参数：
            index: LLMS 中的索引.

        返回：
            模型注册项字典.
        """
        if 0 <= index < len(cls.LLMS):
            return cls.LLMS[index]
        return cls.LLMS[0]
