from django.db import IntegrityError, transaction
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from .models import App
from .serializers import AppSerializer


def _truthy(value: str) -> bool:
    return value.lower() in ("true", "1", "yes")


class AppViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """CRUD operations on the tracked-apps list.

    Only list/create/partial_update/destroy are exposed (no retrieve, no
    full PUT update) to match the FastAPI implementation's endpoint set.
    """

    queryset = App.objects.all().order_by("id")
    serializer_class = AppSerializer
    http_method_names = ["get", "post", "patch", "delete", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list" and _truthy(self.request.query_params.get("active_only", "false")):
            qs = qs.filter(is_active=True)
        return qs

    def _duplicate_package_name_response(self, request) -> Response:
        return Response(
            {"detail": f"An app with package_name '{request.data.get('package_name')}' already exists."},
            status=status.HTTP_409_CONFLICT,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            return self._duplicate_package_name_response(request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            return self._duplicate_package_name_response(request)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        return Response(self.get_serializer(instance).data)
