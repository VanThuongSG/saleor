```powershell
python -m venv venv
venv/Scripts/activate
python -m pip install wheel
python -m pip install pydotplus
python -m pip install -r requirements_dev.txt

$env:ENABLE_DJANGO_EXTENSIONS = 'True'
$env:ENABLE_DEBUG_TOOLBAR = 'False'
$env:SECRET_KEY = 'MYS3CR3TK4Y'

python manage.py migrate
python manage.py collectstatic --no-input
python manage.py populatedb --createsuperuser
python manage.py runserver 0.0.0.0:8000

python manage.py makemigrations

pytest --reuse-db saleor/graphql/post/tests
python manage.py get_graphql_schema > saleor/graphql/schema.graphql
```

CREATE EXTENSION pgcrypto;
