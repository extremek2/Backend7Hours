from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import ValidationError
from django.db.models import Q
from .models import Place
from .serializers import PlaceSerializer

# API 테스트용 권한 임시 허용
from rest_framework.permissions import AllowAny, IsAuthenticated

"""
활성화된 장소 조회 API
---------------------
선택:
    - lat: 사용자 위도 (기본 용산역)
    - lng: 사용자 경도 (기본 용산역)
    - radius: 반경 (기본 5km)
    - search: title, address, tel, source 검색
"""

class PlaceListAPIView(ListAPIView):
    permission_classes = [AllowAny]  # 누구나 접근 가능 -> 나중에 꼭 'IsAuthenticated' 로 변경 요망
    
    serializer_class = PlaceSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'address', 'tel', 'source']

    DEFAULT_RADIUS_KM = 5  # 기본 반경 5km
    DEFAULT_LAT = 37.5295  # 용산역 위도
    DEFAULT_LNG = 126.9648  # 용산역 경도
    

    def get_queryset(self):
        params = self.request.query_params
        queryset = Place.objects.filter(is_active=True)

        # 1. 위치 및 반경 필터링 및 거리 계산 (필수 로직)
        try:
            lat = float(params.get('lat', self.DEFAULT_LAT))
            lng = float(params.get('lng', self.DEFAULT_LNG))
            user_location = Point(lng, lat, srid=4326)

            radius_km = float(params.get('radius', self.DEFAULT_RADIUS_KM))
            radius_m = radius_km * 1000  # km → m
        except ValueError:
            raise ValidationError({"detail": "lat, lng, radius는 숫자여야 합니다."})

        # 반경 필터 + 거리 계산 (DB 쿼리 2번을 1번으로 최적화)
        queryset = queryset.annotate(
            distance=Distance('coordinates', user_location)
        ).filter(distance__lte=radius_m).order_by('distance')
        
        
        # 2. 카테고리 필터 (통합 Category 모델 활용)
        category_name = params.get('category_name')

        if category_name:
            # 단일 category_name이 Category 1, 2, 3 중 하나와 일치하는 장소를 찾습니다.
            # Category 2와 Category 3의 상위 카테고리(parent, parent__parent)의 이름도 함께 검사합니다.
            
            # Place.category 필드는 가장 세부적인 카테고리(Category 2 또는 3)를 연결합니다.
            # 이 연결된 카테고리의 이름(category__name)이 일치하는 경우를 찾습니다.
            # 또한, 연결된 카테고리의 부모 이름(category__parent__name)이 일치하는 경우도 찾습니다.
            
            queryset = queryset.filter(
                Q(category__name__iexact=category_name) |  # 세부 카테고리 이름이 일치
                Q(category__parent__name__iexact=category_name) # 상위 카테고리 이름이 일치
            ).distinct() # 중복 레코드 방지
        # 3. DRF SearchFilter 자동 적용 (title, address, tel, source)

        return queryset