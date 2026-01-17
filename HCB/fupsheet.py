# from typing import Any
# import time
# from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Form


# from services.fupsheet import fupsheet_service

# # FastAPI Router 인스턴스
# router = APIRouter()

# # --- 에러 메시지 매핑 사전 ---
# # 서비스 계층(fupsheet_service)에서 발생하는 ValueError 키값에 따라
# # HTTP 상태 코드 및 사용자 메시지를 매핑
# ERROR_MESSAGES = {
#     "FUPSHEET_Document_AI_model_is_not_available": (
#         503,
#         "문서 분석 AI 서비스를 현재 사용할 수 없습니다. 관리자에게 문의하세요.",
#     ),
#     "AI_request_blocked_by_safety_settings": (
#         400,
#         "문서 분석 AI 모델 요청이 안전 설정에 의해 차단되었습니다. 입력 파일 내용을 확인해주세요.",
#     ),
#     "AI_model_response_was_not_valid_JSON": (
#         500,
#         "문서 분석 AI 모델로부터 유효한 JSON 형식의 응답을 받지 못했습니다. 다시 시도해주세요.",
#     ),
#     "Error_preparing_PDF_documents": (
#         500,
#         "문서 분석을 위한 PDF 파일 준비 중 오류가 발생했습니다.",
#     ),
#     "Error_processing_documents_with_AI_model": (
#         500,
#         "AI 모델로 문서를 처리하는 중 오류가 발생했습니다.",
#     ),
#     "Invalid_ZIP_file_content": (400, "잘못된 ZIP 파일입니다."),
#     "No_PDF_files_found_in_zip": (400, "ZIP 파일 내에 처리할 PDF 문서가 없습니다."),
#     "default": (500, "문서 처리 중 예기치 않은 오류가 발생했습니다."),
# }

# # 라우터 prefix
# prefix = "/fupsheet"


# # --- API 엔드포인트 정의 ---
# @router.post(
#     path=f"{prefix}/web/fupsheet",
#     summary="Follow-Up Sheet 작성 자동화",
#     response_model=Any,  # 성공 시 AI가 생성한 JSON 객체 반환
# )
# async def process_fupsheet_document_ai_endpoint(
#     file: UploadFile = File(..., description="PDF 문서가 포함된 ZIP 파일"),
#     response: Response = None,
#     # --- 추가 메타 (선택입력) ---
#     session_id: str = Form(default=None),
#     user_id: str = Form(default=None),
#     user_name: str = Form(default=None),
#     company: str = Form(default=None),
#     department: str = Form(default=None),
#     user_email: str = Form(default=None),
# ):
#     """
#     [엔드포인트 설명]
#     - ZIP 파일을 업로드 받아 내부 PDF 문서를 AI로 분석
#     - 결과를 JSON 객체로 반환
#     - 응답 헤더에 처리시간(ms) 포함
#     """
#     # --- 입력 파일 검증 ---
#     if not file.filename.lower().endswith(".zip"):
#         raise HTTPException(
#             status_code=400,
#             detail="잘못된 파일 타입입니다. .zip 파일을 업로드해주세요.",
#         )

#     try:
#         # --- 서비스 호출 및 처리 시간 측정 ---
#         start = time.perf_counter()
#         analysis_result = await fupsheet_service.process_fupsheet_documents(
#             file,
#             session_id=session_id,
#             user_id=user_id,
#             user_name=user_name,
#             company=company,
#             department=department,
#             user_email=user_email,
#             processing_time_ms=None,  # 아래에서 계산 후 별도 로깅도 가능하지만, 여기서 넘겨도 무방
#         )
#         duration_ms = int((time.perf_counter() - start) * 1000)

#         if response is not None:
#             response.headers["X-Processing-Time-MS"] = str(duration_ms)

#         if analysis_result is None:
#             raise HTTPException(
#                 status_code=500,
#                 detail="AI 모델이 FUPSHEET 문서에 대한 결과를 반환하지 않았습니다.",
#             )
#         return analysis_result

#     # --- 예외 처리 ---
#     except ValueError as ve:
#         error_key = str(ve)
#         status_code, detail_message = ERROR_MESSAGES.get(
#             error_key, ERROR_MESSAGES["default"]
#         )
#         raise HTTPException(status_code=status_code, detail=detail_message)

#     except IOError as e:
#         raise HTTPException(
#             status_code=500, detail=f"파일 처리 중 오류가 발생했습니다: {e}"
#         )

#     except Exception as e:
#         print(f"FUPSHEET: 예상치 못한 오류 발생: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail="문서 처리 중 서버에서 예기치 못한 오류가 발생했습니다.",
#         )
