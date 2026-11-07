#!/usr/bin/env python3
"""
Simulador de IDE Copilot (Vía B)
Simula el comportamiento de una extensión de VS Code (Continue.dev) enviando
un fragmento de código incompleto a la GPU local mediante la clave de desarrollador.
"""
import sys
import json
import requests

API_URL = "http://127.0.0.1:8080/v1/chat/completions"
DEV_API_KEY = "sk-9od6eun2IyOt7Qj8NZFeVQ"
MODEL = "light-model-coder"

def simulate_ide_autocomplete(context_code: str, instruction: str):
    print("=" * 70)
    print(" [VS CODE SIMULATOR] Enviando contexto de archivo al modelo...")
    print("=" * 70)
    print(f"ARCHIVO ACTUAL:\n{context_code.strip()}\n")
    print(f"ORDEN DEL PROGRAMADOR (Ctrl + I):\n\"{instruction}\"\n")
    print("-" * 70)
    print(" [GPU LOCAL - Mistral 7B Coding Agent] Generando código...")
    print("-" * 70)

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres el motor de código de un IDE. Completa o refactoriza el código "
                    "según la instrucción del usuario. Devuelve ÚNICAMENTE el bloque de código resultante."
                )
            },
            {
                "role": "user",
                "content": f"Contexto del archivo:\n```python\n{context_code}\n```\n\nInstrucción: {instruction}"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 300,
        "stream": True
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEV_API_KEY}"
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        assistant_code = ""
        for line in response.iter_lines():
            if line:
                decoded = line.decode("utf-8").strip()
                if decoded.startswith("data: ") and decoded != "data: [DONE]":
                    try:
                        data = json.loads(decoded[6:])
                        delta = data["choices"][0]["delta"].get("content", "")
                        assistant_code += delta
                        sys.stdout.write(delta)
                        sys.stdout.flush()
                    except Exception:
                        pass
        print("\n\n" + "=" * 70)
        print(" [COMPLETADO] Código generado y auditado bajo el usuario 'developer-vscode'.")
        print("=" * 70)
    except Exception as e:
        print(f"\n[ERROR]: No se pudo conectar al Gateway: {e}")

def main():
    codigo_ejemplo = """
class DatabaseConnector:
    def __init__(self, host, port, db_name):
        self.host = host
        self.port = port
        self.db_name = db_name
"""
    instruccion_ejemplo = "Añade un método connect() con reintentos exponenciales y manejo de excepciones."

    simulate_ide_autocomplete(codigo_ejemplo, instruccion_ejemplo)

if __name__ == "__main__":
    main()
