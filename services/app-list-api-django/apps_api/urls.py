from rest_framework.routers import DefaultRouter

from .views import AppViewSet

router = DefaultRouter()
router.register("apps", AppViewSet, basename="app")

urlpatterns = router.urls
