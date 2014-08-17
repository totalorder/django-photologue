from __future__ import absolute_import
from io import BytesIO
import logging
import os
import zipfile
from PIL import Image
from django.contrib.sites.models import Site
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify
from celery import current_task

logger = logging.getLogger('photologue.models')

from celery import shared_task
from photologue.models import Gallery, Photo


@shared_task
def add(x, y):
    return x + y


@shared_task
def mul(x, y):
    return x * y


@shared_task
def xsum(numbers):
    return sum(numbers)

@shared_task
def process_zipfile(gallery_id, filename, idx, site_id, gallery_title, gallery_caption, gallery_is_public):
    gallery = Gallery.objects.get(pk=gallery_id)
    #zip = zipfile.ZipFile(default_storage.open(zip_file_name))
    #zipnames = sorted(zip.namelist())

    #current_task.update_state(state='PROGRESS',
    #                          meta={'current': count-1, 'total': len(zipnames)})
    #for filename in zipnames:

    logger.debug('Reading file "{0}".'.format(filename))

    #if filename.startswith('__') or filename.startswith('.') or filename.startswith("/"):
    #    logger.debug('Ignoring file "{0}".'.format(filename))
    #    continue

        #if os.path.dirname(filename):
        #logger.warning('Ignoring file "{0}" as it is in a subfolder; all images should be in the top '
        #               'folder of the zip.'.format(filename))
        #if getattr(self, 'request', None):
        #    messages.warning(self.request,
        #                     _('Ignoring file "{filename}" as it is in a subfolder; all images should '
        #                       'be in the top folder of the zip.').format(filename=filename),
        #                     fail_silently=True)
        #continue

    with open(filename) as f:
        data = f.read()

    if not len(data):
        logger.debug('File "{0}" is empty.'.format(filename))
        return

    title = ' '.join([gallery_title, str(idx)])
    slug = slugify(title)

    try:
        Photo.objects.get(slug=slug)
        logger.warning('Did not create photo "{0}" with slug "{1}" as a photo with that '
                       'slug already exists.'.format(filename, slug))
        # if getattr(self, 'request', None):
        #     messages.warning(self.request,
        #                      _('Did not create photo "%(filename)s" with slug "{1}" as a photo with that '
        #                        'slug already exists.').format(filename, slug),
        #                      fail_silently=True)
        return
    except Photo.DoesNotExist:
        pass

    photo = Photo(title=title,
                  slug=slug,
                  caption=gallery_caption,
                  is_public=gallery_is_public)
                  #tags=self.tags)

    # Basic check that we have a valid image.
    try:
        file = BytesIO(data)
        opened = Image.open(file)
        opened.verify()
    except Exception:
        # Pillow (or PIL) doesn't recognize it as an image.
        # If a "bad" file is found we just skip it.
        # But we do flag this both in the logs and to the user.
        logger.error('Could not process file "{0}" in the .zip archive.'.format(
            filename))
        # if getattr(self, 'request', None):
        #     messages.warning(self.request,
        #                      _('Could not process file "{0}" in the .zip archive.').format(
        #                          filename,
        #                          fail_silently=True))
        return

    contentfile = ContentFile(data)
    photo.image.save(os.path.split(filename)[-1], contentfile)
    photo.save()
    current_site = Site.objects.get(id=site_id)
    photo.sites.add(current_site)
    gallery.photos.add(photo)
    #count = count + 1
    #current_task.update_state(state='PROGRESS',
    #                          meta={'current': count, 'total': len(zipnames)})

    #zip.close()