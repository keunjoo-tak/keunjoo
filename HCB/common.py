# # FastAPI 라우터/파일 업로드 관련 의존성
# from fastapi import APIRouter, File, UploadFile, Form
# from typing import List, Optional
# from pydantic import BaseModel, EmailStr
# import os
# import shutil
# import zipfile
# import smtplib
# from email.message import EmailMessage
# import logging
# from pathlib import Path

# from dotenv import load_dotenv

# load_dotenv(".env")

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     datefmt="%Y-%m-%d %H:%M:%S",
# )
# logger = logging.getLogger(__name__)

# # 이 모듈에서 사용할 전용 라우터 인스턴스 생성
# router = APIRouter()

# # 업로드 파일을 저장할 루트 디렉터리 경로
# # 실제 운영환경에서는 .env 등으로 외부화하는 것이 바람직
# UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(Path("/tmp") / "uploaded_files"))


# # -------------------------------------------------
# # /zipfile_process 엔드포인트의 요청 바디 스키마 정의
# # -------------------------------------------------
# class ZipProcessRequest(BaseModel):
#     zip_path: str


# # -------------------------------------------------
# # 이메일 전송 클래스
# # -------------------------------------------------
# class SimpleEmailSender:
#     def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
#         """
#         SMTP 서버 연결 정보를 초기화합니다.
#         - smtp_host: SMTP 서버 주소
#         - smtp_port: 포트 번호 (25, 465, 587 등)
#         - username/password: 로그인 자격 정보
#         """
#         self.smtp_host = smtp_host
#         self.smtp_port = smtp_port
#         self.username = username
#         self.password = password

#     def send_mail(
#         self,
#         subject: Optional[str],
#         service: Optional[str],
#         from_addr: Optional[str],
#         to_addrs: List[str],
#         body: Optional[str] = None,
#         is_html: bool = False,
#     ) -> None:
#         """
#         메일 작성 및 전송
#         - subject: 메일 제목
#         - body: 메일 본문 (지정 시 그대로 사용)
#         - from_addr: 발신자 주소
#         - to_addrs: 수신자 목록
#         - is_html: 본문이 HTML일 경우 True
#         """
#         msg = EmailMessage()
#         msg["Subject"] = subject
#         msg["From"] = from_addr
#         msg["To"] = ", ".join(to_addrs)

#         # body를 호출 측에서 넘기면 그대로 사용, 없으면 기본 문구 생성
#         if body is None:
#             body = f"요청하신 생성형 AI 서비스 작업({service})이 완료되었습니다."

#         if is_html:
#             msg.add_alternative(body, subtype="html")
#         else:
#             msg.set_content(body)

#         # SMTP 연결 및 메일 전송
#         with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
#             # 필요 시 TLS/SSL 적용 (회사 정책에 따라)
#             # 예: server.starttls()
#             server.login(self.username, self.password)
#             server.send_message(msg)


# # -------------------------------------------------
# # 이메일 요청 모델 정의
# # -------------------------------------------------
# class EmailRequest(BaseModel):
#     subject: Optional[str]
#     service: Optional[str]
#     from_addr: Optional[EmailStr]
#     to_addrs: List[EmailStr]
#     body: Optional[str] = None
#     is_html: Optional[bool] = False


# # -------------------------------------------------
# # FastAPI 엔드포인트
# # -------------------------------------------------


# @router.post("/upload")
# async def upload_files(files: List[UploadFile] = File(...), user_id: str = Form(...)):
#     result = []
#     user_dir = os.path.join(UPLOAD_DIR, user_id)
#     os.makedirs(user_dir, exist_ok=True)

#     for file in files:
#         file_location = os.path.join(user_dir, file.filename)
#         with open(file_location, "wb") as f:
#             shutil.copyfileobj(file.file, f)
#         file_info = {
#             "filename": file.filename,
#             "filetype": file.content_type,
#             "path": file_location,
#         }
#         result.append(file_info)
#     return result


# @router.post("/zipfile_process")
# async def process_zip_file(req: ZipProcessRequest):
#     if not os.path.exists(req.zip_path) or not req.zip_path.endswith(".zip"):
#         return {"error": "Invalid zip file path"}

#     extract_dir = req.zip_path[:-4]
#     os.makedirs(extract_dir, exist_ok=True)

#     file_list = []
#     with zipfile.ZipFile(req.zip_path, "r") as zip_ref:
#         zip_ref.extractall(extract_dir)
#         file_list = [os.path.join(extract_dir, name) for name in zip_ref.namelist()]

#     return {"extracted_files": file_list}


# @router.post("/send_email")
# async def send_email(req: EmailRequest):
#     """
#     이메일을 전송하는 엔드포인트.
#     SMTP 설정은 환경변수 또는 별도 설정 파일에서 불러오는 것이 바람직합니다.
#     """
#     try:
#         # 실제 SMTP 환경 정보 (운영 환경에서는 환경변수로 관리 권장)
#         smtp_host = os.getenv("SMTP_HOST")
#         smtp_port = int(os.getenv("SMTP_PORT"))
#         smtp_user = os.getenv("SMTP_USER")
#         smtp_pass = os.getenv("SMTP_PASS")

#         # 메일 전송 클래스 인스턴스 생성
#         sender = SimpleEmailSender(
#             smtp_host=smtp_host,
#             smtp_port=smtp_port,
#             username=smtp_user,
#             password=smtp_pass,
#         )

#         # 실제 메일 전송
#         sender.send_mail(
#             subject=req.subject,
#             service=req.service,
#             from_addr=req.from_addr,
#             to_addrs=req.to_addrs,
#             body=req.body,
#             is_html=req.is_html,
#         )

#         return {"status": "success", "message": "메일이 성공적으로 전송되었습니다."}

#     except Exception as e:
#         # 에러 발생 시 상세 원인 반환
#         return {"status": "error", "message": str(e)}
