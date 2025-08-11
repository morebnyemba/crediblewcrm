# whatsappcrm_backend/whatsappcrm_backend/settings.py

import os
from pathlib import Path
from datetime import timedelta
import dotenv # For loading .env file
from celery.schedules import crontab

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Environment Variables ---
# Load .env file from the project root
dotenv_file = BASE_DIR / '.env'
if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-fallback-key-for-dev-only-replace-me-in-env') # Ensure this is in your .env

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True' # Default to True for dev if not set

# --- Allowed Hosts ---
# Add your backend domain here. For WebSocket connections to work with
# AllowedHostsOriginValidator, you must also include your frontend domain.
ALLOWED_HOSTS_STRING = os.getenv('DJANGO_ALLOWED_HOSTS',
    'localhost,127.0.0.1,crmbackend.lifeinternationalministries.com,crmfrontend.lifeinternationalministries.com'
)
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()]

# --- CSRF Trusted Origins ---
# Add your frontend domains that will make state-changing requests (POST, PUT, etc.).
# This is crucial for your React frontend to be able to log in and submit data.
CSRF_TRUSTED_ORIGINS_STRING = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173,https://crmfrontend.lifeinternationalministries.com,https://crmbackend.lifeinternationalministries.com'
)
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_STRING.split(',') if origin.strip()]


# Application definition
INSTALLED_APPS = [
    'channels', # Channels must be listed first
    'jazzmin', # Jazzmin must be before django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist', 
    'corsheaders',
    'django_celery_results',
    'django_celery_beat',
    'media_manager.apps.MediaManagerConfig',
    'django_extensions', # Useful for development, optional
    'drf_spectacular', # For OpenAPI schema generation
    'django_prometheus', # For metrics collection

    # Our apps
    "paynow_integration.apps.PaynowIntegrationConfig",
    "stats",
    'meta_integration.apps.MetaIntegrationConfig',
    'conversations.apps.ConversationsConfig',
    'flows.apps.FlowsConfig',
    'customer_data.apps.CustomerDataConfig',
    'church_services.apps.ChurchServicesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 
    'corsheaders.middleware.CorsMiddleware', # Should be placed high
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'whatsappcrm_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Optional project-level templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'whatsappcrm_backend.wsgi.application'
ASGI_APPLICATION = 'whatsappcrm_backend.asgi.application' # Crucial for Django Channels


# Database
DB_ENGINE_DEFAULT = 'django.db.backends.postgresql'
DB_NAME_DEFAULT = 'whatsapp_crm_dev'  # The database name you created
DB_USER_DEFAULT = 'crm_user'          # The user you created
DB_PASSWORD_DEFAULT = ''                # It's best to set this in your .env file
DB_HOST_DEFAULT = 'localhost'           # Or '127.0.0.1'
DB_PORT_DEFAULT = '5432'                # Default PostgreSQL port

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', DB_ENGINE_DEFAULT),
        'NAME': os.getenv('DB_NAME', DB_NAME_DEFAULT),
        'USER': os.getenv('DB_USER', DB_USER_DEFAULT),
        'PASSWORD': os.getenv('DB_PASSWORD', DB_PASSWORD_DEFAULT), # Ensure this is in your .env!
        'HOST': os.getenv('DB_HOST', DB_HOST_DEFAULT),
        'PORT': os.getenv('DB_PORT', DB_PORT_DEFAULT),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Harare' 
USE_I18N = True
USE_TZ = True 

# Static files
STATIC_URL = '/static/' 
STATIC_ROOT = BASE_DIR / 'staticfiles' # For production `collectstatic`

# Media files (user-uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles' # Path where user-uploaded files will be stored.

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Django REST Framework Settings ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication', # For browsable API & Django Admin
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated', # Default to requiring authentication
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20, 
}

# --- Simple JWT Settings ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', '60'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', '7'))),
    'ROTATE_REFRESH_TOKENS': os.getenv('JWT_ROTATE_REFRESH_TOKENS', 'True') == 'True',
    'BLACKLIST_AFTER_ROTATION': os.getenv('JWT_BLACKLIST_AFTER_ROTATION', 'True') == 'True',
    'UPDATE_LAST_LOGIN': os.getenv('JWT_UPDATE_LAST_LOGIN', 'False') == 'True',
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY, 
    'VERIFYING_KEY': None, 
    'AUDIENCE': None, 'ISSUER': None, 'JWK_URL': None, 'LEEWAY': timedelta(seconds=0),
    'AUTH_HEADER_TYPES': ('Bearer',), 
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id', 'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type', 'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_SLIDING_TOKEN_LIFETIME_MINUTES', '5'))),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=int(os.getenv('JWT_SLIDING_TOKEN_REFRESH_LIFETIME_DAYS', '1'))),
}

# --- CORS Settings ---
# This tells the browser that it's safe to accept cross-origin requests from your frontend.
CORS_ALLOWED_ORIGINS_STRING = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173,https://crmfrontend.lifeinternationalministries.com'
)
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ALLOWED_ORIGINS_STRING.split(',') if origin.strip()]
CORS_ALLOW_CREDENTIALS = True

# --- Celery Configuration ---
# Ensure your Redis server is running and accessible at this URL.
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db' # Use a different DB for results
CELERY_ACCEPT_CONTENT = ['json'] # Content types to accept
CELERY_TASK_SERIALIZER = 'json'  # How tasks are serialized
CELERY_RESULT_SERIALIZER = 'json'# How results are serialized
CELERY_TIMEZONE = TIME_ZONE # Use Django's timezone (should be 'UTC')
CELERY_TASK_TRACK_STARTED = True # Optional: To track if a task has started
CELERY_TASK_TIME_LIMIT = int(os.getenv('CELERY_TASK_TIME_LIMIT_SECONDS', '1800')) # Optional: Hard time limit for tasks (e.g., 30 minutes)
CELERY_RESULT_EXTENDED = True
CELERY_CACHE_BACKEND = 'django-cache'

# --- Channels (WebSocket) Configuration ---
# For development, you can use the in-memory backend.
# For production, Redis is strongly recommended.
CHANNEL_LAYERS = {
    "default": {
        # Use Redis in production for a robust, scalable channel layer
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            # In a Docker environment, 'localhost' refers to the container itself.
            # You must use the service name of the Redis container (e.g., 'redis') and password
            # as defined in your docker-compose.yml file.
            "hosts": [os.getenv('REDIS_URL', 'redis://redis:6379/1')],
        },
        # Use in-memory for local development if you don't have Redis running
        # "BACKEND": "channels.layers.InMemoryChannelLayer"
    },
}

# For Celery Beat (scheduled tasks)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    'check-for-birthdays-daily': {
        'task': 'customer_data.tasks.check_for_birthdays_and_dispatch_messages',
        # Runs every day at 8:00 AM (server time, which is set to Africa/Harare)
        'schedule': crontab(hour=8, minute=0),
        'args': (),
    },
}


# --- Application-Specific Settings ---
CONVERSATION_EXPIRY_DAYS = int(os.getenv('CONVERSATION_EXPIRY_DAYS', '60'))
ADMIN_WHATSAPP_NUMBER = os.getenv('ADMIN_WHATSAPP_NUMBER', None) # e.g., '15551234567'

# --- Church Details ---
# Centralized details for use in templates, exports, and messages.
CHURCH_DETAILS = {
    'NAME': os.getenv('CHURCH_NAME', 'Life International Ministries'),
    'ADDRESS_LINE_1': os.getenv('CHURCH_ADDRESS_LINE_1', '123 Gospel Lane'),
    'ADDRESS_LINE_2': os.getenv('CHURCH_ADDRESS_LINE_2', 'Faith City, ZW'),
    'CONTACT_PHONE': os.getenv('CHURCH_CONTACT_PHONE', '+263 123 456789'),
    'CONTACT_EMAIL': os.getenv('CHURCH_CONTACT_EMAIL', 'info@church.com'),
    'WEBSITE': os.getenv('CHURCH_WEBSITE', 'www.lifeinternationalministries.com'),
    'MOTTO': os.getenv('CHURCH_MOTTO', 'Serving the Community with Faith'),
}


print("--- DEBUGGING ENVIRONMENT VARIABLES ---")
celery_log_level_env = os.getenv('CELERY_LOG_LEVEL')
print(f"Value of CELERY_LOG_LEVEL from os.getenv: '{celery_log_level_env}' (Type: {type(celery_log_level_env)})")

effective_celery_level_for_config = os.getenv('CELERY_LOG_LEVEL', 'INFO')
print(f"Effective level used for Celery logger config: '{effective_celery_level_for_config}' (Type: {type(effective_celery_level_for_config)})")
print("------------------------------------")


# --- Logging Configuration ---
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}', 'style': '{'},
        'simple': {'format': '[{asctime}] {levelname} {module} {message}', 'style': '{', 'datefmt': '%Y-%m-%d %H:%M:%S'},
    },
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'), 'propagate': False},
        'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
        'celery': {'handlers': ['console'], 'level': 'INFO', 'propagate': True},
        'meta_integration': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': True},
        'conversations': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': True},
        'flows': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': True},
        'customer_data': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': True},
    },
}

WHATSAPP_APP_SECRET = os.getenv('WHATSAPP_APP_SECRET', None)
# --- Jazzmin Admin Theme Settings ---
JAZZMIN_SETTINGS = {
    "site_title": "AutoWhats",
    "site_header": CHURCH_DETAILS['NAME'],
    "site_brand": "A-W",
    "site_logo_classes": "img-circle",
    # Path to logo, relative to static files.
    # It should not include /static/ in the path.
    "site_logo": "./admin/img/logo.png",
    "welcome_sign": "Welcome to the AutoWhats Admin",
    "copyright": "Slyker Tech Web Services and Patners.",
    "search_model": ["auth.User", "meta_integration.MetaAppConfig", "conversations.Contact", "flows.Flow"],
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"model": "auth.User"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "icons": {
        "auth": "fas fa-users-cog", "auth.user": "fas fa-user", "auth.Group": "fas fa-users",
        "meta_integration": "fab fa-whatsapp-square",
        "meta_integration.MetaAppConfig": "fas fa-cogs", "meta_integration.WebhookEventLog": "fas fa-history",
        "conversations": "fas fa-comments",
        "conversations.Contact": "fas fa-address-book", "conversations.Message": "fas fa-envelope",
        "flows": "fas fa-project-diagram",
        "flows.Flow": "fas fa-bezier-curve", "flows.FlowStep": "fas fa-shoe-prints",
        "flows.FlowTransition": "fas fa-route", "flows.ContactFlowState": "fas fa-map-signs",
        "customer_data": "fas fa-church",
        "customer_data.Family": "fas fa-users",
        "customer_data.MemberProfile": "fas fa-user-tag",
        "customer_data.PendingVerificationPayment": "fas fa-check-double",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "show_ui_builder": False, # Set to True in dev to customize Jazzmin theme via UI
    "changeform_format": "horizontal_tabs",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False, "footer_small_text": False, "body_small_text": False,
    "brand_small_text": False, "brand_colour": "navbar-success", "accent": "accent-teal",
    "navbar": "navbar-dark navbar-success", "no_navbar_border": False, "navbar_fixed": True,
    "layout_boxed": False, "footer_fixed": False, "sidebar_fixed": True,
    "sidebar": "sidebar-dark-success", "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False, "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False, "sidebar_nav_flat_style": False,
    "sidebar_nav_legacy_style": False, "sidebar_nav_accordion": True,
    "actions_sticky_top": True
}

# Ensure your .env file has DJANGO_SECRET_KEY and other sensitive variables.
# Example .env content (should be in a separate .env file at project root):
# DJANGO_SECRET_KEY="your-actual-strong-secret-key-here"
# DJANGO_DEBUG="False" # Set to "False" for production
# DJANGO_ALLOWED_HOSTS="crmbackend.lifeinternationalministries.com,localhost,127.0.0.1"
# CSRF_TRUSTED_ORIGINS="https://crmfrontend.lifeinternationalministries.com,http://localhost:5173"
# CORS_ALLOWED_ORIGINS="https://crmfrontend.lifeinternationalministries.com,http://localhost:5173"
# CELERY_BROKER_URL="redis://localhost:6379/0"
# CELERY_RESULT_BACKEND="redis://localhost:6379/1"
# DB_ENGINE="django.db.backends.postgresql" # Or your preferred DB
# DB_NAME="your_db_name"
CONVERSATION_EXPIRY_DAYS="60"
ADMIN_WHATSAPP_NUMBER="+263787211325"
JWT_ACCESS_TOKEN_LIFETIME_MINUTES="60"
CHURCH_GIVING_DETAILS = {
    'BANK_NAME': os.getenv('CHURCH_BANK_NAME', 'Steward Bank'),
    'ACCOUNT_NUMBER': os.getenv('CHURCH_ACCOUNT_NUMBER', '123456789'),
    'MERCHANT_CODE': os.getenv('CHURCH_MERCHANT_CODE', '*123*456*1#'),
    'DEFAULT_CURRENCY': os.getenv('DEFAULT_GIVING_CURRENCY', 'USD'),
}

# You can then add these to your .env file:
# CHURCH_BANK_NAME="Steward Bank"
# CHURCH_ACCOUNT_NUMBER="123456789"
# CHURCH_MERCHANT_CODE="*123*456*1#"
# DEFAULT_GIVING_CURRENCY="USD"
JWT_REFRESH_TOKEN_LIFETIME_DAYS="7"
