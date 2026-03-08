from sqlalchemy import Column, String, Text

from app.models.base import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    # Encrypted flag - when True, value is encrypted
    encrypted = Column(String, default="false")
