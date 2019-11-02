from app import mssqlix
from app.models import *

if __name__ == "__main__":
    MSSQLixModel.init_db()
    mssqlix.run()
    MSSQLixModel.close_db()
