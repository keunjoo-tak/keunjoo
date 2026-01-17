# from fastapi import APIRouter

# # 각 도메인(공통, 고압차단기)의 엔드포인트 모듈
# from api.endpoints import common
# from api.endpoints import fupsheet
# from api.endpoints import fupsheet_into

# # 애플리케이션 전역 라우터
# # - 이 라우터에 하위 라우터들(common, fupsheet 등)을 포함시켜 URL 트리를 구성한다.
# router = APIRouter()

# # --------------------------------------------------------------------
# # 공통 영역 (Health check, 공통 유틸 등)
# #  - Base path: /common
# #  - Tags: ["공통"] → 문서화(Swagger)에서 그룹화용
# # --------------------------------------------------------------------
# router.include_router(common.router, prefix="/common", tags=["공통"])

# # --------------------------------------------------------------------
# # 고압차단기(HCV) 영역
# #  - Base path: /HCV
# #  - fupsheet: FUP Sheet 자동화 관련 API
# #  - fupsheet_into: (동일 도메인의 별도 하위 기능)
# #  - 두 라우터 모두 동일 prefix("/HCV") 아래에서 각각의 엔드포인트 path를 노출한다.
# # --------------------------------------------------------------------
# router.include_router(fupsheet.router, prefix="/HCV", tags=["고압차단기"])
# router.include_router(fupsheet_into.router, prefix="/HCV", tags=["고압차단기"])
