
Framework: FastAPI (Python)
ORM: SQLAlchemy
Database: MySQL
Migrations: Alembic (Python-based)
Async Processing: Celery + Redis
Storage: Local (with abstraction for future AWS S3)
Payments: Razorpay
PDF Generation: WeasyPrint or ReportLab
Authentication: JWT (access + refresh tokens)

All services are running under supervisor app. So restart is needed.

Once restarted:
go to the project folder
    source venv/bin/activate    
    sudo supervisorctl restart all

    Check all the services are running
    #sudo supervisorctl status
    vastu_api       RUNNING
    vastu_celery    RUNNING



An Admin to be created with Flutter as front end and python, mysql for a SaaS Vastu App
The server configuration for python is such like that Supervisor 
fastapi
uvicorn
gunicorn
sqlalchemy
alembic
celery

psycopg2-binary

Modules:

Subscription Packages. 
    No. Reports Can be taken.
    Limit of Subscription
Rooms and Object Management
Direction Management 16/32
Criticality of Placing Rooms and Objects on each direction,Remedies,Colors,Therapy.


I have made all the databases, and now need to create api.

How do I provide the existing code so that we can start where it stopped?

pip install passlib bcrypt python-jose python-multipart
alembic revision --autogenerate -m "add_role_column_to_users"
alembic upgrade head
