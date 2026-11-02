# 06. Guía Práctica de la PoC: Saturación, Auditoría de Tokens y Conexión de Clientes

## 1. El Objetivo de la PoC
Demostrar empíricamente en el clúster:
1. **Generación de API Keys Gobernadas:** Crear claves independientes para cada servicio o VM (ej. `vm-gemini-client`, `app-backend`).
2. **Auditoría de Consumo por Clave:** Saber con precisión de token cuántos tokens de entrada y salida ha consumido cada cliente y en qué modelo (`reasoning-model` vs `light-model-fast`).
3. **Observabilidad de Saturación en Vivo:** Medir el porcentaje de VRAM (`gpu_cache_usage_factor`) y la cola de espera (`num_requests_waiting`).
4. **Resiliencia ante Sobrecarga:** Estresar el clúster con 50 peticiones simultáneas de razonamiento pesado y comprobar que el sistema degrada la latencia con elegancia sin caer en `CUDA OutOfMemory`.

---

## 2. Paso 1: Generar una API Key para una VM Externa

Ejecute una llamada a la API de administración del Gateway (LiteLLM) para crear una clave restringida:

```bash
# Crear una API Key para una VM Linux con límite de 50.000 tokens
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer sk-tier1-master-governance-key-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "vm-linux-gemini-01",
    "team_id": "infra-ops",
    "max_budget": 5.0,
    "models": ["reasoning-model", "light-model-fast"],
    "metadata": {"environment": "testing", "owner": "sysadmin"}
  }'
```

**Respuesta devuelta por el Gateway:**
```json
{
  "key": "sk-litellm-78ab34cd90ef...",
  "user_id": "vm-linux-gemini-01",
  "max_budget": 5.0,
  "expires": null
}
```
*Guarde la clave generada (`sk-litellm-...`) para configurarla en la VM cliente.*

---

## 3. Paso 2: Conectar la VM Linux y Consumir los Modelos

En la VM Linux remota (o en cualquier servidor que tenga acceso IP al Gateway):

### Opción A: Consumo vía cURL estándar
```bash
export AI_GATEWAY_URL="http://<IP_DEL_GATEWAY>:80/v1/chat/completions"
export AI_API_KEY="sk-litellm-78ab34cd90ef..."

# 1. Petición al Modelo de Razonamiento Profundo
curl -X POST $AI_GATEWAY_URL \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AI_API_KEY" \
  -d '{
    "model": "reasoning-model",
    "messages": [{"role": "user", "content": "Explica la diferencia entre TCP BBR y CUBIC."}],
    "max_tokens": 300
  }'

# 2. Petición al Modelo Ligero
curl -X POST $AI_GATEWAY_URL \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AI_API_KEY" \
  -d '{
    "model": "light-model-fast",
    "messages": [{"role": "user", "content": "Resume este texto: Alta disponibilidad en bases de datos relacionales."}],
    "max_tokens": 50
  }'
```

### Opción B: Consumo con SDK de OpenAI / Gemini CLI
Cualquier cliente compatible con OpenAI funciona sin modificar código apuntando a la URL del Gateway:
```bash
export OPENAI_API_BASE="http://<IP_DEL_GATEWAY>:80/v1"
export OPENAI_API_KEY="sk-litellm-78ab34cd90ef..."
```

---

## 4. Paso 3: Cuadro de Mandos de Saturación en Vivo

Durante la prueba, abra **3 terminales** para observar cómo se comporta la infraestructura:

### Terminal 1: Saturación Física de GPUs (Silicio)
```bash
kubectl exec -it deployment/vllm-inference-engine -c vllm-server -- \
  nvidia-smi dmon -s um -d 1
```
- **Qué vigilar:** 
  - Columna `sm`: Porcentaje de núcleos de cómputo en uso (subirá al 90-100% durante el Prefill).
  - Columna `fb` (Frame Buffer): Memoria VRAM fija ocupada (debe marcar ~19.000 MB para pesos y el resto asignado al pool de KV Cache).

### Terminal 2: Saturación del Planificador vLLM (Cola de Espera y KV Cache)
```bash
watch -n 1 "kubectl exec -it deployment/vllm-inference-engine -c vllm-server -- \
  curl -s http://localhost:8000/metrics | grep -E 'vllm:num_requests_running|vllm:num_requests_waiting|vllm:gpu_cache_usage_factor'"
```
- **Métricas clave:**
  - `vllm:num_requests_running`: Peticiones activas calculando tokens simultáneamente.
  - `vllm:num_requests_waiting`: Peticiones en cola en RAM de CPU (si sube de 0, el sistema está en saturación controlada).
  - `vllm:gpu_cache_usage_factor`: Porcentaje de la memoria elástica ocupada (debe fluctuar entre 0.05 y 0.95 sin superar 1.0).

### Terminal 3: Panel Gráfico Web de Auditoría (LiteLLM Dashboard)
Abra en el navegador web:
```text
http://<IP_DEL_GATEWAY>:4000/ui
```
- Introduzca la clave maestra: `sk-tier1-master-governance-key-2026`.
- Acceda a las pestañas:
  - **Usage / Spend:** Gráficas de barras con el número exacto de tokens consumidos por `vm-linux-gemini-01` en cada modelo.
  - **Logs:** Registro detallado de cada solicitud (latencia TTFT en milisegundos, prompt tokens y completion tokens).

---

## 5. Paso 4: Ejecución de la Prueba de Saturación Extrema

Lance el generador de carga para forzar la saturación del sistema:

```bash
# Lanzar 24 clientes concurrentes con prompts largos de razonamiento durante 5 rondas
python3 /home/jsanchhi/PoCGPU/scripts/benchmark.py \
  --url http://localhost:4000 \
  --key sk-tier1-master-governance-key-2026 \
  --concurrency 24 \
  --rounds 5
```

### Fenómenos a observar durante la prueba:
1. **Comportamiento de la cola:** `num_requests_running` se mantendrá en ~12-16 (el límite óptimo de la GPU), mientras que `num_requests_waiting` subirá a 8-12 peticiones.
2. **Latencia TTFT:** Subirá progresivamente de 200 ms a 1.200 ms para las peticiones encoladas.
3. **Estabilidad de VRAM:** `gpu_cache_usage_factor` tocará el 90-94%, pero **nunca saltará un error OOM ni se reiniciará el Pod**.
4. **Liberación Inmediata:** En cuanto finalice el script, la cola caerá a 0 y el factor de uso de KV Cache volverá a $\sim 0.00$ en menos de 2 segundos.

---

## 6. Paso 5: Consultar la Factura de Tokens por API Key vía Terminal

Una vez concluida la prueba, audite el consumo acumulado de la clave:

```bash
curl -X GET "http://localhost:4000/key/info?key=sk-litellm-78ab34cd90ef..." \
  -H "Authorization: Bearer sk-tier1-master-governance-key-2026"
```

**Resultado de auditoría devuelto:**
```json
{
  "info": {
    "user_id": "vm-linux-gemini-01",
    "team_id": "infra-ops",
    "spend": 0.042,
    "total_tokens": 14850,
    "prompt_tokens": 10200,
    "completion_tokens": 4650
  }
}
```
*Se comprueba con precisión de auditoría cuántos tokens ha consumido esa máquina concreta sin interferir con otros servicios.*
