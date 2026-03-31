import enum


class ReportStyle(enum.Enum):
    ACADEMIC = "academic"
    POPULAR_SCIENCE = "popular_science"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    BUSINESS_MARKETING = "business_marketing"
    BUSINESS_MARKETING_CLIENT = "business_marketing_client"  # 对公营销报告-战客版
    INDUSTRY_REPORT = "industry_report"  # 行业研报
