from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import UserPathCreateSerializer, PathSerializer
from .services import PathService
from django.contrib.auth.models import User
from .models import Path

class UserPathCreateView(APIView):
    """
    GET: DB에 존재하는 모든 경로 반환 (사용자+추천)
    POST: 사용자 입력 좌표로 경로 생성
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.AllowAny()]
            # return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get(self, request):
        # 필요 시 쿼리 파라미터로 필터 가능
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        radius = int(request.query_params.get("radius", 3))

        if lat and lng:
            user_location = Point(float(lng), float(lat), srid=4326)

            # 거리 계산 + 반경 필터링
            paths = (
                Path.objects.annotate(distance=Distance("geom", user_location))
                .filter(distance__lte=radius_km * 1000)  # km → m 변환
                .order_by("distance")
            )
        else:
            paths = Path.objects.all()

        serializer = PathSerializer(paths, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = UserPathCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            path = PathService.create_from_user_input(
                user_id=data["user_id"],
                path_name=data.get("path_name"),
                path_comment=data.get("path_comment"),
                coords_2d=data["coords"],
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
            )
            if not path:
                return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            output_serializer = PathSerializer(path)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)