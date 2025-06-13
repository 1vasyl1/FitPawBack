from django.urls import path
from rest_framework.routers import DefaultRouter

from schedule.views import LessonsViewSet, TrainerViewSet

router = DefaultRouter()
router.register('lessons', LessonsViewSet, basename='lessons')
router.register('trainers', TrainerViewSet, basename='trainers')
urlpatterns = router.urls