from asyncio import Event
from django.contrib import admin

from .models import *

# Register your models here.
admin.site.register(Event)
admin.site.register(EventProgram)  
admin.site.register(EventSubProgram)
admin.site.register(EventAttendance)
admin.site.register(WhatsAppNotification)
admin.site.register(EventCategory)
