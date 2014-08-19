from __future__ import absolute_import
from io import BytesIO
import logging
import os
from PIL import Image
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify
from celery import shared_task

logger = logging.getLogger('photologue.models')


class PhotoProcessException(Exception):
    def __init__(self, message, filename):
        super(PhotoProcessException, self).__init__(message)
        self.filename = filename


@shared_task(bind=True, max_retries=5)
def process_photo(self, gallery_id, filename, idx, site_id, gallery_title, gallery_caption, gallery_is_public):
    # This is initiated by photologue.models.Gallery.process_zipfile, but executed in an isolated celery task.
    # This gives a circular dependency on import time, but is not executed circularly.
    print settings.MEDIA_ROOT
    from photologue.models import Gallery, Photo
    try:
        gallery = Gallery.objects.get(pk=gallery_id)
    except Gallery.DoesNotExist:
        # Since the django admin views are in atomic transactions the gallery might not have been commited yet.
        self.retry(countdown=1)

    logger.debug('Reading file "{0}".'.format(filename))
    data = default_storage.open(filename).read()

    title = ' '.join([gallery_title, str(idx)])
    slug = slugify(title)

    try:
        Photo.objects.get(slug=slug)
        logger.warning('Did not create photo "{0}" with slug "{1}" as a photo with that '
                       'slug already exists.'.format(filename, slug))
        raise PhotoProcessException("Slug already exists!", filename)
    except Photo.DoesNotExist:
        pass

    photo = Photo(title=title,
                  slug=slug,
                  caption=gallery_caption,
                  is_public=gallery_is_public)
                  #tags=self.tags) # FIXME

    # Basic check that we have a valid image.
    try:
        file = BytesIO(data)
        opened = Image.open(file)
        opened.verify()
    except Exception:
        # Pillow (or PIL) doesn't recognize it as an image.
        # If a "bad" file is found we just skip it.
        # But we do flag this both in the logs and to the user.
        logger.error('Could not process image "{0}".'.format(
            filename))
        raise PhotoProcessException("Not an image!", filename)

    contentfile = ContentFile(data)
    photo.image.save(os.path.split(filename)[-1], contentfile)
    photo.save()
    current_site = Site.objects.get(id=site_id)
    photo.sites.add(current_site)
    gallery.photos.add(photo)