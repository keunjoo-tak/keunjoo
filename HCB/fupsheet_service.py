# # ========================================================================
# # 파일명: fupsheet_service.py
# # ------------------------------------------------------------------------
# # 역할:
# #   - 업로드 ZIP을 받아 PDF 오버레이/추출/Vertex AI 분석/결과 병합/DB 로깅 수행
# #   - 프롬프트 매니저 활용
# #   - 서비스 최상위 함수: process_fupsheet_documents
# # ========================================================================
# from __future__ import annotations
# import os
# import threading
# import asyncio
# import json
# import logging
# import zipfile
# import shutil
# import tempfile
# import io
# from datetime import datetime, timedelta, timezone
# import re
# from utils.path_utils import resolve_path, project_root
# from io import BytesIO
# from pypdf import PdfReader, PdfWriter
# import warnings
# import uuid


# from pathlib import Path
# from typing import List, Union, Optional, Dict, Any, Callable, Awaitable, TypeVar
# from tqdm import tqdm
# import fitz  # PyMuPDF

# # PDF 처리 라이브러리
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import letter

# # 폰트 등록 (한국어 지원)
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont

# from services.db_logging import insert_ai_service_history

# # FastAPI 업로드 파일 타입
# from fastapi import UploadFile
# from aiohttp.client_exceptions import ClientOSError
# import random

# # Google Vertex AI SDK
# from google import genai
# from google.genai import types

# try:
#     from vertexai.generative_models import (
#         GenerativeModel,
#         Part,
#         GenerationConfig,
#         HarmCategory,
#         HarmBlockThreshold,
#     )

#     VERTEX_AI_AVAILABLE = True
# except ImportError:
#     VERTEX_AI_AVAILABLE = False

# # 내부 모듈
# from constant import Service
# from services.fupsheet.PromptManager import PromptManager

# from api.endpoints.common import EmailRequest, send_email

# from utils.gemini_client import GeminiClientProvider

# # --------------------------------------------------------------------
# # 로깅 설정
# # --------------------------------------------------------------------
# logger = logging.getLogger(__name__)

# # ------------------------------------------------------------------------
# # 환경설정 및 상수
# # ------------------------------------------------------------------------
# MODULE_DIR = Path(__file__).resolve().parent
# SERVICE_DIR = MODULE_DIR.parent

# FUPSHEET_ZIP_DIR = MODULE_DIR / "zip_archive"
# FUPSHEET_ZIP_DIR.mkdir(parents=True, exist_ok=True)

# PROJECT = os.getenv("GCP_PROJECT_ID_HCB")
# LOCATION = os.getenv(key="GCP_LOCATION")
# FUPSHEET_MODEL_NAME = os.getenv(key="GEMINI_MODEL_25P")
# DEFAULT_PROMPT = SERVICE_DIR / "fupsheet_prompt.json"
# FUPSHEET_PROMPT_FILE_PATH = resolve_path(
#     os.getenv("FUPSHEET_PROMPT_FILE_PATH"), DEFAULT_PROMPT
# )

# FONT_PATH_ENV = os.getenv("NOTO_FONT_PATH")
# FONT_PATH = (
#     Path(FONT_PATH_ENV)
#     if FONT_PATH_ENV
#     else SERVICE_DIR / "fupsheet" / "NotoSansKR-Regular.ttf"
# )

# pdfmetrics.registerFont(
#     font=TTFont(
#         name="NotoSansKR-Regular",
#         filename=str(object=FONT_PATH),
#     )
# )

# # --------------------------------------------------------------------
# # 전역 상태 및 AI 응답 스키마
# # --------------------------------------------------------------------
# JOB_STATUS: Dict[str, Dict[str, Any]] = {}


# def _set_status(job_id: str, phase: str, state: str, message: str = "") -> None:
#     """
#     FUP Sheet 비동기 작업의 상태를 전역 딕셔너리에 기록한다.

#     Parameters
#     ----------
#     job_id : str
#         작업 고유 ID.
#     phase : str
#         처리 단계명 (예: START, FTP, UNZIP, AI, DB, DONE, ERROR 등).
#     state : str
#         상태 (예: RUNNING, SUCCESS, FAILED).
#     message : str, optional
#         부가 설명 메시지.
#     """
#     JOB_STATUS[job_id] = {
#         "job_id": job_id,
#         "phase": phase,
#         "state": state,
#         "message": message,
#         "updated_at": datetime.now().isoformat(timespec="seconds"),
#     }
#     logger.info(f"[JOB {job_id}] {phase} - {state} {message}")


# TYPE_RESPONSE_SCHEMA = types.Schema(
#     type=types.Type.ARRAY,
#     items=types.Schema(type=types.Type.STRING),  # ["360kV GIS", "180kV HGIS", ...]
# )

# RESPONSE_SCHEMA = {
#     "type": "ARRAY",
#     "items": {
#         "type": "OBJECT",
#         "properties": {
#             "SerialNumber": {"type": "STRING"},
#             "SwitchGearType": {"type": "STRING"},
#             "Category": {"type": "STRING"},
#             "Item": {"type": "STRING"},
#             "Value": {"type": "STRING"},
#             "Unit": {"type": "STRING"},
#             "Ref": {"type": "STRING"},
#             "Title": {"type": "STRING"},
#             "Page": {"type": "STRING"},
#         },
#         "required": [
#             "SerialNumber",
#             "SwitchGearType",
#             "Category",
#             "Item",
#             "Value",
#             "Unit",
#             "Ref",
#             "Title",
#             "Page",
#         ],
#         "propertyOrdering": [
#             "SerialNumber",
#             "SwitchGearType",
#             "Category",
#             "Item",
#             "Value",
#             "Unit",
#             "Ref",
#             "Title",
#             "Page",
#         ],
#     },
# }

# # 모델 객체 (전역 변수)
# client: Optional[Any] = None

# T = TypeVar("T")

# # =========================
# # Gemini 통신 안정화 유틸
# # =========================
# # 운영에서 조정(부하테스트 기반): 8~16부터 추천
# GEMINI_GLOBAL_MAX_CONCURRENCY = int(os.getenv("GEMINI_GLOBAL_MAX_CONCURRENCY", "12"))

# # ⚠️ 이 파일은 스레드/루프가 여러 개일 수 있어 "전역 asyncio.Semaphore"를 직접 공유하면 위험
# # -> 이벤트루프별로 세마포어를 따로 생성해 관리
# _LOOP_SEMAPHORES: Dict[int, asyncio.Semaphore] = {}

# # client reset은 스레드 간에도 보호 필요 -> threading.Lock 사용
# _CLIENT_RESET_TLOCK = threading.Lock()


# def _get_loop_semaphore() -> asyncio.Semaphore:
#     loop = asyncio.get_running_loop()
#     key = id(loop)
#     sem = _LOOP_SEMAPHORES.get(key)
#     if sem is None:
#         sem = asyncio.Semaphore(GEMINI_GLOBAL_MAX_CONCURRENCY)
#         _LOOP_SEMAPHORES[key] = sem
#         logger.info(
#             f"[GeminiLimiter] init semaphore for loop={key}, max={GEMINI_GLOBAL_MAX_CONCURRENCY}"
#         )
#     return sem


# def _is_transient_gemini_error(e: Exception) -> bool:
#     msg = str(e).lower()
#     return (
#         isinstance(
#             e, (BrokenPipeError, ConnectionResetError, TimeoutError, ClientOSError)
#         )
#         or "broken pipe" in msg
#         or "connection reset" in msg
#         or "server disconnected" in msg
#         or "timeout" in msg
#     )


# async def _with_gemini_limit(coro: Awaitable[T]) -> T:
#     sem = _get_loop_semaphore()
#     async with sem:
#         return await coro


# async def _retry_gemini(
#     fn: Callable[[], Awaitable[T]],
#     *,
#     max_retries: int = 3,
#     base_delay: float = 0.8,
#     jitter: float = 0.3,
# ) -> T:
#     last_exc: Exception | None = None
#     for attempt in range(max_retries + 1):
#         try:
#             return await _with_gemini_limit(fn())
#         except Exception as e:
#             last_exc = e
#             if not _is_transient_gemini_error(e) or attempt == max_retries:
#                 raise
#             # 지수 백오프 + 약간의 지터
#             delay = base_delay * (2**attempt) + random.uniform(0, jitter)
#             logger.warning(
#                 f"Gemini transient error -> retry {attempt+1}/{max_retries}, sleep={delay:.2f}s, err={e}"
#             )
#             await asyncio.sleep(delay)

#     assert last_exc is not None
#     raise last_exc


# async def _reset_gemini_client_if_needed(e: Exception) -> None:
#     """스레드/루프 어디서든 호출 가능(동기 함수)."""
#     if not _is_transient_gemini_error(e):
#         return
#     global client
#     async with _CLIENT_RESET_TLOCK:
#         try:
#             # ✅ reset도 Provider 기반으로 수행(캐시 갱신 목적)
#             client = GeminiClientProvider.get_client("hcb_fupsheet")
#             logger.warning(
#                 "Gemini client has been reset due to transient transport error."
#             )
#         except Exception as reset_err:
#             logger.error(f"Gemini client reset failed: {reset_err}")


# # -------------------------------------------------------------------
# # AI 모델 초기화
# # -------------------------------------------------------------------
# def initialize_fupsheet_model() -> object:
#     """
#     ⚠️ DEPRECATED
#     - 앱 진입점(hcb_api_main.py)에서는 utils.initialize_hcb_dependencies()를 사용하세요.
#     - 이 함수는 하위 호환 및 단독 실행/테스트를 위해 유지됩니다.
#     """
#     warnings.warn(
#         "initialize_fupsheet_model() is deprecated. "
#         "Use utils.initialize_hcb_dependencies() at application entrypoint.",
#         DeprecationWarning,
#         stacklevel=2,
#     )
#     global client

#     try:
#         client = GeminiClientProvider.get_client("hcb_fupsheet")
#         logger.info(
#             f"Vertex AI 초기화 완료(FUPSHEET): project={PROJECT}, location={LOCATION}"
#         )
#         return client
#     except Exception as e:
#         logger.exception(f"FUPSHEET gemini client 초기화 중 심각한 오류 발생: {e}")
#         return None


# # -------------------------------------------------------------------
# # 내부 헬퍼: 특정 SwitchGearType 상세 추출
# # -------------------------------------------------------------------
# async def _extract_details_for_switchgear_type(
#     switchgear_type: str,
#     # filtered_entries: list,
#     description_prompt: str,
#     format_prompt: str,
#     pdf_parts: list,
#     generate_content_config: dict,
#     client: Any,
#     semaphore: asyncio.Semaphore,
#     group_name: str = "",
#     max_retries: int = 3,
#     base_delay: float = 2.0,
# ) -> Optional[list]:
#     """
#     병렬 처리 전용 함수.
#     특정 switchgear_type에 대해 AI 모델로 상세 사양을 추출.
#     """
#     async with semaphore:  # 동시 요청 수 제어
#         label = f"{switchgear_type}[{group_name}]" if group_name else switchgear_type
#         logger.info(f"'{label}' 상세 추출 시작...")

#         instruction_prompt = f"""
#         ## Variable Definition
#         - SwitchgearType: The standard field name for the combination of Nominal System Voltage and Switchgear Type (e.g., "132 kV GIS").
#         - Always use "SwitchgearType" (case-sensitive) as the field name in all outputs and subsequent prompts.

#         ## Scope & Source
#         - Analyze the provided PDF document and extract information based on the categories and specification items defined in ## Given Text ##.
#         - Use information explicitly stated in project-binding contexts (Project Spec / SOW / BOQ / project datasheets / drawings).
#         - General Standards inside the PDF are auxiliary only and may be used only if the PDF explicitly makes them binding for this project.

#         ## Context Binding
#         - Set SwitchgearType = "{switchgear_type}"
#         - Assume SwitchgearType is already validated and uniquely defined in the previous step.
#         - Do not revalidate voltage/type pairing unless ambiguity is detected.
#         - Proceed to extract item specifications directly within the context relevant to the given SwitchgearType.

#         ## Extraction Rules
#         - For each of the specification items (see note in conflicts), extract the value as it applies to the validated SwitchgearType context.
#         - Follow the provided Description and AI Extraction Logic for each item strictly.
#         - Do not infer values or cross-reference unrelated contexts.
#         - If not specified → leave blank.

#         ## Conflict Resolution
#         - If multiple thresholds exist, always choose the more conservative requirement.

#         ## Output Format
#         - Output must follow the JSON array format defined in format_prompt.
#         - Ensure completeness: provide values for all items corresponding to the validated SwitchgearType.

#         ## Field-Level Truncation
#         - For any single string field exceeding 300 characters, truncate to the first 290 ASCII characters and append '.....'
#         - Maintain valid JSON formatting after truncation.
#         """
#         user_prompt = instruction_prompt + description_prompt + format_prompt
#         text_parts2 = types.Part.from_text(text=user_prompt)

#         # 입력 토큰 확인
#         token_info2 = await _retry_gemini(
#             lambda: client.aio.models.count_tokens(
#                 model=FUPSHEET_MODEL_NAME, contents=[text_parts2, *pdf_parts]
#             ),
#             max_retries=3,
#         )
#         logger.info(
#             f"[{switchgear_type}Token Count] 입력 토큰 수: {token_info2.total_tokens}"
#         )
#         if token_info2.total_tokens > 1000000:
#             raise ValueError("최대 입력 토큰수를 초과하였습니다.")

#         # --- 최대 max_retries 만큼 재시도 ---
#         for attempt in range(max_retries + 1):
#             try:
#                 if attempt > 0:
#                     logger.warning(
#                         f"'{switchgear_type}' 처리 재시도 ({attempt}/{max_retries})..."
#                     )
#                     await asyncio.sleep(2)

#                 response = await _retry_gemini(
#                     lambda: client.aio.models.generate_content(
#                         model=FUPSHEET_MODEL_NAME,
#                         contents=[text_parts2, *pdf_parts],
#                         config=generate_content_config,
#                     ),
#                     max_retries=2,  # 내부 루프도 있으니 여기서는 2 정도로 줄여도 됨
#                 )

#                 if not response.candidates:
#                     logger.warning(
#                         f"'{switchgear_type}' 처리 실패 (차단 가능성). 피드백: {response.prompt_feedback}"
#                     )
#                     continue

#                 res2 = response.text.strip()
#                 if not res2:
#                     logger.warning(f"'{switchgear_type}' 처리 실패 (빈 응답).")
#                     continue

#                 # 마크다운 블록 제거
#                 if res2.startswith("```json"):
#                     res2 = res2[len("```json") :].strip()
#                 if res2.endswith("```"):
#                     res2 = res2[: -len("```")].strip()

#                 res_json = json.loads(res2)
#                 if isinstance(res_json, dict):
#                     # 혹시 모델이 단일 객체로 반환할 경우 배열로 감싸기
#                     res_json = [res_json]
#                 if not isinstance(res_json, list):
#                     raise ValueError(f"'{label}' 응답이 list가 아님: {type(res_json)}")

#                 logger.info(f"'{label}' 상세 추출 성공. entries={len(res_json)}")
#                 return res_json

#             except json.JSONDecodeError as e:
#                 logger.error(f"'{switchgear_type}' JSON 파싱 오류: {e}")
#             except Exception as e:
#                 logger.error(f"'{switchgear_type}' 처리 오류: {e}")

#         logger.error(f"'{switchgear_type}' 처리 실패 (모든 재시도 소진).")
#         return None


# # --------------------------------------------------------------------
# # 3) JSON 유틸리티
# # --------------------------------------------------------------------


# def _sanitize_value(v: Optional[str]) -> str:
#     """
#     생성 결과에서 Placeholder 또는 의미 없는 값을 공백 문자열로 정규화한다.

#     - DB에는 빈 문자열로 저장하며,
#       필요 시 DB 레벨에서 NULL로 변환할 수 있다.
#     """
#     if v is None:
#         return ""
#     s = str(v).strip()
#     if not s:
#         return ""

#     placeholders = {
#         "none",
#         "not specified",
#         "n/a",
#         "na",
#         "-",
#         "null",
#         "n.a.",
#         "—",
#         "tbd",
#         "to be decided",
#         "to be defined",
#     }
#     return "" if s.lower() in placeholders else s


# def _sanitize_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     """
#     결과 배열 전체에 대해 Value/Unit/Ref/Title/Page를 정규화한다.
#     """
#     cleaned: List[Dict[str, Any]] = []
#     for item in results:
#         new_item = dict(item)
#         for key in ["Value", "Unit", "Ref", "Title", "Page"]:
#             if key in new_item:
#                 new_item[key] = _sanitize_value(new_item[key])
#         cleaned.append(new_item)
#     return cleaned


# # -------------------------------------------------------------------
# # PDF 유틸 함수
# # -------------------------------------------------------------------
# async def get_pdf_list(path: str) -> List[str]:
#     """
#     주어진 폴더 내의 PDF 파일 경로 목록을 반환한다.
#     """
#     pdf_list: List[str] = []
#     for item in os.listdir(path):
#         if item.lower().endswith(".pdf"):
#             pdf_list.append(os.path.join(path, item))
#     return pdf_list


# async def create_overlay_pdf(
#     filename: str, page_num: int, total_pages: int, pagesize
# ) -> PdfReader:
#     """
#     각 PDF 페이지 하단에 파일명/페이지 정보를 출력하는 overlay PDF를 메모리 상에 생성한다.

#     Notes
#     -----
#     - "NotoSansKR-Regular" 폰트는 외부에서 사전 등록되어 있어야 한다.
#     """
#     packet = io.BytesIO()
#     can = canvas.Canvas(packet, pagesize=pagesize)
#     can.setFont("NotoSansKR-Regular", 8)

#     margin_right, margin_bottom, line_gap = 10, 2, 12
#     text1 = f'Filename : "{filename}"'
#     text2 = f'Page : "{page_num}/{total_pages}"'

#     width, height = float(pagesize[0]), float(pagesize[1])
#     can.drawRightString(width - margin_right, margin_bottom + line_gap, text1)
#     can.drawRightString(width - margin_right, margin_bottom, text2)
#     can.save()
#     packet.seek(0)

#     return PdfReader(packet)


# async def overlay_pdf(
#     input_pdf_path: Union[str, Path], output_pdf_path: Union[str, Path]
# ) -> None:
#     """
#     원본 PDF의 각 페이지에 overlay(파일명/페이지 정보)를 병합하여 새로운 PDF를 저장한다.
#     """
#     pdf_reader = PdfReader(str(input_pdf_path))
#     pdf_writer = PdfWriter()
#     filename = os.path.basename(str(input_pdf_path))
#     total_pages = len(pdf_reader.pages)

#     for page_index, page in enumerate(pdf_reader.pages, start=1):
#         overlay_pdf_reader = await create_overlay_pdf(
#             filename, page_index, total_pages, page.mediabox[2:4]
#         )
#         page.merge_page(overlay_pdf_reader.pages[0])
#         pdf_writer.add_page(page)

#     with open(output_pdf_path, "wb") as f:
#         pdf_writer.write(f)


# # ==============================
# # [ADD] Large PDF handling helpers
# # - place this block AFTER overlay_pdf()
# #   and BEFORE _process_documents_with_ai()
# # ==============================

# MAX_INLINE_PDF_BYTES = int(os.getenv("MAX_INLINE_PDF_BYTES", "8000000"))  # 8MB
# MAX_INLINE_PDF_PAGES = int(os.getenv("MAX_INLINE_PDF_PAGES", "200"))
# MAX_TEXT_CHARS_PER_CHUNK = int(os.getenv("MAX_TEXT_CHARS_PER_CHUNK", "120000"))


# def _chunk_text(text: str, limit: int) -> list[str]:
#     if not text:
#         return []
#     return [text[i : i + limit] for i in range(0, len(text), limit)]


# def _extract_pdf_text_with_page_markers(pdf_path: Path) -> str:
#     """
#     PyPDF2 기반 텍스트 추출 + 페이지 마커 삽입
#     (대형 PDF를 bytes로 보내지 않고 텍스트로 전환하기 위함)
#     """
#     reader = PdfReader(str(pdf_path))
#     out = []
#     for idx, page in enumerate(reader.pages, start=1):
#         t = page.extract_text() or ""
#         t = t.strip()
#         if t:
#             out.append(f"\n\n[FILE:{pdf_path.name}][PAGE:{idx}]\n{t}")
#     return "".join(out).strip()


# async def _split_pdf_into_byte_parts(pdf_path: Path) -> list[types.Part]:
#     """
#     스캔 PDF 등 텍스트 추출이 거의 안 되는 대형 PDF fallback:
#     페이지를 여러 조각 PDF로 나눠 bytes로 전송
#     """
#     reader = PdfReader(str(pdf_path))
#     total = len(reader.pages)

#     parts: list[types.Part] = [
#         types.Part.from_text(
#             text=f"[File:{pdf_path.name}] (SPLIT PDF MODE, pages={total})"
#         )
#     ]

#     start = 0
#     chunk_pages = 20  # 필요 시 자동 축소
#     while start < total:
#         end = min(start + chunk_pages, total)

#         writer = PdfWriter()
#         for i in range(start, end):
#             writer.add_page(reader.pages[i])

#         buf = io.BytesIO()
#         writer.write(buf)
#         data = buf.getvalue()

#         # 너무 크면 chunk를 줄여 재시도
#         if len(data) > MAX_INLINE_PDF_BYTES and chunk_pages > 1:
#             chunk_pages = max(1, chunk_pages // 2)
#             continue

#         parts.append(types.Part.from_text(text=f"[PDF_CHUNK pages {start+1}-{end}]"))
#         parts.append(types.Part.from_bytes(data=data, mime_type="application/pdf"))
#         start = end

#     return parts


# async def _build_parts_for_pdf(pdf_file_path: Path) -> list[types.Part]:
#     """
#     PDF 1개를 model input parts로 변환
#     - 작으면 overlay 결과를 PDF bytes로 전송
#     - 크면 텍스트 추출/청크로 전환(또는 split pdf fallback)
#     """
#     size = pdf_file_path.stat().st_size
#     reader = PdfReader(str(pdf_file_path))
#     pages = len(reader.pages)

#     # (1) 큰 PDF는 TEXT MODE
#     if size > MAX_INLINE_PDF_BYTES or pages > MAX_INLINE_PDF_PAGES:
#         logger.warning(
#             f"Large PDF -> TEXT MODE: file={pdf_file_path.name}, size={size}, pages={pages}"
#         )
#         text = _extract_pdf_text_with_page_markers(pdf_file_path)

#         # 텍스트가 거의 없으면(스캔 PDF 등) split pdf fallback
#         if len(text) < 1000:
#             logger.warning(
#                 f"Text empty -> SPLIT PDF MODE fallback: file={pdf_file_path.name}"
#             )
#             return await _split_pdf_into_byte_parts(pdf_file_path)

#         chunks = _chunk_text(text, MAX_TEXT_CHARS_PER_CHUNK)
#         parts = [
#             types.Part.from_text(
#                 text=f"[File:{pdf_file_path.name}] (TEXT MODE, pages={pages})"
#             )
#         ]
#         parts += [types.Part.from_text(text=c) for c in chunks]
#         return parts

#     # (2) 작은 PDF는 overlay를 별도 파일로 만들고 bytes 전송 (원본 덮어쓰기 금지)
#     overlay_path = pdf_file_path.with_suffix(".overlay.pdf")
#     await overlay_pdf(pdf_file_path, overlay_path)
#     pdf_bytes = overlay_path.read_bytes()

#     # 최소 헤더 검증(문제 데이터 빠른 식별)
#     if not pdf_bytes.startswith(b"%PDF"):
#         raise ValueError(f"Invalid PDF header after overlay: {pdf_file_path.name}")

#     # ✅ 라벨은 텍스트 part로 분리 (PDF bytes에 prepend 금지)
#     return [
#         types.Part.from_text(text=f"[File:{pdf_file_path.name}]"),
#         types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
#     ]


# # -------------------------------------------------------------------
# # 문서 처리 (AI 모델 활용)
# # -------------------------------------------------------------------
# # async def _process_documents_with_ai(pdf_directory: Union[str, Path]) -> Dict[str, Any]:
# async def _process_documents_with_ai(
#     pdf_directory: Union[str, Path],
# ) -> List[Dict[str, Any]]:
#     """
#     내부 함수: PDF를 AI 모델로 처리하고 결과를 반환
#     - PromptManager 로드
#     - PDF overlay 추가
#     - Vertex AI 호출
#     - SwitchGearType 별 상세 병렬 처리
#     """
#     global client
#     if client is None:
#         try:
#             client = GeminiClientProvider.get_client("hcb_fupsheet")
#         except Exception:
#             raise ValueError("FUPSHEET_Document_AI_model_is_not_available")

#     # 1. 프롬프트 로드
#     prompt_manager = PromptManager(FUPSHEET_PROMPT_FILE_PATH)
#     sys_prompt = prompt_manager.get_text("sys_prompt")
#     switchgeartype_prompt = prompt_manager.get_text("switchgeartype_prompt")
#     description_prompt_A_H = prompt_manager.get_text("description_prompt_A_H")
#     description_prompt_I_U = prompt_manager.get_text("description_prompt_I_U")
#     format_prompt = prompt_manager.get_text("format_prompt")
#     # instruction_prompt = prompt_manager.get_text("instruction_prompt")
#     CATEGORY_GROUPS = {
#         "A_H": description_prompt_A_H,
#         "I_S": description_prompt_I_U,
#     }
#     if not all(
#         [
#             sys_prompt,
#             switchgeartype_prompt,
#             description_prompt_A_H,
#             description_prompt_I_U,
#             format_prompt,
#         ]
#     ):
#         raise ValueError("프롬프트 로드 실패")

#     text_parts = types.Part.from_text(text=switchgeartype_prompt)

#     # 2. PDF 파일 수집 및 overlay 적용
#     pdf_dir_path = Path(pdf_directory)
#     pdf_files_found = list(pdf_dir_path.glob("*.pdf")) + list(
#         pdf_dir_path.glob("*.PDF")
#     )
#     if not pdf_files_found:
#         raise ValueError("No_PDF_files_found_in_zip")

#     pdf_parts = []
#     for pdf_file_path in pdf_files_found:
#         try:
#             # ✅ 대형/특수 PDF 대응: 크면 텍스트 모드, 작으면 overlay+bytes 모드
#             pdf_parts.extend(await _build_parts_for_pdf(pdf_file_path))
#             logger.info(f"성공적으로 PDF 데이터 추가: {pdf_file_path.name}")
#         except Exception as e:
#             logger.error(f"'{pdf_file_path}' 파일 처리 중 오류: {e}")
#             raise ValueError("Error_preparing_PDF_documents")

#     # --- Vertex AI 호출 ---
#     sgt_config = types.GenerateContentConfig(
#         # system_instruction=[types.Part.from_text(text=sys_prompt)],
#         temperature=0.01,
#         top_p=0.95,
#         seed=5001,
#         max_output_tokens=65535,
#         response_mime_type="application/json",
#         response_schema=TYPE_RESPONSE_SCHEMA,
#     )

#     generate_content_config = types.GenerateContentConfig(
#         system_instruction=[types.Part.from_text(text=sys_prompt)],
#         temperature=0.01,
#         top_p=0.95,
#         seed=5001,
#         max_output_tokens=65535,
#         response_mime_type="application/json",
#         response_schema=RESPONSE_SCHEMA,
#     )

#     try:
#         logger.info(f"{len(pdf_files_found)}개의 PDF로 FUPSHEET 분석 요청 전송 중...")

#         token_info = await _retry_gemini(
#             lambda: client.aio.models.count_tokens(
#                 model=FUPSHEET_MODEL_NAME, contents=[text_parts, *pdf_parts]
#             ),
#             max_retries=3,
#         )
#         logger.info(f"[Token Count] 입력 토큰 수: {token_info.total_tokens}")
#         if token_info.total_tokens > 1000000:
#             raise ValueError("최대 입력 토큰수를 초과하였습니다.")

#         response = await _retry_gemini(
#             lambda: client.aio.models.generate_content(
#                 model=FUPSHEET_MODEL_NAME,
#                 contents=[text_parts, *pdf_parts],
#                 config=sgt_config,
#             ),
#             max_retries=3,
#         )

#         res1 = response.text.strip()
#         print("switchgear type 리스트 : ", res1)

#         # 마크다운 블록 제거
#         if res1.startswith("```json"):
#             res1 = res1[len("```json") :].strip()
#         if res1.endswith("```"):
#             res1 = res1[: -len("```")].strip()

#         logger.info(f"[Raw switchgear type 응답] {res1}")

#         try:
#             res1_json = json.loads(res1)
#             if not isinstance(res1_json, list):
#                 raise ValueError(
#                     f"SwitchgearType 응답이 list 형식이 아닙니다: {type(res1_json)}"
#                 )
#         except json.JSONDecodeError:
#             logger.error(f"AI 응답 JSON 파싱 실패. 원본: {res1}")
#             raise ValueError("AI_model_response_was_not_valid_JSON")

#         # --- 병렬 처리 ---
#         unique_types: list[str] = res1_json
#         semaphore = asyncio.Semaphore(10)

#         # 5. 2차 병렬 호출: SwitchgearType + 카테고리 그룹 단위로 상세 추출
#         tasks: List[asyncio.Task] = []
#         for sg_type in unique_types:
#             for group_name, desc_prompt in CATEGORY_GROUPS.items():
#                 tasks.append(
#                     _extract_details_for_switchgear_type(
#                         switchgear_type=sg_type,
#                         description_prompt=desc_prompt,
#                         format_prompt=format_prompt,
#                         pdf_parts=pdf_parts,
#                         generate_content_config=generate_content_config,
#                         client=client,
#                         semaphore=semaphore,
#                         group_name=group_name,
#                     )
#                 )

#         logger.info(
#             f"{len(tasks)}개의 모델 병렬 호출 및 item spec 추출 시작... \n switchgear type list : {res1}"
#         )
#         parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

#         merged_results: List[Dict[str, Any]] = []
#         for result in parallel_results:
#             if isinstance(result, Exception):
#                 logger.error(f"병렬 작업 오류: {result}")
#             elif result is not None:
#                 merged_results.extend(result)

#         return merged_results

#     except json.JSONDecodeError:
#         logger.error(f"AI 응답 JSON 파싱 실패. 원본: {res1}...")
#         raise ValueError("AI_model_response_was_not_valid_JSON")
#     except Exception as e:
#         logger.exception(f"Gemini 통신 오류: {e}")
#         await _reset_gemini_client_if_needed(e)
#         if "safety" in str(e).lower():
#             raise ValueError("AI_request_blocked_by_safety_settings")
#         raise ValueError("Error_processing_documents_with_AI_model")


# # -------------------------------------------------------------------
# # 최상위 서비스 함수
# # -------------------------------------------------------------------
# KST = timezone(timedelta(hours=9))
# SERVICE_CD = Service.HCB_FUP_SW.value[0]
# SERVICE_NM = Service.HCB_FUP_SW.value[1]


# async def process_fupsheet_documents(
#     file: UploadFile,
#     *,
#     session_id: str | None = None,
#     user_id: str | None = None,
#     user_name: str | None = None,
#     company: str | None = None,
#     department: str | None = None,
#     user_email: str | None = None,
#     processing_time_ms: int | None = None,
# ) -> Dict[str, Any]:
#     """
#     업로드된 ZIP 파일을 처리하고 AI 분석을 수행
#     1. ZIP 임시 저장 및 압축 해제
#     2. 내부 AI 처리 함수 호출
#     """
#     report_file_path: str | None = None
#     status = "SUCCESS"
#     err_msg = None

#     # ---- [FIX] finally에서 참조되는 변수는 미리 초기화 ----
#     temp_zip_path: Path | None = None
#     start_ts: datetime | None = None
#     end_ts: datetime | None = None
#     ai_result: Any = None
#     persist_zip_path: Path | None = None

#     try:
#         if not session_id:
#             session_id = uuid.uuid4().hex  # 서버측 방어 로직
#         if not file.filename.lower().endswith(".zip"):
#             raise ValueError("Invalid_file_type_not_a_zip")

#         with tempfile.TemporaryDirectory() as temp_dir:
#             safe_name = Path(file.filename).name
#             temp_zip_path = Path(temp_dir) / safe_name

#             # --- ZIP 저장 ---
#             try:
#                 with open(temp_zip_path, "wb") as buffer:
#                     shutil.copyfileobj(file.file, buffer)
#             except Exception as e:
#                 logger.error(f"업로드 파일 저장 실패: {e}")
#                 raise IOError("Failed_to_save_uploaded_zip")
#             finally:
#                 await file.close()

#             # ✅ [추가] 영구 보관용 경로로 복사
#             ts = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
#             try:
#                 persist_zip_path = FUPSHEET_ZIP_DIR / f"{ts}_{session_id}_{safe_name}"
#                 logger.info(f"zip arcive dir: {persist_zip_path}")
#                 shutil.copy2(temp_zip_path, persist_zip_path)
#                 logger.info(
#                     f"zip persisted: {persist_zip_path} size={persist_zip_path.stat().st_size}"
#                 )
#             except Exception as e:
#                 logger.exception(
#                     f"persist failed: src={temp_zip_path}, dst={persist_zip_path}, err={e}"
#                 )
#                 raise

#             # --- ZIP 해제 ---
#             extracted_path = Path(temp_dir) / "extracted_pdfs"
#             extracted_path.mkdir()
#             try:
#                 with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
#                     zip_ref.extractall(extracted_path)
#             except zipfile.BadZipFile:
#                 raise ValueError("Invalid_ZIP_file_content")
#             except Exception as e:
#                 logger.error(f"ZIP 파일 압축 해제 실패: {e}")
#                 raise IOError("Failed_to_extract_zip")

#             # --- AI 분석 수행 ---
#             # 처리 시작/종료 시각 측정
#             start_ts = datetime.now(KST)
#             ai_result = await _process_documents_with_ai(extracted_path)
#             end_ts = datetime.now(KST)

#             # 성공 로깅 (에러 없이 결과가 있다면)
#             logger.info(
#                 f"DB 저장중 - company_cd:{company} / dept_nm:{department} / user_nm:{user_name}"
#             )

#     except Exception as e:
#         status = "FAIL"
#         err_msg = str(e)
#         logger.error(f"F-up Sheet 실행 오류: {e}", exc_info=True)
#         ai_result = {"status": "FAIL", "error_message": str(e)}
#         raise

#     finally:
#         # ---- [FIX] end_ts가 없으면 현재로라도 찍어서 로깅 ----
#         if start_ts is None:
#             start_ts = datetime.now(KST)
#         if end_ts is None:
#             end_ts = datetime.now(KST)
#         try:
#             insert_ai_service_history(
#                 session_id=session_id,
#                 company_cd=company,
#                 dept_nm=department,
#                 service_cd=SERVICE_CD,
#                 service_nm=SERVICE_NM,
#                 user_id=user_id,
#                 user_nm=user_name,
#                 user_email=user_email,
#                 input_filepath=(
#                     str(object=persist_zip_path) if persist_zip_path else None
#                 ),  # 업로드된 ZIP의 경로
#                 output_filepath=None,  # (필요 시 결과물 경로)
#                 start_dt=start_ts,
#                 end_dt=end_ts,
#                 status=status,
#                 err_msg=err_msg,
#                 response_json=ai_result,
#             )

#             if user_email:
#                 try:
#                     if status == "SUCCESS":
#                         email_req = EmailRequest(
#                             subject=f"[HDE_AI] {SERVICE_NM} 작업 완료",
#                             service=SERVICE_NM,
#                             from_addr="hde_ai_service@hd.com",
#                             to_addrs=[user_email],
#                             is_html=False,
#                             body=(
#                                 f"{SERVICE_NM} 작업이 완료되었습니다.\n"
#                                 f"- session_id: {session_id}\n"
#                                 f"- start: {start_ts}\n"
#                                 f"- end: {end_ts}\n"
#                             ),
#                         )
#                         await send_email(email_req)
#                         logger.info(
#                             f"완료 메일 발송 성공: to={user_email}, service={SERVICE_NM}"
#                         )
#                     else:
#                         email_req = EmailRequest(
#                             subject=f"[HDE_AI] {SERVICE_NM} 작업 실패",
#                             service=SERVICE_NM,
#                             from_addr="hde_ai_service@hd.com",
#                             to_addrs=[user_email],
#                             is_html=False,
#                             body=(
#                                 f"{SERVICE_NM} 작업이 실패했습니다.\n\n"
#                                 f"- session_id: {session_id}\n"
#                                 f"- 파일정보: {persist_zip_path}\n"
#                                 f"- start: {start_ts}\n"
#                                 f"- end: {end_ts}\n"
#                                 f"- error: {err_msg}\n"
#                             ),
#                         )
#                         await send_email(email_req)
#                         logger.info(
#                             f"실패 메일 발송 성공: to={user_email}, service={SERVICE_NM}"
#                         )

#                 except Exception as mail_err:
#                     logger.warning(f"메일 발송 실패: {mail_err}")
#             else:
#                 logger.info("user_email 미입력으로 메일 발송을 생략합니다.")

#         except Exception as log_err:
#             logger.exception(f"FUPSHEET 로그 기록 실패(성공 케이스): {log_err}")

#         return ai_result
