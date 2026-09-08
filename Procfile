release: python manage.py migrate --noinput
web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn core.wsgi --timeout 120 --bind 0.0.0.0:$PORT