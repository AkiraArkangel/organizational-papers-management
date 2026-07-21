import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'organizational_root'))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'organizational_system.settings')

# Configure Django
import django
django.setup()

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Vercel serverless function handler
def handler(request):
    """Vercel serverless function handler"""
    return application(request)
