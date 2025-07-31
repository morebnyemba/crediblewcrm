from django.contrib import admin
from .models import Event, Ministry, Sermon

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'location', 'is_active')
    list_filter = ('is_active', 'start_time')
    search_fields = ('title', 'description', 'location')

@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    list_display = ('name', 'leader_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description', 'leader_name')

@admin.register(Sermon)
class SermonAdmin(admin.ModelAdmin):
    list_display = ('title', 'preacher', 'sermon_date', 'is_published')
    list_filter = ('is_published', 'preacher', 'sermon_date')
    search_fields = ('title', 'description', 'preacher')
