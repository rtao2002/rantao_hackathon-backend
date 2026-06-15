import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PWD = os.getenv("MYSQL_PWD")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

MYSQL_SSL_CA = os.getenv("MYSQL_SSL_CA")
MYSQL_SSL_CERT = os.getenv("MYSQL_SSL_CERT")
MYSQL_SSL_KEY = os.getenv("MYSQL_SSL_KEY")

if MYSQL_HOST and MYSQL_HOST.startswith("/cloudsql/"):
    DATABASE_URL = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PWD}"
        f"@/{MYSQL_DATABASE}"
        f"?unix_socket={MYSQL_HOST}"
    )
else:
    DATABASE_URL = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PWD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    )

connect_args = {}

if MYSQL_SSL_CA and MYSQL_SSL_CERT and MYSQL_SSL_KEY:
    connect_args["ssl"] = {
        "ca": MYSQL_SSL_CA,
        "cert": MYSQL_SSL_CERT,
        "key": MYSQL_SSL_KEY,
    }

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()