release: python manage.py migrate --noinput
web: gunicorn core.wsgi --timeout 120 --bind 0.0.0.0:$PORT
