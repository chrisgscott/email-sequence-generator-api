from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, index=True, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    wordpress_url = Column(String, nullable=True)
    wordpress_username = Column(String, nullable=True)
    wordpress_password = Column(String, nullable=True)

    user = relationship("User", back_populates="api_keys")