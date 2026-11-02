#!/usr/bin/env python3
"""
Ejemplo de software automatizado: Clasificador y Analizador de Incidencias de IT.
Consume el motor local Mistral-7B vía LiteLLM y devuelve JSON estructurado.
"""
import sys
import json
import requests

API_URL = "http://127.0.0.1:8080/v1/chat/completions"
API_KEY = "sk-tier1-master-governance-key-2026"
MODEL = "light-model-fast"

def analizar_incidencia(texto_incidencia: str) -> dict:
    prompt_sistema = """Eres un motor de triaje de incidencias de infraestructura IT.
Analiza la descripción del problema y responde ÚNICAMENTE con un objeto JSON válido con este formato:
{
  "categoria": "STORAGE | NETWORK | COMPUTE | DATABASE | SECURITY",
  "severidad": "P1-CRITICA | P2-ALTA | P3-MEDIA | P4-BAJA",
  "resumen": "Breve resumen en 10 palabras",
  "accion_recomendada": "Paso técnico inmediato a ejecutar"
}
No añadas texto introductorio ni explicaciones fuera del bloque JSON."""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Incidencia a evaluar: {texto_incidencia}"}
        ],
        "temperature": 0.1,
        "max_tokens": 600
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        contenido = response.json()["choices"][0]["message"]["content"].strip()
        # Limpieza básica si el modelo envuelve en markdown ```json ... ```
        if contenido.startswith("```"):
            contenido = contenido.split("\n", 1)[1].rsplit("\n", 1)[0]
            if contenido.startswith("json"):
                contenido = contenido[4:].strip()
        return json.loads(contenido)
    except Exception as e:
        return {"error": f"Fallo al procesar incidencia: {e}"}

def main():
    if len(sys.argv) > 1:
        texto = " ".join(sys.argv[1:])
    else:
        texto = "El datastore NFS de producción se encuentra al 98% de capacidad y las VMs están bloqueadas por I/O."

    print(f"[+] Enviando incidencia al modelo local ({MODEL})...\n")
    print(f"Texto: \"{texto}\"\n")
    resultado = analizar_incidencia(texto)
    print("=== RESULTADO ESTRUCTURADO (JSON) ===")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
