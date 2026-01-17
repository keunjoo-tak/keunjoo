# # =================================================================================================
# # hcb_api_main.py
# # -------------------------------------------------------------------------------------------------
# # 📘 역할 요약:
# #   - FastAPI 애플리케이션의 메인 진입점
# #   - 전역 CORS 설정 및 라우터(router.py) 포함
# #   - 앱 시작 시 Vertex AI 기반 모델 초기화 수행
# #   - 헬스체크 엔드포인트("/") 제공
# #
# # 📁 주요 의존 모듈:
# #   - router.py : /api/v1 하위 라우팅 담당
# #   - services.fupsheet.fupsheet_service : 모델 초기화 함수 제공
# #
# # ⚙️ 동작 순서:
# #   1) create_app() → FastAPI 인스턴스 생성
# #   2) on_startup 이벤트 시 initialize_fupsheet_model(), initialize_fupsheet_into_model() 실행
# #   3) "/" 경로 헬스체크 엔드포인트 제공
# #   4) uvicorn으로 직접 실행 시 로컬 개발 서버 실행
# #
# # 주의: 코드 본문은 원본 그대로이며, 추가된 것은 설명 주석뿐입니다.
# # ================================================================================================
# from __future__ import annotations
# from utils.path_utils import load_env

# load_env()

# import os
# import sys
# import logging
# from pathlib import Path
# from contextlib import asynccontextmanager

# import uvicorn
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from api.router import router as api_router

# # ✅ 추가: 전역 client 주입용
# from services.fupsheet import fupsheet_service
# from services.fupsheet import fupsheet_service_into

# from utils.gemini_client import GeminiClientProvider
# from utils.hcb_initializer import initialize_gemini_clients, initialize_oracle_client

# # --------------------------------------------------------------------------------------
# # Environment & Path
# # --------------------------------------------------------------------------------------
# ROOT = Path(__file__).resolve().parent
# if str(ROOT) not in sys.path:
#     sys.path.insert(0, str(ROOT))


# # --------------------------------------------------------------------------------------
# # Logging
# # --------------------------------------------------------------------------------------
# def configure_logging() -> None:
#     logging.basicConfig(
#         level=logging.INFO,
#         format="%(asctime)s - %(levelname)s - %(message)s",
#         datefmt="%Y-%m-%d %H:%M:%S",
#     )
#     logging.getLogger("watchfiles").setLevel(logging.WARNING)


# # --------------------------------------------------------------------------------------
# # Lifespan (startup/shutdown)
# # --------------------------------------------------------------------------------------
# @asynccontextmanager
# async def lifespan(_: FastAPI):
#     logging.info("🚀 FastAPI Lifespan startup: initializing HCB AI Services")
#     gc1, gc2 = initialize_gemini_clients()
#     fupsheet_service.initialize_fupsheet_model()
#     fupsheet_service_into.initialize_fupsheet_into_model()
#     if not (gc1 and gc2):
#         logging.error(
#             "❌ One or more gemini client failed to initialize. Service may be degraded."
#         )
#     oc = initialize_oracle_client()
#     if not oc:
#         logging.error(
#             "❌ One or more oracle client failed to initialize. Service may be degraded."
#         )
#     yield
#     logging.info("🧹 FastAPI Lifespan shutdown: done")


# # --------------------------------------------------------------------------------------
# # App Factory
# # --------------------------------------------------------------------------------------
# def create_app() -> FastAPI:
#     configure_logging()

#     app = FastAPI(
#         title="HDE AI Service API(고압차단기)",
#         description="HD현대일렉트릭(고압차단기) 생성형 AI 기반 서비스 API",
#         version="1.0.0",
#         root_path="/hdehcb-backend",
#         lifespan=lifespan,
#     )

#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=["*"],
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )

#     app.include_router(api_router, prefix="/api/v1")

#     @app.get("/health", tags=["health"])
#     async def healthcheck() -> dict:
#         deps = {
#             "gemini_sdk": (
#                 "available" if GeminiClientProvider.is_available() else "missing"
#             ),
#             "fupsheet_client": (
#                 "ready"
#                 if GeminiClientProvider.is_initialized("hcb_fupsheet")
#                 else "not_initialized"
#             ),
#             "fupsheet_into_client": (
#                 "ready"
#                 if GeminiClientProvider.is_initialized("hcb_fupsheet_into")
#                 else "not_initialized"
#             ),
#         }
#         return {
#             "status": "ok",
#             "message": "FastAPI 서버가 5005번 포트에서 실행 중입니다.",
#             "dependencies": deps,
#         }

#     # (선택) root_path 환경에서 직접 /hdehcb-backend/health로 들어오는 경우도 커버하고 싶으면:
#     @app.get("/hdehcb-backend/health")
#     async def healthcheck_with_prefix() -> dict:
#         return await healthcheck()

#     return app


# app = create_app()


# # --------------------------------------------------------------------------------------
# # Local Entrypoint
# # --------------------------------------------------------------------------------------
# if __name__ == "__main__":
#     print(
#         "🚀 HD현대일렉트릭 생성형 AI 기반 서비스(고압차단기) API 서버를 시작합니다..."
#     )
#     print("   - 접속 주소: http://127.0.0.1:5005")
#     print("   - API 문서: http://127.0.0.1:5005/docs")
#     print("   - FastAPI Swagger: http://node.hd-aic.com:32293/docs")

#     reload_excludes = [
#         "install/Noto_Sans_KR/static/*",
#         "install/Noto_Sans_KR/**",
#         "sevices/fupsheet/zip_archive/**",
#         "sevices/fupsheet/tmp/**",
#         ".venv/**",
#         "__pycache__/**",
#         "*.log",
#         "*.pdf",
#         "*.zip",
#     ]

#     uvicorn.run(
#         "hcb_api_main:app",
#         host="0.0.0.0",
#         port=5005,
#         reload=True,
#         reload_excludes=reload_excludes,
#     )

# # --------------------------------------------------------------------------------------
# # README
# # --------------------------------------------------------------------------------------
# """
# # uvicorn.run()을 사용하여 FastAPI 앱을 실행합니다.
# # "main:app"은 main.py 파일의 app 변수를 의미합니다.
# # host="0.0.0.0"은 모든 네트워크 인터페이스에서 접속을 허용합니다.
# # port=5005은 5005번 포트를 사용하도록 설정합니다.
# # reload=True는 코드 변경 시 서버를 자동으로 재시작하는 개발용 옵션입니다.
# # 사용중인 port 확인 방법 : lsof -i :5005
# # API 서버 강제 종료 : kill -9 [PID]
# # 서버 실행 명령 : nohup python hcb_api_main.py > hcb_api_main_output.log 2>&1 &

# # 오라클 클라이언트 문제시(서버 재부팅시) :
# # sudo mkdir -p /opt/oracle
# # cd /home/a524405/install
# # sudo unzip instantclient-basic-linux.x64-19.27.0.0.0dbru.zip
# # sudo mv instantclient_19_27 /opt/oracle/
# # export LD_LIBRARY_PATH=/opt/oracle/instantclient_19_27:$LD_LIBRARY_PATH

# --> 안되면
# echo "/opt/oracle/instantclient_19_27" | sudo tee /etc/ld.so.conf.d/oracle-instantclient.conf
# sudo ldconfig
# ldd /opt/oracle/instantclient_19_27/libclntsh.so   # 다시 확인


# # sudo apt-get update
# # 라이브러리 링크 확인 : ldd /opt/oracle/instantclient_19_27/libclntsh.so
# # 의존성 설치 : sudo apt-get install -y libaio1 libnsl2

# #
# """
