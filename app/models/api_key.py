from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.db.database import Base

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    wordpress_url = Column(String)
    wordpress_username = Column(String)
    wordpress_app_password = Column(String)
    is_active = Column(Boolean, default=True)