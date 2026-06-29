from langchain_community.utilities import SQLDatabase

DATABASE_URL = (
    "oracle+oracledb://APZBANKING_CUB:"
    "APZBANKING_CUB!@192.168.1.52:1521/"
    "?service_name=orcl19c"
)
DATABASE_URL1 = (
    "oracle+oracledb://CUBAPZBANKING:"
    "CUBAPZBANKING!@192.168.1.52:1521/"
    "?service_name=orcl19c"
)
# GLOBAL DB
global_db = SQLDatabase.from_uri(
    DATABASE_URL,
)
