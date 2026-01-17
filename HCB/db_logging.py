# # HDE_HCB/services/fupsheet_logging.py
# import os
# import json
# from dataclasses import is_dataclass, asdict
# from datetime import datetime, timedelta, timezone

# from typing import Optional, Dict, Any, List, Sequence
# from contextlib import contextmanager
# from sqlalchemy.orm import Session
# from sqlalchemy import (
#     BigInteger,
#     Column,
#     DateTime,
#     Integer,
#     String,
#     Text,
#     JSON,
#     create_engine,
#     text,
# )
# from sqlalchemy.orm import declarative_base, sessionmaker


# from constant import Service
# from constant import get_company_name, get_department_code, get_service_code

# # ------------------------------------------------------------------------
# # 환경변수 로딩 및 DB 연결
# # ------------------------------------------------------------------------

# # 동기 엔진(간단/안전하게 추가하기 위해 동기 사용; 호출부에서 thread offload 없이 처리 가능한 범위의 가벼운 INSERT만 수행)
# DATABASE_URL = os.getenv("LOG_DB_URL")
# if not DATABASE_URL:
#     raise RuntimeError("LOG_DB_URL is not set")


# Base = declarative_base()
# _engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
# _SessionLocal = sessionmaker(
#     bind=_engine, autoflush=False, autocommit=False, future=True
# )

# KST = timezone(timedelta(hours=9))


# # ------------------------------------------------------------------------
# # 테이블 모델 정의: ai_service_history
# # ------------------------------------------------------------------------
# class AiServiceHistory(Base):
#     """
#     AI 서비스 실행 이력 테이블 (ai_service_history)
#     """

#     __tablename__ = "ai_service_history"

#     # 기본키 및 생성일자
#     idx = Column(BigInteger, primary_key=True, autoincrement=True, comment="PK")
#     created_at = Column(
#         DateTime, nullable=False, default=datetime.now(KST), comment="생성일시"
#     )
#     updated_at = Column(
#         DateTime,
#         nullable=False,
#         default=datetime.now(KST),
#         onupdate=datetime.now(KST),
#         comment="수정일시",
#     )

#     # 요청 메타
#     session_id = Column(String(50), nullable=True, comment="세션 ID")
#     company_cd = Column(String(50), nullable=True, comment="회사 코드")
#     company_nm = Column(String(50), nullable=True, comment="회사명")
#     dept_cd = Column(String(50), nullable=True, comment="부서 코드")
#     dept_nm = Column(String(50), nullable=True, comment="부서명")
#     service_cd = Column(String(50), nullable=True, comment="서비스 코드")
#     service_nm = Column(String(50), nullable=True, comment="서비스명")
#     user_id = Column(String(50), nullable=True, comment="사용자 ID")
#     user_nm = Column(String(50), nullable=True, comment="사용자명")
#     user_email = Column(String(200), nullable=True, comment="사용자 이메일")

#     # 파일/처리 정보
#     input_filepath = Column(String(512), nullable=True, comment="입력 파일 경로")
#     output_filepath = Column(String(512), nullable=True, comment="출력 파일 경로")
#     fup_switchgear_type = Column(JSON, nullable=True, comment="전력기기 종류")
#     response_json = Column(JSON, nullable=True, comment="전체 응답(JSON)")
#     start_dt = Column(DateTime, nullable=True, comment="처리 시작 시간")
#     end_dt = Column(DateTime, nullable=True, comment="처리 종료 시간")
#     status = Column(String(50), nullable=True, comment="처리 상태 (SUCCESS/ERROR)")
#     err_msg = Column(Text, nullable=True, comment="에러 메시지")


# # ------------------------------------------------------------------------
# # 테이블(없으면 자동생성)
# # ------------------------------------------------------------------------
# def init_tables():
#     # 테이블이 없으면 생성 (운영 DB에서는 별도 DDL 권장)
#     Base.metadata.create_all(_engine)


# init_tables()


# # ------------------------------------------------------------------------
# # JSON safe 변환 유틸
# # -----------------------------------------------------------------------
# def _to_jsonable(obj: Any) -> Any:
#     """
#     SQLAlchemy JSON 컬럼에 넣을 수 있도록 JSON-serializable 형태로 변환.
#     - dataclass -> asdict
#     - dict/list/str/int/float/bool/None -> 그대로
#     - 기타 객체 -> 가능한 경우 __dict__ -> dict
#     - 최후 fallback -> str(obj)
#     """
#     if obj is None:
#         return None
#     if isinstance(obj, (dict, list, str, int, float, bool)):
#         return obj
#     if is_dataclass(obj):
#         try:
#             return asdict(obj)
#         except Exception:
#             return {"_dataclass_str": str(obj)}
#     if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
#         # pydantic v1 스타일 대응
#         try:
#             return obj.dict()
#         except Exception:
#             pass
#     if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
#         # pydantic v2 스타일 대응
#         try:
#             return obj.model_dump()
#         except Exception:
#             pass
#     if hasattr(obj, "__dict__"):
#         try:
#             return dict(obj.__dict__)
#         except Exception:
#             pass
#     return str(obj)


# # ------------------------------------------------------------------------
# # SwitchGearType 요약 추출 함수
# #   - result(JSON배열) → SwitchGearType 값 추출(중복/none 제거, 정렬)
# # -----------------------------------------------------------------------
# def _unique_switchgears_from_result(result: Any) -> Optional[list]:
#     try:
#         if isinstance(result, list):
#             s = {
#                 str(e.get("SwitchGearType"))
#                 for e in result
#                 if isinstance(e, dict) and "SwitchGearType" in e
#             }
#             return sorted([x for x in s if x and x.lower() != "none"])
#         return None
#     except Exception:
#         return None


# # ------------------------------------------------------------------------
# # 실행 이력 기록 함수
# #   - 입력: 실행 메타/결과/에러 등
# #   - 결과: 생성된 row PK(id)
# # ------------------------------------------------------------------------
# def insert_ai_service_history(
#     *,
#     # 공통 식별/조직
#     session_id: Optional[str] = None,
#     company_cd: Optional[str] = None,
#     company_nm: Optional[str] = None,
#     dept_cd: Optional[str] = None,
#     dept_nm: Optional[str] = None,
#     service_cd: Optional[str] = None,
#     service_nm: Optional[str] = None,
#     user_id: Optional[str] = None,
#     user_nm: Optional[str] = None,
#     user_email: Optional[str] = None,
#     # 파일/경로
#     input_filepath: Optional[str] = None,
#     output_filepath: Optional[str] = None,
#     # 처리/시간
#     start_dt: Optional[datetime] = None,
#     end_dt: Optional[datetime] = None,
#     # 결과/상태
#     status: Optional[str] = None,  # 'SUCCESS' | 'ERROR' | ...
#     err_msg: Optional[str] = None,
#     response_json: Optional[Any] = None,  # dict/list/str 허용
# ) -> int:
#     """
#     DBeaver 기준 스키마(ai_service_history)에 맞춘 insert 함수.
#     반환값: 생성된 PK(idx)
#     """
#     # 서비스코드가 HCB_FUP_SW이면 switchgear type 자동 도출
#     if service_cd == Service.HCB_FUP_SW.value[0]:
#         fup_switchgear_type = _unique_switchgears_from_result(response_json)
#     else:
#         fup_switchgear_type = None

#     company_nm = get_company_name(company_cd)
#     dept_cd = get_department_code(dept_nm)
#     response_json = _to_jsonable(response_json)

#     with _SessionLocal() as db:
#         rec = AiServiceHistory(
#             session_id=session_id,
#             company_cd=company_cd,
#             company_nm=company_nm,
#             dept_cd=dept_cd,
#             dept_nm=dept_nm,
#             service_cd=service_cd,
#             service_nm=service_nm,
#             user_id=user_id,
#             user_nm=user_nm,
#             user_email=user_email,
#             input_filepath=input_filepath,
#             output_filepath=output_filepath,
#             fup_switchgear_type=fup_switchgear_type,
#             start_dt=start_dt,
#             end_dt=end_dt,
#             status=status,
#             err_msg=err_msg,
#             response_json=response_json,
#         )
#         db.add(rec)
#         db.commit()
#         db.refresh(rec)
#         return rec.idx
