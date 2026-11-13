from app.db.session import engine
from app.db.base import Base

# Import all models so SQLAlchemy registers their tables
from app.models import (
    User,
    Package,
    AccessPoint,
    Payment,
    Subscription,
    WiFiSession,
)

Base.metadata.create_all(bind=engine)

print("Database tables created successfully.")
print("Tables:", list(Base.metadata.tables.keys()))
