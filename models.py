from sqlalchemy import Column, Integer, String, DateTime, Text
from db_config import Base
import datetime

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    component_id = Column(String)
    status = Column(String, default="OPEN")
    severity = Column(String)

    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

    # RCA fields
    root_cause = Column(Text, nullable=True)
    fix_applied = Column(Text, nullable=True)
    prevention = Column(Text, nullable=True)  
