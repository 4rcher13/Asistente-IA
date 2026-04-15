import os
from google import genai

def test_gemini():
    # Usando la clave proporcionada por el usuario directamente para la prueba
    api_key = "AIzaSyDQ7K29F1F70GxuS7suwuwXjuMV66b2pK4"
    client = genai.Client(api_key=api_key)
    
    try:
        print("Enlistando modelos disponibles...")
        for model in client.models.list():
            print(f"- {model.name} : {model.supported_methods}")
    except Exception as e:
        print(f"Error al enlistar modelos: {e}")

if __name__ == "__main__":
    test_gemini()
