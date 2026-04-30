from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from db_config import Base
import datetime

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)

    component_id = Column(String, index=True, nullable=False)
    severity = Column(String, index=True, nullable=False)

    status = Column(String, default="OPEN", index=True)

    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

    mttr_seconds = Column(Float, nullable=True)

    # RCA fields
    root_cause = Column(Text, nullable=True)
    fix_applied = Column(Text, nullable=True)
    prevention = Column(Text, nullable=True)
