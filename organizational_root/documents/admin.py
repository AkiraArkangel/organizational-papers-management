from django.contrib import admin
from .models import (
    AdviserProfile,
    Document,
    FileSectionTemplate,
    OrganizationOfficer,
    OrganizationProfile,
    SignedScannedCopy,
    SubmissionFolder,
)


@admin.register(OrganizationProfile)
class OrganizationProfileAdmin(admin.ModelAdmin):
    list_display = ('organization_name', 'created_at')


@admin.register(AdviserProfile)
class AdviserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'created_at')
    list_filter = ('organization',)


@admin.register(OrganizationOfficer)
class OrganizationOfficerAdmin(admin.ModelAdmin):
    list_display = ('position', 'name', 'organization', 'display_order')
    list_filter = ('organization',)
    search_fields = ('position', 'name', 'organization__organization_name')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_organization', 'section', 'status', 'adviser_status', 'uploaded_at')
    list_filter = ('section', 'status', 'adviser_status')
    search_fields = ('title', 'user__organizationprofile__organization_name')

    def get_organization(self, obj):
        return obj.organization_name()

    get_organization.short_description = 'Organization'


@admin.register(FileSectionTemplate)
class FileSectionTemplateAdmin(admin.ModelAdmin):
    list_display = ('section', 'uploaded_by', 'uploaded_at')


@admin.register(SubmissionFolder)
class SubmissionFolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_organization', 'section', 'created_at')
    list_filter = ('section',)
    search_fields = ('name', 'user__organizationprofile__organization_name')

    def get_organization(self, obj):
        return obj.organization_name()

    get_organization.short_description = 'Organization'


@admin.register(SignedScannedCopy)
class SignedScannedCopyAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_organization', 'folder', 'uploaded_at')
    search_fields = ('title', 'user__organizationprofile__organization_name')

    def get_organization(self, obj):
        return obj.organization_display_name()

    get_organization.short_description = 'Organization'
