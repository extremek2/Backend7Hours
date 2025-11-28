from rest_framework import viewsets, mixins
from rest_framework.exceptions import PermissionDenied
from .models import Comment
from .serializers import CommentSerializer

class BaseCommentViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = CommentSerializer

    parent_field = None          # 모델 필드 이름 (FK)
    parent_lookup_kwarg = 'id'   # URL에서 받을 파라미터 이름

    def get_queryset(self):
        parent = self.kwargs.get(self.parent_lookup_kwarg)
        return Comment.objects.filter(**{self.parent_field: parent})

    def perform_create(self, serializer):
        parent = self.kwargs.get(self.parent_lookup_kwarg)
        serializer.save(
            author=self.request.user,
            **{self.parent_field: parent}
        )

    def perform_update(self, serializer):
        comment = self.get_object()
        if comment.author != self.request.user:
            raise PermissionDenied("본인이 작성한 댓글만 수정할 수 있습니다.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("본인이 작성한 댓글만 삭제할 수 있습니다.")
        instance.delete()