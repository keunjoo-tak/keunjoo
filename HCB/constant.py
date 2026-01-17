# # -*- coding: utf-8 -*-
# """
# 코드 마스터 상수 (자동 생성 버전)
# - Company / Department / Service Enum
# - 각 멤버 값: (code, name)
# - get_*_name(code) 헬퍼 제공
# """
# from enum import Enum


# # -----------------------------
# # Company
# # -----------------------------
# class Company(Enum):
#     """회사 코드"""

#     CODE_100 = ("100", "HD한국조선해양㈜")
#     CODE_110 = ("110", "HD아트센터")
#     CODE_200 = ("200", "HD현대일렉트릭㈜")
#     CODE_210 = ("210", "HD현대건설기계㈜")
#     CODE_220 = ("220", "HD현대㈜")
#     CODE_240 = ("240", "현대중공업 파워시스템㈜")
#     CODE_260 = ("260", "HD현대에너지솔루션㈜")
#     CODE_270 = ("270", "HD현대로보틱스㈜")
#     CODE_280 = ("280", "현대엘앤에스㈜")
#     CODE_300 = ("300", "HD현대중공업㈜")
#     CODE_310 = ("310", "HD현대마린솔루션㈜")
#     CODE_320 = ("320", "HD현대사이트솔루션㈜")
#     CODE_330 = ("330", "HD현대마린솔루션테크㈜")
#     CODE_340 = ("340", "HD현대미포")
#     CODE_350 = ("350", "HD현대삼호")
#     CODE_360 = ("360", "아비커스")
#     CODE_370 = ("370", "씨마크서비스")
#     CODE_380 = ("380", "HD현대마린엔진㈜")
#     CODE_390 = ("390", "HD현대크랭크샤프트㈜")
#     CODE_400 = ("400", "HD하이드로젠㈜")
#     CODE_420 = ("420", "HD현대이엔티㈜")
#     CODE_1000 = ("1000", "현대중공업터보기계㈜")
#     CODE_2000 = ("2000", "현대엔진유한회사")
#     HYMS = ("HYMS", "현대힘스(주)")
#     HEGREEN = ("HEGREEN", "현대에너지솔루션㈜")
#     HHISERV = ("HHISERV", "현대글로벌서비스㈜")


# # -----------------------------
# # Department
# # -----------------------------
# class Department(Enum):
#     """부서 코드"""

#     AIC_AI = ("AIC_AI", "AI센터")
#     ACC_AI = ("ACC_AI", "AI가속화실")
#     PM_AI = ("PM_AI", "AI_PM실")
#     DEV_AI = ("DEV_AI", "AI_개발실")
#     AUTO_AI = ("AUTO_AI", "AI자율기술실")
#     AI_STRAT = ("AI_STRAT", "AI전략팀")
#     HVC_DSN = ("HVC_DSN", "고압차단기설계부")
#     TRF_DSN = ("TRF_DSN", "변압기설계부")
#     RMD_DSN = ("RMD_DSN", "회전기설계부")
#     TRF_DEV = ("TRF_DEV", "변압기개발부")
#     RMD_DEV = ("RMD_DEV", "회전기개발부")
#     ICT_LAB = ("ICT_LAB", "ICT솔루션연구실")
#     QMS_OPS = ("QMS_OPS", "품질경영팀")


# # -----------------------------
# # Service
# # -----------------------------
# class Service(Enum):
#     """서비스 코드"""

#     HCB_FUP_SW = ("HCB_FUP_SW", "고압차단기-FUP SHEET")
#     TRF_DOC_EXT = ("TRF_DOC_EXT", "변압기-문서원형추출")
#     TRF_SPEC_INP = ("TRF_SPEC_INP", "변압기-설계입력표")
#     TRF_DOC_REV = ("TRF_DOC_REV", "변압기-문서개정추적")
#     TRF_PRPD_DIAG = ("TRF_PRPD_DIAG", "변압기-PRPD 진단")
#     TRF_DGA_ANA = ("TRF_DGA_ANA", "변압기-DGA 분석")
#     RMD_OUTL_REV = ("RMD_OUTL_REV", "회전기-외형도 검토")
#     RMD_SPEC_SEARCH = ("RMD_SPEC_SEARCH", "회전기-고객사양문서 AUTO SEARCH")
#     RMD_SPEC_ISPEC = ("RMD_SPEC_ISPEC", "회전기-고객사양문서 ISPEC 자동완성")


# # -----------------------------
# # Helpers: code → name
# # -----------------------------
# def get_company_name(code: str) -> str | None:
#     """회사 코드 → 이름"""
#     for c in Company:
#         if c.value[0] == code:
#             return c.value[1]
#     return None


# def get_department_name(code: str) -> str | None:
#     """부서 코드 → 이름"""
#     for d in Department:
#         if d.value[0] == code:
#             return d.value[1]
#     return None


# def get_service_name(code: str) -> str | None:
#     """서비스 코드 → 이름"""
#     for s in Service:
#         if s.value[0] == code:
#             return s.value[1]
#     return None


# # -----------------------------
# # Helpers: name → code
# # -----------------------------
# def get_company_code(name: str) -> str | None:
#     """회사 이름 → 코드"""
#     for c in Company:
#         if c.value[1] == name:
#             return c.value[0]
#     return None


# def get_department_code(name: str) -> str | None:
#     """부서 이름 → 코드"""
#     for d in Department:
#         if d.value[1] == name:
#             return d.value[0]
#     return None


# def get_service_code(name: str) -> str | None:
#     """서비스 이름 → 코드"""
#     for s in Service:
#         if s.value[1] == name:
#             return s.value[0]
#     return None
