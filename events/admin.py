from asyncio import Event
from os import path
from pyexpat.errors import messages
from django.contrib import admin
from django.db import connection
from django.shortcuts import redirect

from .models import *

# Register your models here.
admin.site.register(Event)  
admin.site.register(EventProgram)  
admin.site.register(EventSubProgram)
admin.site.register(EventAttendance)
admin.site.register(WhatsAppNotification)
admin.site.register(EventCategory)



