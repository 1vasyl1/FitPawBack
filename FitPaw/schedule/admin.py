from django.contrib import admin
from schedule.models import Lessons, Trainer

@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ("name", "bio")
    search_fields = ("name",)

@admin.register(Lessons)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("subject", "date", "start_time", "end_time", "location", "trainer")
    list_filter = ("date", "trainer")
    search_fields = ("subject",)
