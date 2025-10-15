from django.contrib import admin
from .models import Member, Ministry, Group, Family, Attendance

# ----------------------
# Administration des Membres
# ----------------------
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'member_id', 'email', 'phone', 'status','nationalite','nombres_enfant','domaines')
    list_filter = ('status', 'gender', 'ministries', 'groups')
    search_fields = ('first_name', 'last_name', 'member_id', 'email', 'phone')
    ordering = ('last_name',)
    filter_horizontal = ('ministries', 'groups')  # Pour ManyToManyField

# ----------------------
# Administration des Ministères
# ----------------------
@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

# ----------------------
# Administration des Groupes
# ----------------------
@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

# ----------------------
# Administration des Familles
# ----------------------
@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ('name', )
    search_fields = ('name',)

# ----------------------
# Administration des Présences
# ----------------------
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('member', 'date', 'present')
    list_filter = ('date', 'present')
    search_fields = ('member__first_name', 'member__last_name')
    date_hierarchy = 'date'
