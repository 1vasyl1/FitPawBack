from django.contrib import admin

from .models import StripeWebhookEvent


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "received_at", "processed_at")
    search_fields = ("event_id", "event_type")
    readonly_fields = ("event_id", "event_type", "payload", "received_at", "processed_at")
