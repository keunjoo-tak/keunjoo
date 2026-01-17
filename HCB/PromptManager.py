# import os
# import json
# import logging
# from typing import Optional, List

# # 로거 설정
# logger = logging.getLogger(__name__)


# class PromptManager:
#     """
#     프롬프트(JSON 기반)를 관리하는 클래스.
#     - JSON 파일 로드/저장
#     - 프롬프트 엔트리 CRUD 제공
#     - 특정 subject 기반 조회 기능 제공
#     """

#     def __init__(self, filename: str):
#         """
#         생성자: 지정된 JSON 파일을 로드하여 데이터 초기화
#         - 파일이 없거나 JSON 파싱 오류 시 빈 리스트로 초기화

#         :param filename: JSON 프롬프트 파일 경로
#         """
#         self.filename = filename
#         self.data = self.load_json()
#         logger.info(
#             f"PromptManager initialized with file: '{self.filename}'. "
#             f"Loaded {len(self.data)} entries."
#         )

#     # -------------------------------------------------------------------
#     # 내부 유틸: JSON 로드/저장
#     # -------------------------------------------------------------------
#     def load_json(self) -> List[dict]:
#         """JSON 파일을 읽어 파이썬 리스트 반환"""
#         try:
#             with open(self.filename, "r", encoding="utf8") as f:
#                 data = json.load(f)
#             if not isinstance(data, list):
#                 logger.warning(
#                     f"Prompt file '{self.filename}' content is not a list. "
#                     "Initializing with empty list."
#                 )
#                 return []
#             return data
#         except FileNotFoundError:
#             logger.warning(
#                 f"Prompt file '{self.filename}' not found. Initializing with empty list."
#             )
#             return []
#         except json.JSONDecodeError as e:
#             logger.error(
#                 f"Error decoding JSON from '{self.filename}': {e}. "
#                 "Initializing with empty list."
#             )
#             return []
#         except Exception as e:
#             logger.error(
#                 f"Unexpected error loading JSON from '{self.filename}': {e}. "
#                 "Initializing with empty list."
#             )
#             return []

#     def save_json(self):
#         """현재 데이터를 JSON 파일에 저장"""
#         try:
#             with open(self.filename, "w", encoding="utf8") as f:
#                 json.dump(self.data, f, ensure_ascii=False, indent=4)
#             logger.info(f"Prompt data saved to '{self.filename}'.")
#         except Exception as e:
#             logger.error(f"Error saving JSON to '{self.filename}': {e}")

#     # -------------------------------------------------------------------
#     # CRUD 기능
#     # -------------------------------------------------------------------
#     def update_entry(self, subject: str, new_values: dict) -> bool:
#         """
#         subject에 해당하는 프롬프트 엔트리를 업데이트
#         - version 업데이트 시 동일 version 값은 허용하지 않음

#         :param subject: 업데이트 대상 subject 값
#         :param new_values: 업데이트할 내용 (dict)
#         :return: 업데이트 성공 여부
#         :raises ValueError: 동일 version 업데이트 시 예외 발생
#         """
#         for entry in self.data:
#             if entry.get("subject") == subject:
#                 if "version" in new_values and new_values["version"] == entry.get(
#                     "version"
#                 ):
#                     raise ValueError(
#                         f"업데이트하려는 version 값({new_values['version']})이 "
#                         f"기존 엔트리({entry.get('version')})와 동일합니다."
#                     )

#                 entry.update(new_values)
#                 self.save_json()
#                 logger.info(f"Entry with subject '{subject}' updated.")
#                 return True

#         logger.warning(f"Entry with subject '{subject}' not found for update.")
#         return False

#     def delete_entry(self, subject: str) -> bool:
#         """
#         subject에 해당하는 프롬프트 엔트리를 삭제

#         :param subject: 삭제할 subject 값
#         :return: 삭제 성공 여부
#         """
#         initial_len = len(self.data)
#         self.data = [entry for entry in self.data if entry.get("subject") != subject]
#         if len(self.data) < initial_len:
#             self.save_json()
#             logger.info(f"Entry with subject '{subject}' deleted.")
#             return True

#         logger.warning(f"Entry with subject '{subject}' not found for deletion.")
#         return False

#     def create_entry(
#         self,
#         subject: str,
#         text: str,
#         type: str,
#         author: Optional[str] = None,
#         version: Optional[int] = None,
#     ):
#         """
#         새로운 프롬프트 엔트리를 생성하여 저장
#         - subject는 50자 이내여야 하며, 중복 불가

#         :param subject: 프롬프트 제목 (50자 제한)
#         :param text: 프롬프트 내용
#         :param type: 프롬프트 종류
#         :param author: 작성자 (선택)
#         :param version: 버전 정보 (선택)
#         :raises ValueError: subject 길이 초과 or 중복 시
#         """
#         if len(subject) > 50:
#             raise ValueError("subject는 50자 이내로 입력되어야 합니다.")

#         for entry in self.data:
#             if entry.get("subject") == subject:
#                 raise ValueError(
#                     f"동일한 subject '{subject}'를 가진 엔트리가 이미 존재합니다."
#                 )

#         prompt_entry = {
#             "subject": subject,
#             "text": text,
#             "type": type,
#             "author": author,
#             "version": version,
#         }
#         self.data.append(prompt_entry)
#         self.save_json()
#         logger.info(f"New prompt entry '{subject}' created.")

#     # -------------------------------------------------------------------
#     # 조회 기능
#     # -------------------------------------------------------------------
#     def listup_subjects(self):
#         """전체 subject 목록을 로깅 출력"""
#         for entry in self.data:
#             subject = entry.get("subject")
#             logger.info(f"subject: {subject}")

#     def get_text(self, subject: str) -> Optional[str]:
#         """
#         subject에 해당하는 프롬프트의 text 반환

#         :param subject: 조회할 subject 값
#         :return: text 문자열 (없으면 None)
#         """
#         for entry in self.data:
#             if entry.get("subject") == subject:
#                 text = entry.get("text")
#                 logger.debug(
#                     f"Retrieved text for subject '{subject}'. "
#                     f"Length: {len(text) if text else 0}"
#                 )
#                 return text

#         logger.warning(f"Entry for subject '{subject}' not found.")
#         return None
