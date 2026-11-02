#!/usr/bin/env python3
"""
Benchmark de Carga y Concurrencia Dinámica para Inferencia LLM (PoCGPU)
Simula tráfico mixto: Modelo de Razonamiento Profundo + Modelos Ligeros Concurrentes.
Mide TTFT, TPOT, Throughput y tasa de errores.
"""

import asyncio
import time
import json
import statistics
import argparse
from typing import List, Dict, Any
import httpx

async def send_inference_request(
    client: httpx.AsyncClient,
    url: str,
    headers: Dict[str, str],
    model: str,
    prompt: str,
    max_tokens: int,
    request_id: int
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0.1
    }

    start_time = time.perf_counter()
    first_token_time = None
    token_count = 0
    status_code = 0
    error = None

    try:
        async with client.stream("POST", url, json=payload, headers=headers, timeout=180.0) as response:
            status_code = response.status_code
            if status_code != 200:
                body = await response.aread()
                return {
                    "request_id": request_id,
                    "model": model,
                    "status": "error",
                    "status_code": status_code,
                    "error": body.decode("utf-8", errors="ignore"),
                    "total_time": time.perf_counter() - start_time
                }

            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            token_count += 1
                            if first_token_time is None:
                                first_token_time = time.perf_counter()
                    except json.JSONDecodeError:
                        continue

    except Exception as exc:
        error = str(exc)

    end_time = time.perf_counter()
    total_time = end_time - start_time
    ttft = (first_token_time - start_time) if first_token_time else 0.0
    tpot = ((end_time - first_token_time) / (token_count - 1)) if (first_token_time and token_count > 1) else 0.0

    return {
        "request_id": request_id,
        "model": model,
        "status": "success" if error is None and status_code == 200 else "error",
        "status_code": status_code,
        "error": error,
        "total_time": total_time,
        "ttft": ttft,
        "tpot": tpot,
        "tokens": token_count,
        "tokens_per_sec": (token_count / total_time) if total_time > 0 else 0.0
    }

async def run_benchmark(gateway_url: str, api_key: str, concurrency: int, duration_rounds: int):
    endpoint = f"{gateway_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    print("=" * 70)
    print("INICIANDO BENCHMARK DE ESTRÉS CONCURRENTE TIER-1 (PoCGPU)")
    print(f"Target: {endpoint}")
    print(f"Concurrencia: {concurrency} clientes simultáneos")
    print(f"Rondas: {duration_rounds}")
    print("=" * 70)

    # Prompt de razonamiento largo para forzar asignación masiva de KV Cache
    deep_reasoning_prompt = (
        "Analiza formalmente el problema de consenso en sistemas distribuidos bajo el modelo FLP "
        "y formula una demostración de por qué es imposible garantizar consenso determinista en redes "
        "asíncronas con fallos por caída. Proporciona una explicación detallada paso a paso."
    )

    # Prompt corto para modelos ligeros
    light_prompt = "Resume en 15 palabras el concepto de idempotencia en APIs REST."

    results: List[Dict[str, Any]] = []

    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(limits=limits) as client:
        req_id = 0
        for round_idx in range(1, duration_rounds + 1):
            tasks = []
            for i in range(concurrency):
                req_id += 1
                # Alternar: 1 petición de razonamiento pesado por cada 2 ligeras
                if i % 3 == 0:
                    tasks.append(
                        send_inference_request(
                            client, endpoint, headers,
                            model="reasoning-model",
                            prompt=deep_reasoning_prompt,
                            max_tokens=512,
                            request_id=req_id
                        )
                    )
                else:
                    tasks.append(
                        send_inference_request(
                            client, endpoint, headers,
                            model="light-model-fast",
                            prompt=light_prompt,
                            max_tokens=60,
                            request_id=req_id
                        )
                    )

            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            print(f"Ronda {round_idx}/{duration_rounds} completada. {len(batch_results)} peticiones procesadas.")

    # Análisis Estadístico
    success_results = [r for r in results if r["status"] == "success"]
    failed_results = [r for r in results if r["status"] == "error"]

    print("\n" + "=" * 70)
    print("RESULTADOS EMPÍRICOS DEL BENCHMARK")
    print("=" * 70)
    print(f"Total Peticiones: {len(results)}")
    print(f"Exitosas: {len(success_results)} ({len(success_results)/len(results)*100:.1f}%)")
    print(f"Fallidas: {len(failed_results)}")

    if not success_results:
        print("ERROR: Ninguna petición tuvo éxito. Verifique los logs del cluster.")
        return

    ttft_list = [r["ttft"] * 1000 for r in success_results] # ms
    tpot_list = [r["tpot"] * 1000 for r in success_results if r["tpot"] > 0] # ms
    total_tokens = sum(r["tokens"] for r in success_results)
    total_duration = max(r["total_time"] for r in success_results)

    print("\n[MÉTRICAS DE TIEMPO A PRIMER TOKEN (TTFT) - Prefill]:")
    print(f"  P50 TTFT: {statistics.median(ttft_list):.2f} ms")
    if len(ttft_list) >= 4:
        print(f"  P90 TTFT: {statistics.quantiles(ttft_list, n=10)[8]:.2f} ms")
        print(f"  P99 TTFT: {statistics.quantiles(ttft_list, n=100)[98]:.2f} ms")

    print("\n[MÉTRICAS DE TIEMPO POR TOKEN (TPOT) - Decode Fluidity]:")
    if tpot_list:
        print(f"  Media TPOT: {statistics.mean(tpot_list):.2f} ms/token")
        print(f"  P50 TPOT:   {statistics.median(tpot_list):.2f} ms/token")

    print("\n[RENDIMIENTO GLOBAL (Throughput)]:")
    print(f"  Tokens Totales Generados: {total_tokens}")
    print(f"  Rendimiento Agregado:     {total_tokens / total_duration:.2f} tokens/segundo")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM Load Benchmark")
    parser.add_argument("--url", default="http://localhost:8080", help="URL del AI Gateway")
    parser.add_argument("--key", default="sk-tier1-master-governance-key-2026", help="Master API Key")
    parser.add_argument("--concurrency", type=int, default=8, help="Número de conexiones concurrentes")
    parser.add_argument("--rounds", type=int, default=3, help="Rondas de prueba")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.url, args.key, args.concurrency, args.rounds))
