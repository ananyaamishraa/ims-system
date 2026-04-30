from db_config import engine, Base
from models import Incident

Base.metadata.create_all(bind=engine) 
