from .db import global_db
from langchain_core.documents import Document
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS


tables=global_db.get_usable_table_names()
docs=[]

for table in tables:
    try:
        schema=global_db.get_table_info([table])
        content = f"""
                        TABLE_NAME: {table}
                        SCHEMA:{schema}
                   """
        docs.append(Document(
                                page_content=content,
                                metadata={"table_name":table,"schema":schema}
                            )
                    )
    except Exception as e:
        print(f"Error Processing {table}: e")

# --------------------------------------------------
# EMBEDDINGS + VECTOR STORE
# --------------------------------------------------

embedding=OllamaEmbeddings(model="nomic-embed-text")

vectorstore=FAISS.from_documents(documents=docs,embedding=embedding)

retriever = vectorstore.as_retriever(
    search_kwargs={"k": 5}
)










