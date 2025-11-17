# posts/views.py
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.gis.geos import Point
# from django.contrib.gis.measure import D 

from .models import Location

from django.contrib.gis.geos import LineString
from .models import Route

def find_nearby_locations(request):
    
    
    # 1. 기준점 (강남역)
    my_location = Point(127.0276, 37.4979, srid=4326)
    
   
    distance_degrees = 0.009  # 약 1km
    

    nearby_locations = Location.objects.filter(
        geom__dwithin=(my_location, distance_degrees)
    )
    
    # 2. 찾은 장소들의 이름을 리스트로 만듭니다.
    response_text = "<h1>강남역 1km 이내 장소 (PointField 사용):</h1><ul>"
    
    if not nearby_locations.exists():
        response_text += "<li>주변에 아무것도 없습니다.</li>"
    
    for location in nearby_locations:
        response_text += f"<li>{location.name}</li>"
        
    response_text += "</ul>"
    
    return HttpResponse(response_text)


def show_line_map(request):
    """
    DB에 저장된 모든 Location(점)들을 잇는 선(LineString)을 만들어
    지도 페이지(HTML)에 전달합니다.
    """
    
    # 1. DB에서 모든 Location 객체를 가져옵니다.
    locations = Location.objects.order_by('id') # id 순서대로 정렬
    
    # 2. 각 Location의 좌표(x, y)만 추출하여 리스트로 만듭니다.
    #    (loc.geom.coords는 (경도, 위도) 튜플입니다)
    coords = [loc.geom.coords for loc in locations]
    
    line_geojson = None

    # 3. 선을 만들려면 점이 2개 이상 필요합니다.
    if len(coords) > 1:
        # 4. 좌표 리스트로 'LineString' 객체를 메모리에서 생성합니다.
        line = LineString(coords, srid=4326)
        
        # 5. (가장 중요) LineString 객체를 'GeoJSON' 텍스트 형식으로 변환합니다.
        #    이 텍스트를 JavaScript(Leaflet)가 읽게 됩니다.
        line_geojson = line.geojson
    
    # 6. 'line_geojson' 데이터를 'posts/map.html' 템플릿으로 전달합니다.
    context = {
        'line_geojson': line_geojson
    }
    return render(request, 'posts/map.html', context)

def create_route_from_coords(request):
    # 1. 주어진 위도, 경도 좌표 리스트 (경도, 위도)
    coords = [
        (127.0276, 37.4979),  # 강남역
        (127.0480, 37.5042),  # 선릉역
        (127.0628, 37.5172),  # 삼성역
    ]

    try:
        # 2. 좌표 리스트로 LineString 객체 생성 (srid=4326)
        line = LineString(coords, srid=4326)

        # 3. '강남 테헤란로'라는 이름으로 Route 객체 생성 및 저장
        route_obj, created = Route.objects.update_or_create(
            name="강남 테헤란로",
            defaults={'path': line}
        )
        
        if created:
            return HttpResponse("<h1>'강남 테헤란로' 경로를 생성했습니다!</h1>")
        else:
            return HttpResponse("<h1>'강남 테헤란로' 경로를 새 좌표로 업데이트했습니다!</h1>")
    
    except Exception as e:
        return HttpResponse(f"<h1>오류 발생:</h1><p>{e}</p>")