from pathlib import Path
import os
import dj_database_url


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=None):
    value = os.environ.get(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(',') if item.strip()]

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-wmzub_57!&9(v&v-1c-yjmgw6tr^7%-i%ygcrxwhvaj8ta$m%q'),
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DEBUG', env_bool('DJANGO_DEBUG', True))

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', env_list('DJANGO_ALLOWED_HOSTS', [
    'localhost',
    '127.0.0.1',
    '[::1]',
    'testserver',
]))

CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', env_list('DJANGO_CSRF_TRUSTED_ORIGINS'))


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'documents',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'organizational_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'organizational_system.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Manila'

USE_I18N = True

USE_TZ = True

# Media files configuration
if os.environ.get('SUPABASE_URL') and os.environ.get('SUPABASE_KEY'):
    # Use Supabase Storage for production (Vercel)
    from supabase import create_client
    
    # Supabase configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'documents')
    
    # Create Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    MEDIA_URL = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/"
    MEDIA_ROOT = 'media/'
    
    # Custom Supabase storage backend
    class SupabaseStorage:
        def __init__(self):
            self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            self.bucket = SUPABASE_STORAGE_BUCKET
            
        def _save(self, name, content):
            # Upload file to Supabase Storage
            content.seek(0)
            file_data = content.read()
            
            response = self.client.storage.from_(self.bucket).upload(
                path=name,
                file=file_data,
                file_options={'content-type': 'application/pdf'}
            )
            
            return name
            
        def url(self, name):
            # Get public URL for file
            return f"{SUPABASE_URL}/storage/v1/object/public/{self.bucket}/{name}"
            
        def exists(self, name):
            # Check if file exists
            try:
                self.client.storage.from_(self.bucket).get_public_url(name)
                return True
            except:
                return False
                
        def delete(self, name):
            # Delete file from Supabase Storage
            self.client.storage.from_(self.bucket).remove([name])
    
    DEFAULT_FILE_STORAGE = 'organizational_system.settings.SupabaseStorage'
else:
    # Use local filesystem for development
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL = '/login/'

SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', False)
SESSION_COOKIE_SECURE = env_bool('DJANGO_SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = env_bool('DJANGO_CSRF_COOKIE_SECURE', not DEBUG)
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', False)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
