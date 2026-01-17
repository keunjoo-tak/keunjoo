# from __future__ import annotations
# import os
# from pathlib import Path
# from dotenv import load_dotenv


# def project_root() -> Path:
#     """
#     이 파일 위치 기준으로 상위로 올라가 프로젝트 루트 추정
#     예: /app/utils/path_utils.py -> /app
#     """
#     return Path(__file__).resolve().parents[1]


# def module_dir(module_file: str | Path) -> Path:
#     """
#     각 모듈 파일(__file__)을 넘기면 해당 모듈 디렉토리를 돌려준다.
#     사용처에서 MODULE_DIR을 안정적으로 계산하기 위한 헬퍼.
#     """
#     return Path(module_file).resolve().parent


# def load_env() -> None:
#     """
#     우선순위:
#       1) ENV_FILE (명시)
#       2) 프로젝트 루트의 .env_hcb
#       3) 현재 작업디렉토리의 .env_hcb
#     """
#     # ✅ 1. ENV_FILE 명시된 경우
#     env_file = os.getenv("ENV_FILE")
#     if env_file:
#         load_dotenv(env_file, override=True)
#         return

#     root_candidate = project_root() / ".env"
#     if root_candidate.exists():
#         load_dotenv(root_candidate, override=True)
#         return

#     cwd_candidate = Path.cwd() / ".env"
#     if cwd_candidate.exists():
#         load_dotenv(cwd_candidate, override=True)


# def resolve_path(p: str | None, default: Path) -> Path:
#     if not p:
#         return default

#     path = Path(p)

#     # 1) 상대경로면 project_root 기준으로
#     if not path.is_absolute():
#         path = project_root() / path

#     # 2) (옵션) 예전 값(/app/...)이 들어왔는데 로컬에서 없으면 project_root로 보정
#     if not path.exists() and str(path).startswith("/app/"):
#         candidate = project_root() / Path(str(path).removeprefix("/app/"))
#         if candidate.exists():
#             path = candidate

#     return str(path)


# def resolve_cred_path():
#     p = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
#     if not p:
#         return
#     path = Path(p)
#     if not path.is_absolute():
#         path = project_root() / path
#         os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path)


# resolve_cred_path()
