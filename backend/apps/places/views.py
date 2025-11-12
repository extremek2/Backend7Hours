from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import ValidationError
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
    - category1, category2, category3: 카테고리 필터
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

        # lat/lng 가져오기, 없으면 기본값 사용
        try:
            lat = float(params.get('lat', self.DEFAULT_LAT))
            lng = float(params.get('lng', self.DEFAULT_LNG))
            user_location = Point(lng, lat, srid=4326)

            # radius 기본값 적용
            radius_km = float(params.get('radius', self.DEFAULT_RADIUS_KM))
            radius_m = radius_km * 1000  # km → m
        except ValueError:
            raise ValidationError("lat, lng, radius는 숫자여야 합니다.")

        queryset = Place.objects.filter(is_active=True)

        # 카테고리 필터 (선택)
        category1 = params.get('category1')
        category2 = params.get('category2')
        category3 = params.get('category3')

        if category1:
            queryset = queryset.filter(category1__name=category1)
        if category2:
            queryset = queryset.filter(category2__name=category2)
        if category3:
            queryset = queryset.filter(category3__name=category3)

        # DRF SearchFilter를 통한 검색 필터 자동 적용
        # search_fields에 명시된 필드(title, address, tel, source) 적용

        # 반경 필터 + 거리 계산
        queryset = queryset.annotate(
            distance=Distance('coordinates', user_location)
        ).filter(distance__lte=radius_m).order_by('distance')

        return queryset
