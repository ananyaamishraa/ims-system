from db_config import engine, Base
from models import Incident

# Creates all tables safely
def init():
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")

if __name__ == "__main__":
    init()
