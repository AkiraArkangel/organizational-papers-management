import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'organizational_root'))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'organizational_system.settings')

# Configure Django before importing anything else
import django
django.setup()

from django.core.wsgi import get_wsgi_application

# Get the WSGI application
wsgi_app = get_wsgi_application()

# Vercel serverless function handler
def handler(event, context):
    """
    Vercel serverless function handler for Django
    """
    from django.http import HttpResponse
    from django.core.handlers.wsgi import WSGIHandler
    
    # Create a simple WSGI environment from the Vercel event
    environ = {
        'REQUEST_METHOD': event.get('method', 'GET'),
        'PATH_INFO': event.get('path', '/'),
        'QUERY_STRING': event.get('query', ''),
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '80',
        'wsgi.url_scheme': 'https',
        'wsgi.input': event.get('body', b''),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False,
    }
    
    # Add headers
    for key, value in event.get('headers', {}).items():
        environ[f'HTTP_{key.upper().replace("-", "_")}'] = value
    
    # Create response
    def start_response(status, response_headers):
        return None
    
    # Call the WSGI application
    response = wsgi_app(environ, start_response)
    
    return {
        'statusCode': 200,
        'body': ''.join(response),
        'headers': {
            'Content-Type': 'text/html',
        }
    }

# For Vercel's Python runtime
def app(environ, start_response):
    """Standard WSGI application for Vercel"""
    return wsgi_app(environ, start_response)
