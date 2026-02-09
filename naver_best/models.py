import time
from dataclasses import dataclass, field
from typing import List, Dict, Any


# ==========================================================
# 옵션 DOM 참조 객체 (자동화 핵심 단위)
# ==========================================================
@dataclass
class OptionNodeRef:
    value: str
    selector: str
    fingerprint: Dict[str, Any]
    depth_index: int

    interaction_type: str = "click"   # "click" or "select"
    option_value: str = None          # select일 때 실제 value
    meta: Dict[str, Any] = field(default_factory=dict)



# ==========================================================
# 개별 옵션 조합 단위 (Variant)
# ==========================================================
@dataclass
class NaverVariant:
    """
    네이버 상품의 하나의 옵션 조합 (예: 블랙 + XL)
    """
    # 사람이 읽는 옵션 의미 (GUI/표시/LLM용)
    option_map: Dict[str, str]                 # {"색상": "블랙", "사이즈": "XL"}

    # 🔥 자동화용 인터랙션 정보
    option_nodes: Dict[str, OptionNodeRef] = field(default_factory=dict)
    # {"색상": OptionNodeRef(...), "사이즈": OptionNodeRef(...)}

    # 상태 변화 수집 결과
    price: float = 0
    stock: str = "in_stock"

    # 디버깅/원본 저장
    raw_data: Dict[str, Any] = field(default_factory=dict)


# ==========================================================
# 상품 단위 모델
# ==========================================================
@dataclass
class NaverProductItem:
    """
    네이버 베스트 상품 수집 전체 정보 모델
    """
    # 기본 정보
    name: str = ""
    best_rank: int = 0
    best_detail_url: str = ""
    original_url: str = ""

    # 미디어 / 설명
    images: List[str] = field(default_factory=list)
    description: str = ""

    # ----------------------------
    # 옵션 구조 (의미 레이어)
    # ----------------------------
    option_groups: List[str] = field(default_factory=list)     # ["색상", "사이즈"]
    options: List[str] = field(default_factory=list)           # 원본 텍스트 옵션들
    variants: List[NaverVariant] = field(default_factory=list) # 조합 단위 결과

    # ----------------------------
    # 자동화 준비 레이어 (그룹 단위 노드 보관)
    # ----------------------------
    option_node_groups: Dict[str, List[OptionNodeRef]] = field(default_factory=dict)
    # 예:
    # {
    #   "색상": [OptionNodeRef(...), OptionNodeRef(...)],
    #   "사이즈": [OptionNodeRef(...)]
    # }

    # 메타 관리
    store_url: str = ""
    collected_at: float = field(default_factory=time.time)

    # GUI 상태
    is_collected: bool = False

    # 확장 데이터
    extra_info: Dict[str, Any] = field(default_factory=dict)
