#!/usr/bin/env python3
import sys
import json
import requests

API_URL = "http://127.0.0.1:8080/v1/chat/completions"
API_KEY = "sk-tier1-master-governance-key-2026"
MODEL = "light-model-fast"

def chat_stream(prompt, history):
    history.append({"role": "user", "content": prompt})
    payload = {
        "model": MODEL,
        "messages": history,
        "max_tokens": 512,
        "temperature": 0.3,
        "stream": True
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
    except Exception as e:
        print(f"\n[Error de conexion]: {e}")
        return ""

    assistant_reply = ""
    for line in response.iter_lines():
        if line:
            decoded = line.decode("utf-8").strip()
            if decoded.startswith("data: ") and decoded != "data: [DONE]":
                try:
                    data = json.loads(decoded[6:])
                    delta = data["choices"][0]["delta"].get("content", "")
                    assistant_reply += delta
                    sys.stdout.write(delta)
                    sys.stdout.flush()
                except Exception:
                    pass
    print()
    history.append({"role": "assistant", "content": assistant_reply})
    return assistant_reply

def main():
    print("==================================================")
    print(f"Chat interactivo con Mistral-7B vía LiteLLM ({MODEL})")
    print("Escribe tu pregunta o 'salir' para terminar.")
    print("==================================================\n")

    history = [
        {"role": "system", "content": "Eres un asistente técnico conciso, experto en infraestructura cloud y sistemas."}
    ]

    while True:
        try:
            user_input = input("\nTú (Escribe tu pregunta) > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("salir", "exit", "quit"):
                print("Sesion finalizada.")
                break
            sys.stdout.write("Mistral > ")
            sys.stdout.flush()
            chat_stream(user_input, history)
        except (KeyboardInterrupt, EOFError):
            print("\nSesion finalizada.")
            break

if __name__ == "__main__":
    main()
