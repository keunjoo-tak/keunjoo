# from pydantic import BaseModel, Field
# from typing import Optional, List

# # --- Chat Schemas ---
# class FilePart(BaseModel):
#     mime_type: str
#     data_base64: str

# class ChatRequest(BaseModel):
#     sessionId: str = Field(..., description="고유한 세션 식별자")
#     message: str
#     userId: Optional[str] = Field(None, description="사용자 식별자(선택 사항)")
#     model: str = Field(..., description="사용할 LLM 모델 ('GEMINI' 또는 'QWEN3')")
#     file_parts: Optional[List[FilePart]] = Field(None, description="첨부된 파일 정보")

# class ResetChatRequest(BaseModel):
#     sessionId: str

# # --- Outline (FTP) Schemas ---
# # 기존 FtpRequest 모델
# class FtpRequest(BaseModel):
#     proj_no: Optional[str] = None
#     file_dir: Optional[str] = None
#     file_names: Optional[List[str]] = None
