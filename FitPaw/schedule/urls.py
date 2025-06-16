from django.urls import include, path
from rest_framework.routers import DefaultRouter

from schedule.views import LessonsViewSet, TrainerViewSet

router = DefaultRouter()
router.register("trainers", TrainerViewSet, basename="trainer")
router.register("lessons",  LessonsViewSet,  basename="lesson")
urlpatterns = [
    path("/", include(router.urls)),
]