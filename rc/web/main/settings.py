"""
Django settings for main project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import os.path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'jneti7!uj+_0isd66^1f@a4g($_x3ewcvq^w_a9c5omeju$pjv'

# SECURITY WARNING: don't run with debug turned on in production!
if os.environ.get('DJANGO_DEBUG') == "on":
    # or gethostname() == 'i3live.sps.icecube.southpole.usap.gov':
    DEBUG = True
else:
    DEBUG = False

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rc.web.control',
    'rc.web.dbserv',
    'django_nose'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'rc.web.main.urls'

WSGI_APPLICATION = 'rc.web.main.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'NAME': 'lbnerc',
        'ENGINE': 'django.db.backends.mysql',
        # 'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'USER': 'lbne',
        'PASSWORD': '',
        'OPTIONS': {},
        'HOST': 'localhost',
        'PORT': ''
    }
}

# Templates

# TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__),
#                              'templates').replace('\\', '/'))

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(SITE_ROOT, 'static')

# Nose testing

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

NOSE_ARGS = [
    '--with-coverage',
    '-s',
    '-x',
    '--cover-html',
    '--cover-html-dir=/tmp/lbnerc-coverage',
    # '--cover-min-percentage=100',  # messes up test database deletion
    '--cover-inclusive',
    '--cover-package=rc']
