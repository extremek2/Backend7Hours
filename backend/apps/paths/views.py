from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Path
from .serializers import UserPathCreateSerializer, PathSerializer
from .services import PathService
from .tasks import render_path_and_upload

class UserPathCreateView(APIView):
    permission_classes = [permissions.AllowAny]
    
    # 메서드별 권한
    # def get_permissions(self):
    #     if self.request.method == "POST":
    #         # POST는 인증된 사용자만 허용
    #         return [permissions.IsAuthenticated()]
    #     # 나머지(GET 등)는 기본 permission_classes 적용
    #     return super().get_permissions()
    
    """
    GET: DB에 존재하는 모든 경로 반환 (사용자+추천)
    POST: 사용자 입력 좌표로 경로 생성
    """
    # @swagger_auto_schema(
    #     operation_summary="주변 경로 조회",
    #     operation_description="사용자 위치(lat/lng)와 반경(radius) 기준으로 주변 경로를 조회합니다.",
    #     manual_parameters=[
    #         openapi.Parameter('lat', openapi.IN_QUERY, description="사용자 위도", type=openapi.TYPE_NUMBER, required=False),
    #         openapi.Parameter('lng', openapi.IN_QUERY, description="사용자 경도", type=openapi.TYPE_NUMBER, required=False),
    #         openapi.Parameter('radius', openapi.IN_QUERY, description="반경 (m)", type=openapi.TYPE_NUMBER, required=False),
    #     ],
    #     responses={200: PathSerializer(many=True)}
    # )
    def get(self, request):
        # 필요 시 쿼리 파라미터로 필터 가능
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        radius = float(request.query_params.get("radius", 5000))  # m 단위

        if lat is not None and lng is not None:
            try:
                lat = float(lat)
                lng = float(lng)
                user_location = Point(lng, lat, srid=4326)

                # 거리 계산 + 반경 필터링
                paths = (
                    Path.objects.filter(geom__isnull=False)
                    .annotate(distance_m=Distance("geom", user_location))
                    .filter(distance_m__lte=radius)  # km → m 변환
                    .order_by("distance_m")
                )
            except ValueError:
                return Response({"detail": "Invalid lat/lng"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            paths = Path.objects.all()

        serializer = PathSerializer(paths, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    # swagger schema 정의
    path_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "path_name": openapi.Schema(type=openapi.TYPE_STRING),
        "path_comment": openapi.Schema(type=openapi.TYPE_STRING),
        "level": openapi.Schema(type=openapi.TYPE_INTEGER),
        "distance": openapi.Schema(type=openapi.TYPE_NUMBER),
        "duration": openapi.Schema(type=openapi.TYPE_INTEGER),
        "is_private": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        "thumbnail": openapi.Schema(type=openapi.TYPE_STRING),
        "coords": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(
                type=openapi.TYPE_OBJECT,
                properties={
                    "lat": openapi.Schema(type=openapi.TYPE_NUMBER),
                    "lng": openapi.Schema(type=openapi.TYPE_NUMBER),
                    "z": openapi.Schema(type=openapi.TYPE_NUMBER),
                }
            )
        )
    }
    )
    @swagger_auto_schema(
        operation_summary="사용자 경로 등록",
        operation_description="사용자가 입력한 좌표를 기반으로 경로를 생성합니다.",
        request_body=UserPathCreateSerializer,
        responses={
            201: path_response_schema,
            400: openapi.Response("Bad Request"),
            404: openapi.Response("User Not Found")
        }
    )
    def post(self, request):
        serializer = UserPathCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            path = PathService.create_from_user_input(
                user_id=data["user_id"],
                path_name=data.get("path_name"),
                path_comment=data.get("path_comment"),
                coords_json=data["coords"],
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
            )
            if not path:
                return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            output_serializer = PathSerializer(path)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        serializer = UserPathCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            path = PathService.create_from_user_input(
                user_id=data["user_id"],
                path_name=data.get("path_name"),
                path_comment=data.get("path_comment"),
                coords_json=data["coords"],
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
            )
            if not path:
                return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            output_serializer = PathSerializer(path)
            
            # 🔽 [2. 추가] 경로 생성 성공 시, 렌더링 태스크 비동기 호출
            # path.id를 태스크에 넘겨주어 백그라운드에서 처리 시작
            render_path_and_upload.delay(path.id)
            
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)