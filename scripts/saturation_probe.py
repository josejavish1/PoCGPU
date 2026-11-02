#!/usr/bin/env python3
"""
Experimento de Saturación al 100%, Contención y Cloud Bursting a Gemini (PoCGPU)
- Carga 1: 80% tráfico pesado a 'reasoning-model' (long tokens)
- Carga 2: 20% tráfico a 'light-model-fast'
- Carga 3 (Probe): Inyección de 'light-model-coder' en pico de congestión
Mide encolamiento, degradación de TTFT, conmutación automática a Gemini y ausencia de caídas.
"""

import asyncio
import time
import json
import httpx
import statistics

GATEWAY_URL = "http://localhost:8080/v1/chat/completions"
API_KEY = "sk-tier1-master-governance-key-2026"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

DEEP_PROMPT = (
    "Demuestra rigurosamente y paso a paso por que la raiz cuadrada de dos es un numero irracional, "
    "incluyendo la formulacion matematica clasica de reduccion al absurdo, el analisis de paridad "
    "de los enteros coprimos y las implicaciones algebraicas en el cuerpo de los numeros racionales. "
    "Desarrolla una explicacion muy detallada y exhaustiva."
)

LIGHT_PROMPT = "Resume en 20 palabras por que Kubernetes utiliza cgroups para aislar memoria."
CODER_PROMPT = "Escribe una funcion en Python para invertir un arbol binario de busqueda con recursion."

async def send_request(client, model, prompt, max_tokens, request_label):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0.0
    }
    t_start = time.perf_counter()
    first_token_t = None
    tokens = 0
    status = 0
    error = None
    served_model = model

    try:
        async with client.stream("POST", GATEWAY_URL, json=payload, headers=HEADERS, timeout=120.0) as resp:
            status = resp.status_code
            if status != 200:
                body = await resp.aread()
                return {
                    "label": request_label,
                    "model": model,
                    "served_by": "error",
                    "status": status,
                    "error": body.decode(),
                    "ttft_ms": 0,
                    "total_t_s": time.perf_counter() - t_start,
                    "tokens": 0,
                    "tpot_ms": 0
                }

            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        if "model" in chunk and chunk["model"]:
                            served_model = chunk["model"]
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            tokens += 1
                            if first_token_t is None:
                                first_token_t = time.perf_counter()
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        error = str(e)

    t_end = time.perf_counter()
    ttft = (first_token_t - t_start) * 1000 if first_token_t else 0.0
    total_t = t_end - t_start

    return {
        "label": request_label,
        "model": model,
        "served_by": served_model,
        "status": status,
        "error": error,
        "ttft_ms": ttft,
        "total_t_s": total_t,
        "tokens": tokens,
        "tpot_ms": ((total_t - (ttft/1000)) / (tokens - 1) * 1000) if (tokens > 1 and first_token_t) else 0.0
    }

async def run_probe():
    print("=" * 75)
    print("INICIANDO EXPERIMENTO DE CONTENCIÓN Y SATURACIÓN AL 100%")
    print("Escenario:")
    print("  - Fase 1: Lanzar 24 clientes concurrentes en 'reasoning-model' (~80% tráfico)")
    print("  - Fase 2: Lanzar 12 clientes concurrentes en 'light-model-fast' (~20% tráfico)")
    print("  - Fase 3: Inyectar 'light-model-coder' en pleno pico de saturación")
    print("  - Resiliencia: Timeout local de 10-15s con desvío a Gemini si la GPU colapsa")
    print("=" * 75)

    limits = httpx.Limits(max_connections=60, max_keepalive_connections=40)
    async with httpx.AsyncClient(limits=limits) as client:
        # 1. Medir baseline en reposo del 3er modelo (light-model-coder)
        print("\n[PASO 1] Midiendo línea base de 'light-model-coder' en reposo (sin tráfico)...")
        baseline_coder = await send_request(client, "light-model-coder", CODER_PROMPT, 100, "baseline-coder")
        print(f"  -> Baseline TTFT: {baseline_coder['ttft_ms']:.2f} ms | Servido por: {baseline_coder['served_by']} | Status: {baseline_coder['status']}")

        # 2. Lanzar la sobrecarga masiva para saturar los núcleos y la memoria
        print("\n[PASO 2] Lanzando saturación masiva (36 clientes simultáneos)...")
        tasks = []

        # Grupo 1 (80%): 24 clientes pesados de razonamiento
        for i in range(1, 25):
            tasks.append(send_request(client, "reasoning-model", DEEP_PROMPT, 600, f"reasoning-{i}"))

        # Grupo 2 (20%): 12 clientes ligeros
        for j in range(1, 13):
            tasks.append(send_request(client, "light-model-fast", LIGHT_PROMPT, 80, f"light-{j}"))

        # Iniciar las 36 peticiones en paralelo
        gathered_heavy_tasks = asyncio.gather(*tasks)

        # Esperar 2.5 segundos a que la GPU entre en saturación activa
        print("  -> Esperando a que el lote de cómputo y la memoria KV entren en saturación...")
        await asyncio.sleep(2.5)

        # 3. Inyectar la petición del TERCER MODELO en plena saturación
        print("\n[PASO 3] ¡INYECTANDO PETICIÓN DEL TERCER MODELO ('light-model-coder') EN PLENA SATURACIÓN!")
        saturated_coder = await send_request(client, "light-model-coder", CODER_PROMPT, 100, "saturated-coder-probe")
        print(f"  -> Saturated TTFT: {saturated_coder['ttft_ms']:.2f} ms | Servido por: {saturated_coder['served_by']} | Total Time: {saturated_coder['total_t_s']:.2f} s | Status: {saturated_coder['status']}")

        # Esperar a que todo el lote pesado finalice
        print("\n[PASO 4] Esperando a que el resto de las 36 peticiones pesadas finalicen...")
        heavy_results = await gathered_heavy_tasks

    # Análisis de resultados
    all_results = heavy_results + [saturated_coder]
    successful = [r for r in all_results if r["status"] == 200]
    failed = [r for r in all_results if r["status"] != 200 or r["error"] is not None]

    local_served = [r for r in successful if "gemini" not in r["served_by"].lower()]
    gemini_served = [r for r in successful if "gemini" in r["served_by"].lower()]

    print("\n" + "=" * 75)
    print("ANÁLISIS COMPARATIVO DE DEGRADACIÓN Y CONTENCIÓN (Resultados Empíricos)")
    print("=" * 75)
    print(f"Peticiones Totales Inyectadas: {len(all_results)}")
    print(f"Peticiones Exitosas:           {len(successful)} ({len(successful)/len(all_results)*100:.1f}%)")
    print(f"Peticiones Fallidas / OOM:     {len(failed)}")
    print(f"  - Atendidas por GPU Local:   {len(local_served)}")
    print(f"  - Desviadas a Gemini Cloud:  {len(gemini_served)}")

    print("\n[IMPACTO EN EL TERCER MODELO ('light-model-coder')]:")
    print(f"  - TTFT en Reposo (Baseline):      {baseline_coder['ttft_ms']:.2f} ms")
    print(f"  - TTFT en Plena Saturación:       {saturated_coder['ttft_ms']:.2f} ms")
    ratio = (saturated_coder['ttft_ms'] / baseline_coder['ttft_ms']) if baseline_coder['ttft_ms'] > 0 else 1.0
    print(f"  - Factor de Degradación de TTFT:  {ratio:.2f}x")
    print(f"  - Servido en Saturación por:      {saturated_coder['served_by']}")
    print(f"  - ¿Hubo caída o error OOM?:       {'NO (Atendido con éxito)' if saturated_coder['status'] == 200 else 'SÍ'}")

    print("\n[RESUMEN DE RENDIMIENTO DE LA CARGA DE FONDO (36 Peticiones Concurrentes)]:")
    heavy_ttft = [r["ttft_ms"] for r in heavy_results if r["status"] == 200 and r["ttft_ms"] > 0]
    total_tokens = sum(r["tokens"] for r in all_results if r["status"] == 200)
    if heavy_ttft:
        print(f"  - P50 TTFT Carga: {statistics.median(heavy_ttft):.2f} ms")
        print(f"  - P99 TTFT Carga: {max(heavy_ttft):.2f} ms")
    print(f"  - Tokens Totales Generados en la Prueba: {total_tokens}")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(run_probe())
