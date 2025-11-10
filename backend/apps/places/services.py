import requests
from urllib.parse import quote
from django.forms.models import model_to_dict
from apps.places.models import Category1, Category2, Category3
from django.contrib.gis.geos import Point
from .models import KCISAPlace, KoreaTourPlace, Place

KCISA_KEY = "a7d54bca-e026-4bf0-a490-2cbbf0433709"
KCISA_URL = "https://api.kcisa.kr/openapi/API_TOU_050/request"

TOUR_KEY = "YOUR_KTOUR_KEY"
TOUR_URL = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaBasedList"

# ===============================
# KCISA API 호출
# ===============================
def fetch_kcisa_places(keyword=None, numOfRows=1000, pageNo=1):
    params = f"?serviceKey={KCISA_KEY}&numOfRows={numOfRows}&pageNo={pageNo}"
    if keyword:
        params += f"&keyword={quote(keyword)}"
    response = requests.get(KCISA_URL + params, headers={"accept": "application/json"})
    response.raise_for_status()
    items = response.json()['response']['body'].get('items', {}).get('item', [])
    return items if isinstance(items, list) else [items]

# ===============================
# KCISA → Place 저장
# ===============================
def save_kcisa_to_place(rows):
    for item in rows:
                    
        # KCISA 원본 저장    
        kcisa_obj, _ = KCISAPlace.objects.update_or_create(
            title=item.get('title'),
            defaults={
                'issued_date': item.get('issuedDate'),
                'description': item.get('description'),
                'tel': item.get('tel'),
                'url': item.get('url'),
                'address': item.get('address'),
                'charge': item.get('charge'),
                'category1': item.get('category1'),
                'category2': item.get('category2'),
                'category3': item.get('category3'),
            }
        )

        # 좌표(PointField) 설정
        coords = kcisa_obj.set_coordinates(item.get('coordinates'))
        if coords:
            kcisa_obj.coordinates = coords
            kcisa_obj.save()
        
        # category1,2,3가 존재하면 ForeignKey 객체 가져오거나 생성
        cat1_obj = Category1.objects.get_or_create(name=kcisa_obj.category1)[0] if kcisa_obj.category1 else None
        cat2_obj = Category2.objects.get_or_create(name=kcisa_obj.category2, parent=cat1_obj)[0] if kcisa_obj.category2 else None
        cat3_obj = Category3.objects.get_or_create(name=kcisa_obj.category3, parent=cat2_obj)[0] if kcisa_obj.category3 else None
        
        # Place 통합 저장
        raw_data = model_to_dict(kcisa_obj)
        if kcisa_obj.coordinates:
            raw_data['coordinates'] = {'lng': kcisa_obj.coordinates.x, 'lat': kcisa_obj.coordinates.y}

        Place.objects.update_or_create(
            title=kcisa_obj.title,
            defaults={
                'title': kcisa_obj.title,
                'tel': kcisa_obj.tel,
                'address': kcisa_obj.address,
                'category1': cat1_obj,
                'category2': cat2_obj,
                'category3': cat3_obj,
                'coordinates': kcisa_obj.coordinates,
                'source': 'KCISA',
                'raw_data': raw_data,
                'is_active': True
            }
        )



# ===============================
# 한국관광공사 API 호출
# ===============================
def fetch_ktour_places(areaCode=None, sigunguCode=None, numOfRows=1000, pageNo=1):
    params = {
        "ServiceKey": TOUR_KEY,
        "numOfRows": numOfRows,
        "pageNo": pageNo,
        "MobileOS": "ETC",
        "MobileApp": "MyApp",
    }
    if areaCode:
        params["areaCode"] = areaCode
    if sigunguCode:
        params["sigunguCode"] = sigunguCode

    response = requests.get(TOUR_URL, params=params)
    response.raise_for_status()
    items = response.json()['response']['body'].get('items', {}).get('item', [])
    return items if isinstance(items, list) else [items]

# ===============================
# KTOUR → Place 저장
# ===============================
def save_ktour_to_place(rows):
    for item in rows:
        tour_obj, _ = KoreaTourPlace.objects.update_or_create(
            title=item.get('title'),
            defaults={
                'addr1': item.get('addr1'),
                'addr2': item.get('addr2'),
                'cat1': item.get('cat1'),
                'cat2': item.get('cat2'),
                'cat3': item.get('cat3'),
                'mapx': item.get('mapx'),
                'mapy': item.get('mapy'),
                'contentid': item.get('contentid'),
                'contenttypeid': item.get('contenttypeid'),
                'createdtime': item.get('createdtime'),
                'modifiedtime': item.get('modifiedtime'),
                'tel': item.get('tel'),
            }
        )

        # 좌표(PointField) 설정
        if item.get('mapx') and item.get('mapy'):
            try:
                lng, lat = float(item.get('mapx')), float(item.get('mapy'))
                tour_obj.coordinates = Point(lng, lat, srid=4326)
                tour_obj.save()
            except Exception:
                pass

        # Place 통합 저장
        raw_data = model_to_dict(tour_obj)
        if tour_obj.coordinates:
            raw_data['coordinates'] = {'lng': tour_obj.coordinates.x, 'lat': tour_obj.coordinates.y}

        Place.objects.update_or_create(
            title=tour_obj.title,
            defaults={
                'coordinates': tour_obj.coordinates,
                'source': 'KTOUR',
                'raw_data': raw_data,
                'is_active': True
            }
        )
