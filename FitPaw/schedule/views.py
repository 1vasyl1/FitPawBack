from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Trainer, Lessons
from .serializers import TrainerSerializer, LessonsSerializer

class TrainerViewSet(viewsets.ModelViewSet):
    queryset = Trainer.objects.all().order_by('name')
    serializer_class = TrainerSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class LessonsViewSet(viewsets.ModelViewSet):
    queryset = Lessons.objects.all()
    serializer_class = LessonsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]