from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.sites.models import Site
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import ungettext, ugettext_lazy as _
from django.core.urlresolvers import reverse
from celery_app import app as cel_app

from .models import Gallery, Photo, GalleryUpload, PhotoEffect, PhotoSize, \
    Watermark

MULTISITE = getattr(settings, 'PHOTOLOGUE_MULTISITE', False)


class GalleryAdminForm(forms.ModelForm):

    class Meta:
        model = Gallery
        if MULTISITE:
            exclude = []
        else:
            exclude = ['sites']


class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_added', 'photo_count', 'is_public')
    list_filter = ['date_added', 'is_public']
    if MULTISITE:
        list_filter.append('sites')
    date_hierarchy = 'date_added'
    prepopulated_fields = {'slug': ('title',)}
    form = GalleryAdminForm
    if MULTISITE:
        filter_horizontal = ['sites']
    if MULTISITE:
        actions = [
            'add_to_current_site',
            'add_photos_to_current_site',
            'remove_from_current_site',
            'remove_photos_from_current_site'
        ]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """ Set the current site as initial value. """
        if db_field.name == "sites":
            kwargs["initial"] = [Site.objects.get_current()]
        return super(GalleryAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def save_related(self, request, form, *args, **kwargs):
        """
        If the user has saved a gallery with a photo that belongs only to
        different Sites - it might cause much confusion. So let them know.
        """
        super(GalleryAdmin, self).save_related(request, form, *args, **kwargs)
        orphaned_photos = form.instance.orphaned_photos()
        if orphaned_photos:
            msg = ungettext(
                'The following photo does not belong to the same site(s)'
                ' as the gallery, so will never be displayed: %(photo_list)s.',
                'The following photos do not belong to the same site(s)'
                ' as the gallery, so will never be displayed: %(photo_list)s.',
                len(orphaned_photos)
            ) % {'photo_list': ", ".join([photo.title for photo in orphaned_photos])}
            messages.warning(request, msg)

    def add_to_current_site(modeladmin, request, queryset):
        current_site = Site.objects.get_current()
        current_site.gallery_set.add(*queryset)
        msg = ungettext(
            "The gallery has been successfully added to %(site)s",
            "The galleries have been successfully added to %(site)s",
            len(queryset)
        ) % {'site': current_site.name}
        messages.success(request, msg)

    add_to_current_site.short_description = \
        _("Add selected galleries from the current site")

    def remove_from_current_site(modeladmin, request, queryset):
        current_site = Site.objects.get_current()
        current_site.gallery_set.remove(*queryset)
        msg = ungettext(
            "The gallery has been successfully removed from %(site)s",
            "The selected galleries have been successfully removed from %(site)s",
            len(queryset)
        ) % {'site': current_site.name}
        messages.success(request, msg)

    remove_from_current_site.short_description = \
        _("Remove selected galleries from the current site")

    def add_photos_to_current_site(modeladmin, request, queryset):
        photos = Photo.objects.filter(galleries__in=queryset)
        current_site = Site.objects.get_current()
        current_site.photo_set.add(*photos)
        msg = ungettext(
            'All photos of gallery %(galleries)s have been successfully '
            'added to %(site)s',
            'All photos of in the galleries %(galleries)s have been successfully '
            'added to %(site)s',
            len(queryset)
        ) % {
            'site': current_site.name,
            'galleries': ", ".join(["'{0}'".format(gallery.title)
                                    for gallery in queryset])
        }
        messages.success(request, msg)

    add_photos_to_current_site.short_description = \
        _("Add all photos of selected galleries to the current site")

    def remove_photos_from_current_site(modeladmin, request, queryset):
        photos = Photo.objects.filter(galleries__in=queryset)
        current_site = Site.objects.get_current()
        current_site.photo_set.remove(*photos)
        msg = ungettext(
            'All photos of gallery %(galleries)s have been successfully '
            'removed from %(site)s',
            'All photos of in the galleries %(galleries)s have been successfully '
            'removed from %(site)s',
            len(queryset)
        ) % {
            'site': current_site.name,
            'galleries': ", ".join(["'{0}'".format(gallery.title)
                                    for gallery in queryset])
        }
        messages.success(request, msg)

    remove_photos_from_current_site.short_description = \
        _("Remove all photos of selected galleries from the current site")

admin.site.register(Gallery, GalleryAdmin)


class GalleryUploadAdmin(admin.ModelAdmin):

    def has_change_permission(self, request, obj=None):
        return False  # To remove the 'Save and continue editing' button

    def save_model(self, request, obj, form, change):
        # Warning the user when things go wrong in a zip upload.
        obj.request = request
        obj.save()

    def response_add(self, request, obj, post_url_continue="../%s/"):
        if not '_continue' in request.POST:
            return redirect(reverse('celery_poll_job', args=[request.celery_poll_job_id,
                                                             request.celery_poll_job_length,
                                                             request.celery_poll_job_gallery]))
        else:
            return super(GalleryUploadAdmin, self).response_add(request, obj, post_url_continue)


admin.site.register(GalleryUpload, GalleryUploadAdmin)


class PhotoAdminForm(forms.ModelForm):

    class Meta:
        model = Photo
        if MULTISITE:
            exclude = []
        else:
            exclude = ['sites']


class PhotoAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_taken', 'date_added',
                    'is_public', 'tags', 'view_count', 'admin_thumbnail')
    list_filter = ['date_added', 'is_public']
    if MULTISITE:
        list_filter.append('sites')
    search_fields = ['title', 'slug', 'caption']
    list_per_page = 10
    prepopulated_fields = {'slug': ('title',)}
    form = PhotoAdminForm
    if MULTISITE:
        filter_horizontal = ['sites']
    if MULTISITE:
        actions = ['add_photos_to_current_site', 'remove_photos_from_current_site']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """ Set the current site as initial value. """
        if db_field.name == "sites":
            kwargs["initial"] = [Site.objects.get_current()]
        return super(PhotoAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def add_photos_to_current_site(modeladmin, request, queryset):
        current_site = Site.objects.get_current()
        current_site.photo_set.add(*queryset)
        msg = ungettext(
            'The photo has been successfully added to %(site)s',
            'The selected photos have been successfully added to %(site)s',
            len(queryset)
        ) % {'site': current_site.name}
        messages.success(request, msg)

    add_photos_to_current_site.short_description = \
        _("Add selected photos to the current site")

    def remove_photos_from_current_site(modeladmin, request, queryset):
        current_site = Site.objects.get_current()
        current_site.photo_set.remove(*queryset)
        msg = ungettext(
            'The photo has been successfully removed from %(site)s',
            'The selected photos have been successfully removed from %(site)s',
            len(queryset)
        ) % {'site': current_site.name}
        messages.success(request, msg)

    remove_photos_from_current_site.short_description = \
        _("Remove selected photos from the current site")

admin.site.register(Photo, PhotoAdmin)


class PhotoEffectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color', 'brightness',
                    'contrast', 'sharpness', 'filters', 'admin_sample')
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Adjustments', {
            'fields': ('color', 'brightness', 'contrast', 'sharpness')
        }),
        ('Filters', {
            'fields': ('filters',)
        }),
        ('Reflection', {
            'fields': ('reflection_size', 'reflection_strength', 'background_color')
        }),
        ('Transpose', {
            'fields': ('transpose_method',)
        }),
    )

admin.site.register(PhotoEffect, PhotoEffectAdmin)


class PhotoSizeAdmin(admin.ModelAdmin):
    list_display = ('name', 'width', 'height', 'crop', 'pre_cache', 'effect', 'increment_count')
    fieldsets = (
        (None, {
            'fields': ('name', 'width', 'height', 'quality')
        }),
        ('Options', {
            'fields': ('upscale', 'crop', 'pre_cache', 'increment_count')
        }),
        ('Enhancements', {
            'fields': ('effect', 'watermark',)
        }),
    )

admin.site.register(PhotoSize, PhotoSizeAdmin)


class WatermarkAdmin(admin.ModelAdmin):
    list_display = ('name', 'opacity', 'style')


admin.site.register(Watermark, WatermarkAdmin)


def celery_poll_job(request, job_id, job_length, job_gallery_id):
    job_length, job_gallery_id = int(job_length), int(job_gallery_id)
    group_result = cel_app.backend.restore_group(job_id)

    failed_count = sum(int(result.failed()) for result in group_result.results)
    completed_count = group_result.completed_count()

    if completed_count + failed_count == job_length:
        return redirect(reverse('admin:photologue_gallery_change', args=[job_gallery_id]))

    gallery = Gallery.objects.get(pk=job_gallery_id)
    return render(request, 'photologue/poll_job.html',
                  {'completed': completed_count, 'failed': failed_count, 'total': job_length, 'gallery': gallery,
                   'opts': Gallery._meta})
