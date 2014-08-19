import logging
from django.core.files.storage import default_storage
from celery import shared_task

logger = logging.getLogger('photologue.models')

@shared_task(bind=True, max_retries=5)
def process_photo(self, gallery_id, filename, number, gallery_title, gallery_caption, gallery_is_public):
    # This is initiated by photologue.models.Gallery.process_zipfile, but executed in an isolated celery task.
    # This gives a circular dependency on import time, but is not executed circularly.
    from photologue.models import Gallery, GalleryUpload
    try:
        gallery = Gallery.objects.get(pk=gallery_id)
    except Gallery.DoesNotExist:
        gallery = None
        # Since the django admin views are in atomic transactions the gallery might not have been commited yet.
        self.retry(countdown=1)

    logger.debug('Reading file "{0}".'.format(filename))
    data = default_storage.open(filename).read()
    GalleryUpload.process_photo(gallery, data, filename, number, gallery_title, gallery_caption, gallery_is_public)
