#!/usr/bin/env python3
"""
Prueba de Saturación y Balanceo Homogéneo entre 2 Servidores GPU (Vía D)
Lanza 40 peticiones concurrentes para saturar el clúster y comprueba:
1. Reparto homogéneo de carga entre Servidor 1 (10.124.1.5) y Servidor 2 (10.124.2.5).
2. Tasa de éxito al 100% (cero errores).
3. Throughput agregado de las 4 GPUs en paralelo.
4. Registro de auditoría por servidor en PostgreSQL.
"""

import asyncio
import time
import json
import httpx
import subprocess

GATEWAY_URL = "http://localhost:8080/v1/chat/completions"
API_KEY = "sk-tier1-master-governance-key-2026"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

PROMPT = "Escribe una función recursiva para calcular el enésimo número de Fibonacci y analiza su complejidad temporal."

async def send_worker_request(client, req_id):
    payload = {
        "model": "light-model-coder",
        "messages": [{"role": "user", "content": f"Req {req_id}: {PROMPT}"}],
        "max_tokens": 80,
        "temperature": 0.2
    }
    t0 = time.perf_counter()
    try:
        r = await client.post(GATEWAY_URL, json=payload, headers=HEADERS, timeout=60.0)
        dt = time.perf_counter() - t0
        status = r.status_code
        backend = r.headers.get("x-litellm-model-id", "unknown")
        tokens = r.json().get("usage", {}).get("total_tokens", 0) if status == 200 else 0
        return {"id": req_id, "status": status, "time_s": dt, "backend": backend, "tokens": tokens}
    except Exception as e:
        return {"id": req_id, "status": 500, "error": str(e), "time_s": time.perf_counter() - t0, "tokens": 0}

async def main():
    print("=" * 80)
    print(" INICIANDO PRUEBA DE SATURACIÓN Y BALANCEO HOMOGÉNEO ENTRE 2 SERVIDORES GPU")
    print(" Target: http://localhost:8080/v1/chat/completions (LiteLLM Router)")
    print(" Concurrencia: 40 clientes simultáneos")
    print(" Servidores Físicos: Servidor 1 (2x L4) + Servidor 2 (2x L4) = 4 GPUs")
    print("=" * 80)

    # 1. Obtener conteo de peticiones previas en PostgreSQL por api_base
    check_sql_pre = """
    SELECT api_base, count(*) as count 
    FROM "LiteLLM_SpendLogs" 
    WHERE api_base IS NOT NULL 
    GROUP BY api_base;
    """
    cmd = ["kubectl", "exec", "deployment/litellm-db", "--", "psql", "-U", "litellm_admin", "-d", "litellm", "-t", "-c", check_sql_pre]
    pre_counts = subprocess.run(cmd, stdout=subprocess.PIPE, text=True).stdout.strip()
    print("\n[ESTADO PREVIO EN BASE DE DATOS]:")
    print(pre_counts if pre_counts else "  (Sin registros previos)")

    print("\n[+] Disparando ráfaga masiva de 40 peticiones simultáneas a las 4 GPUs...")
    t_start = time.perf_counter()
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=50)
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [send_worker_request(client, i) for i in range(1, 41)]
        results = await asyncio.gather(*tasks)
    total_duration = time.perf_counter() - t_start

    # 2. Análisis de resultados de la ráfaga
    successful = [r for r in results if r["status"] == 200]
    failed = [r for r in results if r["status"] != 200]
    total_tokens = sum(r["tokens"] for r in successful)

    print("\n" + "=" * 80)
    print(" RESULTADOS DE LA RÁFAGA DE SATURACIÓN")
    print("=" * 80)
    print(f"Peticiones Totales:       {len(results)}")
    print(f"Peticiones Exitosas:      {len(successful)} (100.0%)" if len(successful) == len(results) else f"Exitosas: {len(successful)}")
    print(f"Peticiones Fallidas:      {len(failed)}")
    print(f"Tokens Totales:           {total_tokens} tokens")
    print(f"Tiempo Total de la Carga: {total_duration:.2f} segundos")
    print(f"Throughput Agregado:      {total_tokens / total_duration:.2f} tokens/segundo")

    # 3. Comprobar en PostgreSQL el reparto exacto entre ambos servidores físicos
    print("\n" + "=" * 80)
    print(" DISTRIBUCIÓN HOMOGÉNEA DE CARGA EN LOS SERVIDORES FÍSICOS (AUDITORÍA SQL)")
    print("=" * 80)
    check_sql_post = """
    SELECT 
        CASE 
            WHEN api_base LIKE '%10.124.1.5%' THEN 'Servidor GPU 1 (Node xnck - 2x L4)'
            WHEN api_base LIKE '%10.124.2.5%' THEN 'Servidor GPU 2 (Node l0j7 - 2x L4)'
            WHEN api_base LIKE '%google%' THEN 'Desborde Cloud (Gemini)'
            ELSE api_base
        END AS servidor_fisico,
        count(*) as peticiones_atendidas,
        sum(total_tokens) as tokens_procesados
    FROM "LiteLLM_SpendLogs"
    WHERE "startTime" >= NOW() - INTERVAL '3 minutes'
    GROUP BY api_base
    ORDER BY peticiones_atendidas DESC;
    """
    cmd_post = ["kubectl", "exec", "deployment/litellm-db", "--", "psql", "-U", "litellm_admin", "-d", "litellm", "-c", check_sql_post]
    post_counts = subprocess.run(cmd_post, stdout=subprocess.PIPE, text=True).stdout.strip()
    print(post_counts)

if __name__ == "__main__":
    asyncio.run(main())
