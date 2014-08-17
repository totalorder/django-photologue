from __future__ import absolute_import
import os

__version__ = '3.0.dev0'

PHOTOLOGUE_APP_DIR = os.path.dirname(os.path.abspath(__file__))

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery_app import app as celery_app