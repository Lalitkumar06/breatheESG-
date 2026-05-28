import sys
import os

# Make the backend package importable by the serverless function
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')
sys.path.insert(0, backend_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breathe.settings')

from breathe.wsgi import application as app  # noqa: E402, F401
