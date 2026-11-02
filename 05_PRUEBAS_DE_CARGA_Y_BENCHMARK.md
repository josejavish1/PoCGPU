# 05. Protocolo de Pruebas de Carga y Benchmarking Empírico

## 1. Fundamentos: Qué se Mide en Inferencia LLM (y qué no)
En servicios web tradicionales se mide transacciones por segundo (RPS) y latencia HTTP. En inferencia de modelos generativos, esas métricas son insuficientes. Es obligatorio medir:
1. **TTFT (Time to First Token) / Prefill Latency:** Tiempo desde que el cliente envía el prompt hasta que recibe el primer token. Mide la velocidad de absorción del contexto.
2. **TPOT (Time Per Output Token) / Inter-Token Latency (ITL):** Tiempo entre cada token emitido de forma consecutiva. Determina si la respuesta es fluida en streaming (objetivo: $< 50\text{ ms/token}$).
3. **Throughput de Tokens Agregado:** Número total de tokens (entrada + salida) procesados por segundo en ambas GPUs de forma simultánea.
4. **Factor de Uso del KV Cache (`gpu_cache_usage_factor`):** Debe crecer dinámicamente durante ráfagas de razonamiento largo hasta el 90-95% y descender inmediatamente al completarse la petición sin reinicios de contenedor ni fugas de memoria.

---

## 2. Preparación del Entorno de Prueba

Instale las dependencias del script de prueba en su entorno de ejecución:
```bash
pip install httpx
```

Verifique la accesibilidad del Gateway:
```bash
curl -I http://localhost:4000/health/readiness
```

---

## 3. Monitorización de VRAM y Métricas en Tiempo Real

Antes de iniciar el benchmark, abra dos terminales auxiliares para auditar el comportamiento del hardware y del motor:

**Terminal 1: Telemetría de GPU en el nodo:**
```bash
kubectl exec -it deployment/vllm-inference-engine -c vllm-server -- nvidia-smi dmon -s um -d 1
```
*Muestra en tiempo real la utilización de Streaming Multiprocessors (`sm`), uso de memoria (`mclk`) y consumo de VRAM por tarjeta.*

**Terminal 2: Métricas del motor vLLM:**
```bash
kubectl exec -it deployment/vllm-inference-engine -c vllm-server -- curl -s http://localhost:8000/metrics | grep -E "vllm:gpu_cache_usage_factor|vllm:num_requests"
```

---

## 4. Ejecución del Benchmark de Concurrencia Mixta

Ejecute el script automatizado ubicado en `scripts/benchmark.py`:

```bash
python3 /home/jsanchhi/PoCGPU/scripts/benchmark.py \
  --url http://localhost:4000 \
  --key sk-tier1-master-governance-key-2026 \
  --concurrency 12 \
  --rounds 5
```

### Qué simula este test:
- Genera **12 clientes concurrentes** en paralelo.
- El 33% del tráfico envía prompts complejos de razonamiento (solicitando cientos de tokens de deducción formal).
- El 66% del tráfico envía prompts cortos a los modelos ligeros concurrentes.
- Evalúa el comportamiento del planificador a nivel de iteración (*Iteration-level scheduler*): los modelos ligeros no deben quedar bloqueados por el modelo de razonamiento.

---

## 5. Criterios de Aceptación Fáctica (Tier-1 Quality Gate)

Para considerar la infraestructura certificada para producción, los resultados deben cumplir:

| Métrica | Umbral Tier-1 Aceptable | Umbral Crítico (Fallo) |
| :--- | :--- | :--- |
| **Tasa de Errores (HTTP 5xx / OOM)** | **0.0%** | $> 0.1\%$ |
| **P50 TTFT (Modelos Ligeros)** | $< 350\text{ ms}$ | $> 1000\text{ ms}$ |
| **P99 TTFT (Razonamiento Profundo)** | $< 1800\text{ ms}$ | $> 4000\text{ ms}$ |
| **Media TPOT (Streaming)** | $< 45\text{ ms/token}$ | $> 100\text{ ms/token}$ |
| **Factor de Uso KV Cache Pico** | $85\% - 95\%$ | $100\%$ (con expulsión de requests) |
| **Reclamación de VRAM post-test** | VRAM retorna al estado base de pesos en $< 2\text{ s}$ | Fuga de VRAM (OOM en la siguiente ronda) |
