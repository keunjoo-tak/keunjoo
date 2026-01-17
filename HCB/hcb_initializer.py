# # utils/hcb_initializer.py
# # -------------------------------------------------------------------
# # 역할:
# #   - HCB(고압차단기) 서비스에서 사용하는 Gemini(Vertex AI) 클라이언트 초기화 로직을 utils로 분리
# #   - /health 의 GeminiClientProvider.is_initialized(...) 가 ready 가 되도록 Provider 초기화까지 수행
# #   - 서비스 레이어(fupsheet_service*.py)는 여기 함수를 호출하는 thin wrapper로 유지(A안)
# # -------------------------------------------------------------------
# from __future__ import annotations

# import logging
# import os
# from typing import Optional, Tuple
# import threading

# from utils.path_utils import load_env, resolve_cred_path
# from utils.gemini_client import GeminiClientProvider, GeminiConfig

# logger = logging.getLogger(__name__)

# DEFAULT_FUPSHEET_KEY = "hcb_fupsheet"
# DEFAULT_FUPSHEET_INTO_KEY = "hcb_fupsheet_into"


# def _ensure_env_loaded() -> None:
#     load_env()
#     resolve_cred_path()


# # -------------------------------------------------------------------
# # Initialize Gemini Client
# # -------------------------------------------------------------------
# def _build_gemini_config() -> GeminiConfig:
#     project_id = os.getenv("GCP_PROJECT_ID_HCB")
#     location = os.getenv("GCP_LOCATION")
#     model_name = os.getenv(key="GEMINI_MODEL_25P")
#     credentials_path: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
#     return GeminiConfig(
#         project_id=project_id,
#         location=location,
#         model_name=model_name,
#         credentials_path=credentials_path,
#     )


# def initialize_gemini_clients(
#     *,
#     fupsheet_key: str = DEFAULT_FUPSHEET_KEY,
#     fupsheet_into_key: str = DEFAULT_FUPSHEET_INTO_KEY,
# ) -> Tuple[object, object]:
#     """
#     앱 진입점에서 1회 호출을 위한 통합 초기화 함수.

#     - 내부적으로 Provider에 2개 key를 모두 initialize 해서
#       /health가 두 항목 모두 ready가 되게 유지한다.
#     - 반환: (fupsheet_client, fupsheet_into_client)
#     """
#     _ensure_env_loaded()
#     config = _build_gemini_config()

#     # ✅ "초기화 호출"은 1회지만, /health ready를 위해 key 2개를 모두 캐시에 올린다.
#     c1 = GeminiClientProvider.initialize(config=config, key=fupsheet_key)
#     c2 = GeminiClientProvider.initialize(config=config, key=fupsheet_into_key)

#     logger.info(f"✅ HCB Gemini clients ready. keys={fupsheet_key},{fupsheet_into_key}")
#     return c1, c2


# def initialize_gemini_client(key: str = DEFAULT_FUPSHEET_KEY) -> object:
#     """
#     (옵션) 단일 key 초기화가 필요한 경우를 위한 유틸.
#     - 대부분은 initialize_gemini_clients()를 사용 권장.
#     """
#     _ensure_env_loaded()
#     config = _build_gemini_config()
#     c = GeminiClientProvider.initialize(config=config, key=key)
#     logger.info(f"✅ HCB Gemini client ready. key={key}")
#     return c


# # -------------------------------------------------------------------
# # Initialize Oracle Instant Client
# # -------------------------------------------------------------------
# # 1회 초기화 보장
# _ORACLE_INIT_LOCK = threading.Lock()
# _ORACLE_INITIALIZED = False


# def initialize_oracle_client(
#     *,
#     lib_dir: str = "/opt/oracle/instantclient_19_27",
#     ld_library_path: str = "/opt/oracle/instantclient_19_27",
# ) -> object:
#     """
#     Oracle Instant Client(thick mode) 초기화.
#     - 성공 시 oracledb 모듈 객체를 반환
#     - 이미 초기화된 경우, 그대로 oracledb를 반환
#     """
#     global _ORACLE_INITIALIZED

#     with _ORACLE_INIT_LOCK:
#         if _ORACLE_INITIALIZED:
#             import oracledb  # noqa

#             return oracledb

#         os.environ["LD_LIBRARY_PATH"] = ld_library_path

#         try:
#             import oracledb  # noqa: E402

#             try:
#                 logger.info(
#                     f"⏳ Oracle client initializing... oracledb version={oracledb.__version__}"
#                 )
#                 oracledb.init_oracle_client(lib_dir=lib_dir)
#                 logger.info(
#                     f"✅ Oracle client initialized successfully. lib_dir={lib_dir}"
#                 )
#             except Exception as e:
#                 logger.warning(f"Oracle client init skipped/ignored: {e}")

#             _ORACLE_INITIALIZED = True
#             return oracledb

#         except Exception as e:
#             logger.exception(f"❌ Oracle client initialization failed: %{e}")
#             raise
