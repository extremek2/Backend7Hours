import requests
from urllib.parse import quote, unquote
from django.db import transaction
from django.contrib.gis.geos import Point
from core.models import Category
from .models import Place

# API 키 및 URL
KCISA_KEY = "a7d54bca-e026-4bf0-a490-2cbbf0433709"
KCISA_URL = "https://api.kcisa.kr/openapi/API_TOU_050/request"

TOUR_KEY = unquote("Um%2Bqj6eBcNF3%2FgXOHnehh%2BpF5QvECe9Q4DGbptVAij9wB3Flsx5KDTC5hPaf5kq636FuXDi0eG1jy8KjF8BfJQ%3D%3D")
TOUR_URL = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaBasedList"

# ===============================
# 공통 변환 로직
# ===============================

def convert_kcisa_coords(coord_str: str) -> Point | None:
    """KCISA 좌표 문자열을 PostGIS Point 객체로 변환"""
    if not coord_str: return None
    try:
        # 공백 및 방향 문자 제거 후 float 변환 (KCISA: 위도, 경도)
        coord_str = coord_str.replace("N", "").replace("E", "").replace("S", "-").replace("W", "-").strip()
        parts = [p.strip() for p in coord_str.split(",")]
        if len(parts) == 2:
            lat, lng = map(float, parts)
            # PostGIS는 Point(경도, 위도) 순서
            return Point(lng, lat, srid=4326) 
    except Exception as e:
        print(f"KCISA 좌표 변환 실패: {coord_str} ({e})")
        return None

def convert_ktour_coords(mapx: float | None, mapy: float | None) -> Point | None:
    """KTOUR mapx/mapy (경도/위도)를 Point 객체로 변환"""
    if mapx is None or mapy is None: return None
    try:
        lng, lat = float(mapx), float(mapy)
        return Point(lng, lat, srid=4326)
    except Exception as e:
        print(f"KTOUR 좌표 변환 실패: {mapx}, {mapy} ({e})")
        return None

def get_or_create_category(cat1_name: str | None, cat2_name: str | None, cat3_name: str | None = None) -> Category | None:
    """단일 Category 모델에 3계층 카테고리를 저장/가져오고 가장 세부 카테고리 객체 반환"""
    cat_obj = None
    parent_obj = None

    # Category 1 처리
    if cat1_name:
        parent_obj, _ = Category.objects.get_or_create(name=cat1_name, defaults={'parent': None})
    
    # Category 2 처리
    if cat2_name and parent_obj:
        cat_obj, _ = Category.objects.get_or_create(name=cat2_name, defaults={'parent': parent_obj})
        parent_obj = cat_obj # 다음 계층의 부모로 설정
    
    # Category 3 처리
    if cat3_name and parent_obj:
        cat_obj, _ = Category.objects.get_or_create(name=cat3_name, defaults={'parent': parent_obj})
    
    # 최종적으로 가장 세부적인 카테고리 객체 반환 (3 > 2 > 1 순)
    return cat_obj or parent_obj



# ===============================
# KCISA API 호출 (유지)
# ===============================
def fetch_kcisa_places(keyword=None, numOfRows=1000, pageNo=1):
    # ... (기존 API 호출 로직 유지) ...
    params = f"?serviceKey={KCISA_KEY}&numOfRows={numOfRows}&pageNo={pageNo}"
    if keyword:
        params += f"&keyword={quote(keyword)}"
    response = requests.get(KCISA_URL + params, headers={"accept": "application/json"})
    response.raise_for_status()
    items = response.json()['response']['body'].get('items', {}).get('item', [])
    return items if isinstance(items, list) else [items]


# ===============================
# KCISA → Place 통합 저장
# ===============================
@transaction.atomic
def save_kcisa_to_place(rows):
    for item in rows:
        # 변환 로직
        coords = convert_kcisa_coords(item.get('coordinates'))
        category_obj = get_or_create_category(
            item.get('category1'), 
            item.get('category2'), 
            item.get('category3')
        )
        
        # 통합 Place 저장
        Place.objects.update_or_create(
            # 고유 식별자로 업데이트/생성 (KCISA는 title/address 조합 또는 고유 ID 사용 필요)
            # 여기서는 API 출처와 제목을 조합하여 임시 고유 키로 사용 (실제 고유 ID가 필요함)
            kcisa_id=item.get('title'), # title이 고유 ID 역할을 한다고 가정
            defaults={
                'title': item.get('title'),
                'tel': item.get('tel'),
                'address': item.get('address'),
                'coordinates': coords,
                'category': category_obj,
                'source': 'KCISA',
                'raw_data': item, # 원본 JSON 전체 저장
                'is_active': True
            }
        )


# ===============================
# 한국관광공사 API 호출 (유지)
# ===============================
def fetch_ktour_places(areaCode=None, sigunguCode=None, numOfRows=1000, pageNo=1):
    # ... (기존 API 호출 로직 유지) ...
    params = {
        "ServiceKey": TOUR_KEY,
        "numOfRows": numOfRows,
        "pageNo": pageNo,
        "MobileOS": "ETC",
        "MobileApp": "MyApp",
    }
    # ... (areaCode, sigunguCode 조건 추가) ...
    if areaCode: params["areaCode"] = areaCode
    if sigunguCode: params["sigunguCode"] = sigunguCode

    response = requests.get(TOUR_URL, params=params)
    response.raise_for_status()
    items = response.json()['response']['body'].get('items', {}).get('item', [])
    return items if isinstance(items, list) else [items]


# ===============================
# KTOUR → Place 통합 저장
# ===============================
@transaction.atomic
def save_ktour_to_place(rows):
    for item in rows:
        # 변환 로직
        coords = convert_ktour_coords(item.get('mapx'), item.get('mapy'))
        category_obj = get_or_create_category(
            item.get('cat1'), 
            item.get('cat2'), 
            item.get('cat3')
        )

        # 통합 Place 저장
        Place.objects.update_or_create(
            # KTOUR는 contentid가 고유 ID이므로 이를 사용
            ktour_content_id=item.get('contentid'), 
            defaults={
                'title': item.get('title'),
                'tel': item.get('tel'),
                # KTOUR는 addr1만 통합 address로 사용
                'address': item.get('addr1'), 
                'coordinates': coords,
                'category': category_obj,
                'source': 'KTOUR',
                'raw_data': item, # 원본 JSON 전체 저장
                'is_active': True
            }
        )
