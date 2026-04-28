from __future__ import annotations

from openai import OpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai

from app.settings import settings


def get_openai_client() -> OpenAI:
    client = OpenAI(api_key=settings.openai_api_key)

    if settings.langsmith_tracing and settings.langsmith_api_key:
        return wrap_openai(client)

    return client


__all__ = ["traceable", "get_openai_client"]