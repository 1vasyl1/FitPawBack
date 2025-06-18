from django.utils.translation import gettext_lazy as _
from unfold.sites import UnfoldAdminSite
from schedule.admin import TrainerAdmin, LessonAdmin
from schedule.models import Trainer, Lessons

class StaffAdminSite(UnfoldAdminSite):

    def each_context(self, request):
        context = super().each_context(request)
        context['site_header'] = _("Staff Dashboard")
        context['site_title'] = _("Staff Portal")
        self.index_title = _("Witaj na panelu Staff")
        return context

    def has_permission(self, request):
        user = request.user
        return user.is_active and user.is_staff

staff_admin = StaffAdminSite(name="staff_admin")
staff_admin.register(Trainer, TrainerAdmin)
staff_admin.register(Lessons, LessonAdmin)
