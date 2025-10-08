from django.contrib import admin

# Register your models here.
from .models import StudyMaterial

@admin.register(StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = ('topic', 'subtopic', 'difficulty_level')
    search_fields = ('topic', 'subtopic')
    list_filter = ('difficulty_level',)

if not admin.site.is_registered(StudyMaterial):
    admin.site.register(StudyMaterial, StudyMaterialAdmin)