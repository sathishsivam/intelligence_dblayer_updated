from .db import global_db
from langchain_core.documents import Document
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS


tables=global_db.get_usable_table_names()
docs=[]

for table in tables:
    try:
        schema=global_db.get_table_info([table])
        docs.append(Document(
                                page_content=schema,
                                metadata={"table_name":table}
                            )
                    )
    except Exception as e:
        print(f"Error Processing {table}: e")


embedding=OllamaEmbeddings(model="nomic-embed-text")

vectorstore=FAISS.from_documents(documents=docs,embedding=embedding)

retriever = vectorstore.as_retriever(
    search_kwargs={"k": 5}
)



# docs=retriever.invoke(input="what is the payload of authentication")
# print("Metadata embedding  with")

# tables=[]
# for i in docs:
#     tables.append(i.metadata['table_name'])

# for table in tables:
#     print(table)

# context="\n\n".join([doc.page_content for doc in docs])

# print(context)







