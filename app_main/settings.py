import os
import django_heroku
import dj_database_url
from django.utils.log import DEFAULT_LOGGING
from django.utils.log import configure_logging


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "CHANGE_ME!!!! (P.S. the SECRET_KEY environment variable will be used, if set, instead)."

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Forms template
CRISPY_TEMPLATE_PACK = "bootstrap4"

# Application definition

INSTALLED_APPS = [
    "app_main",
    "app_db_logger",
    "app_web",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_fsm_log",
    "subscriptions.apps.SubscriptionsConfig",
    'multiselectfield',
    "crispy_forms",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app_main.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "app_main.wsgi.application"

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
}

# Logger
# https://docs.djangoproject.com/en/3.0/topics/logging/

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'formatters': {
        'django.server': DEFAULT_LOGGING['formatters']['django.server'],
        'verbose': {
            # TODO: comment before deploying
            # '()': 'djangocolors_formatter.DjangoColorsFormatter',
            'format': '[%(asctime)s] %(levelname)s [%(name)s] [%(pathname)s.%(funcName)s:%(lineno)d] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            # TODO: comment before deploying
            # '()': 'djangocolors_formatter.DjangoColorsFormatter',
            'format': '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'msg': {
            'format': '%(message)s',
        },
    },
    'handlers': {
        'django.server': DEFAULT_LOGGING['handlers']['django.server'],
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'console_simple': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        # 'production_logfile': {
        #     'level': 'ERROR',
        #     'filters': ['require_debug_false'],
        #     'class': 'logging.handlers.RotatingFileHandler',
        #     'filename': '/var/log/django/django_production.log',
        #     'maxBytes' : 1024*1024*100, # 100MB
        #     'backupCount' : 5,
        #     'formatter': 'simple'
        # },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        },
        'db_log': {
            'level': 'INFO',
            # 'filters': ['require_debug_false'],
            'class': 'app_db_logger.db_log_handler.DatabaseLogHandler',
            'formatter': 'msg',
        },
    },
    # 'root': {
    #     'level': 'DEBUG',
    #     'handlers': ['console'],
    # },
    'loggers': {
        # TODO: uncomment before deploying
        '': {
           'level': 'DEBUG',
           'handlers': ['console'],
        },
        'django.server': DEFAULT_LOGGING['loggers']['django.server'],
        'django.security': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'py.warnings': {
            'handlers': ['console'],
            'propagate': False
        },
        'decorator': {
            'level': 'DEBUG',
            'handlers': ['console_simple'],
            'propagate': False
        },
        'db': {
            'level': 'INFO',
            'handlers': ['db_log', 'console'],
            'propagate': False
        }
    },
}

LOGGING_CONFIG = 'logging.config.dictConfig'
configure_logging(LOGGING_CONFIG, LOGGING)

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# TODO: change
# send emails to console for testing purposes
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = "en-us"

USE_TZ = False
TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = "/static/"

django_heroku.settings(locals(), logging=False)

""" 
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERYBEAT_SCHEDULE = {
    "subscriptions_renewals": {
        "task": "subscriptions.tasks.trigger_renewals",
        "schedule": crontab(hour=0, minute=10),
    },
    "subscriptions_expiring": {
        "task": "subscriptions.tasks.trigger_expiring",
        "schedule": crontab(hour=0, minute=15),
    },
    "subscriptions_suspended": {
        "task": "subscriptions.tasks.trigger_suspended",
        "schedule": crontab(hour="3,6,9", minute=30),
    },
    "subscriptions_suspended_timeout": {
        "task": "subscriptions.tasks.trigger_suspended_timeout",
        "schedule": crontab(hour=0, minute=40),
        "kwargs": {"hours": 48},
    },
    "subscriptions_stuck": {
        "task": "subscriptions.tasks.trigger_stuck",
        "schedule": crontab(hour="*/2", minute=50),
        "kwargs": {"hours": 2},
    },
}
 """

