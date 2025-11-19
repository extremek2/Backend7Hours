from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from .models import Post, Like, Bookmark
from .serializers import PostSerializer
from .permissions import IsOwnerOrReadOnly


# ------------------------------
# Post CRUD
# ------------------------------
class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated & IsOwnerOrReadOnly]
    parser_classes = [MultiPartParser, FormParser] 

    def get_queryset(self):
        return Post.objects.select_related('auth_user').all()

    def perform_create(self, serializer):
        serializer.save(auth_user=self.request.user)


# ------------------------------
# Like Toggle API
# ------------------------------
class LikeToggleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        # 자기 글에는 좋아요 불가
        if post.auth_user == request.user:
            return Response({"detail": "자기 글에는 좋아요할 수 없습니다."}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        content_type = ContentType.objects.get_for_model(post)

        like, created = Like.objects.get_or_create(
            user=request.user,
            content_type=content_type,
            object_id=post.id
        )

        if not created:
            like.delete()
            return Response({
                'liked': False,
                'likes_count': post.likes.count()
            }, status=status.HTTP_200_OK)

        return Response({
            'liked': True,
            'likes_count': post.likes.count()
        }, status=status.HTTP_201_CREATED)


# ------------------------------
# Bookmark Toggle API
# ------------------------------
class BookmarkToggleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        # 자기 글에는 북마크 불가
        if post.auth_user == request.user:
            return Response({"detail": "자기 글에는 북마크할 수 없습니다."},
                            status=status.HTTP_400_BAD_REQUEST)
        
        content_type = ContentType.objects.get_for_model(post)

        bookmark, created = Bookmark.objects.get_or_create(
            user=request.user,
            content_type=content_type,
            object_id=post.id
        )

        if not created:
            bookmark.delete()
            return Response({
                'bookmarked': False,
                'bookmarks_count': post.bookmarks.count()
            }, status=status.HTTP_200_OK)

        return Response({
            'bookmarked': True,
            'bookmarks_count': post.bookmarks.count()
        }, status=status.HTTP_201_CREATED)