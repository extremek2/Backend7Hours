from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Path
from .serializers import (
    UserPathCreateSerializer,
    UserPathUpdateSerializer,
    PathSerializer,
)
from .services import PathService
from .permissions import IsOwnerOrReadOnly


class PathListCreateView(generics.ListCreateAPIView):
    """
    GET: 조건에 따라 경로 목록을 조회합니다. (위치 기반 또는 전체)
    POST: 인증된 사용자의 새 경로를 생성합니다.
    """
    serializer_class = PathSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(
        operation_summary="주변 경로 조회",
        operation_description="사용자 위치(lat/lng)와 반경(radius) 기준으로 주변 경로를 조회하거나, 파라미터가 없으면 전체 경로를 조회합니다.",
        manual_parameters=[
            openapi.Parameter('lat', openapi.IN_QUERY, description="사용자 위도", type=openapi.TYPE_NUMBER),
            openapi.Parameter('lng', openapi.IN_QUERY, description="사용자 경도", type=openapi.TYPE_NUMBER),
            openapi.Parameter('radius', openapi.IN_QUERY, description="반경 (m)", type=openapi.TYPE_NUMBER, default=5000),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        lat = self.request.query_params.get("lat")
        lng = self.request.query_params.get("lng")
        radius = float(self.request.query_params.get("radius", 5000))

        queryset = Path.objects.filter(is_private=False)

        if lat is not None and lng is not None:
            try:
                lat, lng = float(lat), float(lng)
                user_location = Point(lng, lat, srid=4326)
                queryset = queryset.filter(geom__isnull=False).annotate(
                    distance_m=Distance("geom", user_location)
                ).filter(distance_m__lte=radius).order_by("distance_m")
            except (ValueError, TypeError):
                # 유효하지 않은 파라미터는 무시하고 전체 쿼리셋 반환
                return Path.objects.filter(is_private=False).order_by('-created_at')
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset

    @swagger_auto_schema(
        operation_summary="사용자 경로 등록",
        operation_description="인증된 사용자가 입력한 좌표를 기반으로 경로를 생성합니다.",
        request_body=UserPathCreateSerializer,
        responses={201: PathSerializer()}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        # UserPathCreateSerializer는 model serializer가 아니므로 직접 호출
        create_serializer = UserPathCreateSerializer(data=self.request.data)
        create_serializer.is_valid(raise_exception=True)
        data = create_serializer.validated_data

        path = PathService.create_from_user_input(
            # auth_user=self.request.user,
            user_id=self.request.user.id,
            path_name=data.get("path_name"),
            path_comment=data.get("path_comment"),
            coords_json=data["coords"],
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            level=data.get("level"),
            distance=data.get("distance"),
            duration=data.get("duration"),
            thumbnail=data.get("thumbnail"),
            is_private=data.get("is_private"),
        )
        
        # 생성된 객체를 응답으로 보내기 위해 serializer.instance에 할당
        serializer.instance = path


class MyPathListView(generics.ListAPIView):
    """
    현재 인증된 사용자가 생성한 경로 목록을 반환합니다.
    """
    serializer_class = PathSerializer
    permission_classes = [IsAuthenticated] # 이 뷰는 반드시 인증이 필요함을 명시

    def get_queryset(self):
        """
        요청을 보낸 사용자(request.user)에게 소유권이 있는 경로만 필터링합니다.
        """
        user = self.request.user
        return Path.objects.filter(auth_user=user)


class PathDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: 특정 경로의 상세 정보를 조회합니다.
    PATCH: 특정 경로의 정보를 수정합니다. (소유자만 가능)
    DELETE: 특정 경로를 삭제합니다. (소유자만 가능)
    """
    queryset = Path.objects.all()
    permission_classes = [IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UserPathUpdateSerializer
        return PathSerializer

    @swagger_auto_schema(operation_summary="개별 경로 조회")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="경로 정보 수정 (소유자만)")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="경로 삭제 (소유자만)")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)