import logging

from django.db import IntegrityError, connection, transaction
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import App
from .serializers import AppSerializer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app-list-api-django")


class HealthView(APIView):
    """Reports 200 only if the database is actually reachable, not just that the process is running."""

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            return Response({"status": "unhealthy"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"status": "ok"})


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

    def _duplicate_package_name_response(self, request, action: str) -> Response:
        logger.warning(
            "Rejected %s: package_name '%s' already exists", action, request.data.get("package_name")
        )
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
            return self._duplicate_package_name_response(request, "create")
        logger.info("Created app id=%s name=%r", serializer.instance.id, serializer.instance.name)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            return self._duplicate_package_name_response(request, f"update for app id={instance.id}")
        logger.info("Updated app id=%s name=%r", serializer.instance.id, serializer.instance.name)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        logger.info("Deactivated app id=%s name=%r", instance.id, instance.name)
        return Response(self.get_serializer(instance).data)
