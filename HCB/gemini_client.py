# from __future__ import annotations

# import asyncio
# import logging
# import os
# import random
# from dataclasses import dataclass
# from pathlib import Path
# from typing import Dict, Any, Awaitable, Callable, Optional, TypeVar


# from aiohttp.client_exceptions import ClientOSError
# from google import genai


# logger = logging.getLogger(__name__)

# try:
#     import vertexai
#     from google import genai
#     from vertexai.generative_models import GenerativeModel  # type: ignore

#     VERTEX_AI_AVAILABLE = True
# except Exception:
#     GenerativeModel = object  # type: ignore
#     VERTEX_AI_AVAILABLE = False

# T = TypeVar("T")


# @dataclass(frozen=True)
# class GeminiConfig:
#     project_id: str
#     location: str
#     model_name: str
#     credentials_path: Optional[str] = None


# class GeminiClientProvider:
#     """
#     - 서비스별(key)로 Gemini client를 캐시하는 Provider
#     - FastAPI lifespan에서 initialize_* 호출 → 핸들러/서비스 레이어는 get_client만 사용
#     """

#     _clients: Dict[str, object] = {}
#     _vertexai_inited: bool = False

#     @classmethod
#     def is_available(cls) -> bool:
#         return VERTEX_AI_AVAILABLE

#     @classmethod
#     def is_initialized(cls, key: str = "default") -> bool:
#         return key in cls._clients

#     @classmethod
#     def initialize(cls, config: GeminiConfig, key: str = "default") -> object:
#         """
#         초기화가 이미 되어 있으면 기존 인스턴스를 반환합니다.
#         실패 시 예외를 발생시켜, lifespan에서 기동 실패 처리 가능하게 합니다.
#         """
#         if not VERTEX_AI_AVAILABLE:
#             raise RuntimeError(
#                 "Vertex AI / google-genai SDK가 설치되지 않았습니다. "
#                 "예) pip install -U 'google-genai' vertexai"
#             )

#         if key in cls._clients:
#             logger.info("Gemini client already initialized. key=%s", key)
#             return cls._clients[key]

#         credentials_path = config.credentials_path or os.getenv(
#             "GOOGLE_APPLICATION_CREDENTIALS"
#         )
#         if credentials_path:
#             cred = Path(credentials_path)
#             if not cred.exists():
#                 raise FileNotFoundError(
#                     f"Google Cloud credentials not found at: {cred}"
#                 )
#             os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred)

#         if not config.project_id or not config.location:
#             raise ValueError(
#                 "project_id / location is required to initialize Gemini client."
#             )

#         # vertexai.init()는 프로세스 단위 1회 호출이 보통 안전합니다.
#         if not cls._vertexai_inited:
#             vertexai.init(project=config.project_id, location=config.location)
#             cls._vertexai_inited = True

#         client = genai.Client(
#             vertexai=True, project=config.project_id, location=config.location
#         )
#         cls._clients[key] = client

#         logger.info(
#             "⏳ Gemini Client initialized. key=%s project=%s location=%s",
#             key,
#             config.project_id,
#             config.location,
#         )
#         return client

#     @classmethod
#     def get_client(cls, key: str = "default") -> object:
#         if key not in cls._clients:
#             raise RuntimeError(
#                 f"Gemini client is not initialized for key='{key}'. "
#                 "Call GeminiClientProvider.initialize(...) first."
#             )
#         return cls._clients[key]
