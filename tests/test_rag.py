import os
import sys
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

# Añadir el directorio raíz al path para poder importar src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def diagnostic_sync():
    print("=== DIAGNOSTICO DE RAG (MODO DIRECTO) ===")
    
    db_path = "data/chroma_db"
    if not os.path.exists(db_path):
        print(f"Error: No existe el directorio {db_path}")
        return

    print("1. Cargando modelo de embeddings (SBERT)...")
    try:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        print("OK: Modelo cargado correctamente.")
    except Exception as e:
        print(f"ERROR: Error cargando modelo: {e}")
        return

    print("2. Conectando a ChromaDB...")
    try:
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_or_create_collection(
            name="icaro_memories",
            embedding_function=ef
        )
        count = collection.count()
        print(f"OK: Conectado. Total de memorias: {count}")
    except Exception as e:
        print(f"ERROR: Error conectando a DB: {e}")
        return

    if count > 0:
        print("\n3. Ultimas 5 memorias:")
        results = collection.get(limit=5)
        for i in range(len(results['ids'])):
            role = results['metadatas'][i].get('role', 'unknown')
            text = results['documents'][i][:100]
            print(f"  - {role}: {text}")

        print("\n4. Probando recuperacion semantica:")
        # Probamos con "Jesus" que es lo que el usuario menciono
        test_queries = ["Jesus", "Icaro", "como me llamo"]
        for q in test_queries:
            print(f"\nBusqueda: '{q}'")
            res = collection.query(query_texts=[q], n_results=2)
            if res['documents'] and res['documents'][0]:
                for doc in res['documents'][0]:
                    print(f"  -> Encontrado: {doc[:80]}...")
            else:
                print("  -> Nada encontrado.")
    else:
        print("\nLa base de datos esta vacia.")

if __name__ == "__main__":
    diagnostic_sync()
