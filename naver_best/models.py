import time
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class NaverVariant:
    """네이버 상품의 개별 옵션 변체 정보"""
    option_map: Dict[str, str]  # 예: {"색상": "블랙", "사이즈": "XL"}
    price: float = 0
    stock: str = "in_stock"
    raw_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NaverProductItem:
    """네이버 베스트 상품 수집 정보 모델"""
    name: str = ""
    best_rank: int = 0           # 네이버 베스트 순위 저장용 추가
    best_detail_url: str = ""    # 베스트 상세 페이지 URL
    original_url: str = ""       # 원본 상품 URL
    images: List[str] = field(default_factory=list)
    description: str = ""        # 상세설명 (MHTML 파싱 결과)
    
    # 옵션 관련
    option_groups: List[str] = field(default_factory=list) # ["색상", "사이즈"]
    options: List[str] = field(default_factory=list)       # 원본 옵션 텍스트
    variants: List[NaverVariant] = field(default_factory=list)
    
    # 메타 데이터 및 관리 정보
    store_url: str = ""         # 출처 상점 URL
    collected_at: float = field(default_factory=time.time) # 수집 시각
    
    # [추가] GUI 연동을 위한 수집 완료 상태 필드
    is_collected: bool = False  
    
    # 확장 데이터 (나중에 분석용으로 활용)
    extra_info: Dict[str, Any] = field(default_factory=dict)