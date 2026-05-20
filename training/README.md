# Guía de Entrenamiento para Ícaro icarus-v1

Esta carpeta contiene las herramientas para realizar el fine-tuning de Ícaro y convertirlo en un experto en programación y ciberseguridad.

## Estructura
- `generate_dataset.py`: Script para crear los datos de entrenamiento usando Gemini.
- `train_config.json`: (Próximamente) Configuración de hiperparámetros.
- `dataset.jsonl`: Archivo generado que se subirá a la nube.

## Pasos para el Fine-Tuning (En la Nube)

### 1. Generar los datos locales
Ejecuta el script desde la raíz del proyecto para generar tu primer dataset basado en tu propio código y logs:
```bash
python training/generate_dataset.py
```

### 2. Preparar el entorno en Google Colab
Recomendamos usar **Unsloth** para un entrenamiento ultra rápido y eficiente en memoria.
- Abre este Notebook: [Unsloth Llama-3 Beginner Notebook](https://colab.research.google.com/github/unslothai/unsloth/blob/main/notebooks/Llama_3_8B_(Alpha).ipynb)
- Sube tu archivo `dataset.jsonl`.

### 3. Configuración de Entrenamiento
En el notebook, asegúrate de configurar:
- **Base Model:** `unsloth/llama-3-8b-bnb-4bit` o `unsloth/mistral-7b-v0.3-bnb-4bit`.
- **Dataset Format:** ChatML o Instruction/Input/Output (según lo generado).
- **Epochs:** 3 a 5 es suficiente para empezar.
- **Learning Rate:** 2e-4.

### 4. Exportación a Ollama
Una vez terminado el entrenamiento:
1. Exporta el modelo a formato **GGUF** (opción disponible en el notebook de Unsloth).
2. Descarga el archivo `.gguf`.
3. Crea un archivo `Modelfile` en tu PC:
   ```dockerfile
   FROM ./tu-modelo-entrenado.gguf
   PARAMETER temperature 0.3
   SYSTEM """
   Eres Ícaro, experto en programación y ciberseguridad. 
   Respondes siempre en JSON para los comandos y con un tono de profesor amigable.
   """
   ```
4. Crea el modelo en Ollama:
   ```bash
   ollama create icaro-v1 -f Modelfile
   ```

### 5. Actualización de Ícaro
Cambia el modelo en tu archivo `.env`:
```env
MODELO_LOCAL=icaro-v1
```

## Tips de Personalidad (Fine-Tuning)
Para que Ícaro actúe como un experto profesor, el dataset debe incluir explicaciones de "por qué" se ejecuta un comando. El script `generate_dataset.py` ya está configurado para pedir esto a Gemini.
