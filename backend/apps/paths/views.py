from rest_framework import permissions, status, viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Exists, OuterRef
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Path
from core.models import Comment, Bookmark
from .serializers import (
    UserPathCreateSerializer,
    UserPathUpdateSerializer,
    PathSerializer,
    CommentSerializer,
)
from .services import PathService
from .permissions import IsOwnerOrReadOnly


class PathViewSet(viewsets.ModelViewSet):
    """
    산책로(Path)에 대한 API.
    기본적인 CRUD, 주변 경로 조회, 내 경로 조회, 즐겨찾기 기능을 포함합니다.
    """
    queryset = Path.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserPathCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserPathUpdateSerializer
        # 'list', 'retrieve' 및 기타 custom action
        return PathSerializer

    def get_queryset(self):
        queryset = Path.objects.select_related('auth_user').prefetch_related('comments__author').filter(is_private=False)
        user = self.request.user

        # 인증된 사용자의 경우, 즐겨찾기 여부와 개수 annotate
        if user and user.is_authenticated:
            bookmarked_subquery = Bookmark.objects.filter(
                user=user,
                content_type=ContentType.objects.get_for_model(Path),
                object_id=OuterRef('pk')
            )
            queryset = queryset.annotate(
                is_bookmarked=Exists(bookmarked_subquery)
            )
        
        queryset = queryset.annotate(
            bookmarks_count=Count('bookmarks')
        )
        
        return queryset

    @swagger_auto_schema(
        operation_summary="주변 경로 조회",
        operation_description="사용자 위치(lat/lng)와 반경(radius) 기준으로 주변 경로를 조회하거나, 파라미터가 없으면 전체 경로를 조회합니다.",
        manual_parameters=[
            openapi.Parameter('lat', openapi.IN_QUERY, description="사용자 위도", type=openapi.TYPE_NUMBER),
            openapi.Parameter('lng', openapi.IN_QUERY, description="사용자 경도", type=openapi.TYPE_NUMBER),
            openapi.Parameter('radius', openapi.IN_QUERY, description="반경 (m)", type=openapi.TYPE_NUMBER, default=5000),
        ]
    )
    def list(self, request, *args, **kwargs):
        lat = self.request.query_params.get("lat")
        lng = self.request.query_params.get("lng")
        radius = float(self.request.query_params.get("radius", 5000))

        queryset = self.get_queryset()

        if lat is not None and lng is not None:
            try:
                lat, lng = float(lat), float(lng)
                user_location = Point(lng, lat, srid=4326)
                queryset = queryset.filter(geom__isnull=False).annotate(
                    distance_m=Distance("geom", user_location)
                ).filter(distance_m__lte=radius).order_by("distance_m")
            except (ValueError, TypeError):
                queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
        
    def perform_create(self, serializer):
        data = serializer.validated_data
        PathService.create_from_user_input(
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
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def mine(self, request):
        """
        현재 인증된 사용자가 생성한 경로 목록을 반환합니다.
        """
        # queryset = self.get_queryset().filter(auth_user=request.user)
        queryset = Path.objects.select_related('auth_user').prefetch_related('comments__author').filter(auth_user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def bookmark(self, request, pk=None):
        """
        특정 산책로를 즐겨찾기 추가/삭제 (토글) 합니다.
        - POST: 즐겨찾기 추가
        - DELETE: 즐겨찾기 삭제
        """
        path = self.get_object()
        content_type = ContentType.objects.get_for_model(path)
        
        if request.method == 'POST':
            bookmark, created = Bookmark.objects.get_or_create(
                user=request.user, 
                content_type=content_type, 
                object_id=path.id
            )
            if created:
                return Response({'status': 'bookmark added'}, status=status.HTTP_201_CREATED)
            return Response({'status': 'bookmark already exists'}, status=status.HTTP_200_OK)
            
        elif request.method == 'DELETE':
            deleted_count, _ = Bookmark.objects.filter(
                user=request.user, 
                content_type=content_type, 
                object_id=path.id
            ).delete()
            if deleted_count > 0:
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({'status': 'bookmark not found'}, status=status.HTTP_404_NOT_FOUND)


class CommentViewSet(viewsets.ModelViewSet):
    """
    산책로(Path)에 대한 댓글 API.
    """
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        """
        URL 파라미터로 받은 `path_pk`에 해당하는 댓글만 필터링합니다.
        """
        path_pk = self.kwargs.get('path_pk')
        if not path_pk:
            return Comment.objects.none()
            
        content_type = ContentType.objects.get_for_model(Path)
        return Comment.objects.filter(content_type=content_type, object_id=path_pk)

    def perform_create(self, serializer):
        """
        댓글 생성 시, URL의 `path_pk`와 요청 유저 정보를 자동으로 저장합니다.
        """
        path_pk = self.kwargs.get('path_pk')
        path = Path.objects.get(pk=path_pk)
        
        serializer.save(
            author=self.request.user,
            content_object=path
        )