from rest_framework import serializers
from .models import Lessons, Trainer

class TrainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trainer
        fields = 'id', 'name', 'bio'

class LessonsSerializer(serializers.ModelSerializer):
    trainer = TrainerSerializer(read_only=True)
    trainer_id = serializers.PrimaryKeyRelatedField(
        source="trainer", queryset=Trainer.objects.all(), write_only=True
    )
    class Meta:
        model = Lessons
        fields = [
            'id','date',
            'start_time','end_time',
            'subject','location',
            'trainer','trainer_id',
        ]