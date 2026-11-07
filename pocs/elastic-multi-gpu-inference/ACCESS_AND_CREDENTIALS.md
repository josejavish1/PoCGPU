# Ficha Centralizada de Accesos y Credenciales de la PoC

Esta ficha contiene las URLs, credenciales de administración, claves de API y puertos de acceso para todos los componentes de la plataforma de inferencia desplegada en GKE Zúrich (`europe-west6-b`).

---

## 1. Resumen Rápido de Puntos de Entrada

| Servicio | URL Pública (IP Servidor) | URL Local (Port-Forward) | Tipo de Acceso | Credenciales / Token |
| :--- | :--- | :--- | :--- | :--- |
| **OpenWebUI** (ChatGPT Corporativo) | `http://34.175.194.93` | `http://localhost:8000` | Web UI | `josejavish@gmail.com`<br>`josejavier.sanchezhidalgo@nttdata.com` |
| **LiteLLM Gateway** (vLLM Router & Gov) | `http://34.175.194.93:8080/ui/` | `http://localhost:8080/ui/` | Web Admin | Usuario: `admin`<br>Password: `sk-tier1-master-governance-key-2026` |
| **Grafana Oficial** (Métricas Clúster) | `http://34.175.194.93:8082` | `http://localhost:8082` | Dashboard | Usuario: `admin`<br>Password: `tier1_grafana_pass_2026` |
| **API Router LLM** (OpenAI-Compatible) | `http://34.175.194.93:8080/v1` | `http://localhost:8080/v1` | REST API | Bearer Token (Ver sección 4) |

---

## 2. OpenWebUI (ChatGPT Corporativo para Empleados)

- **Propósito:** Interfaz de chat corporativo privado para consumo de usuarios finales sin salida de datos a proveedores externos.
- **URL Directa:** `http://34.175.194.93` (o `http://localhost:8000`)
- **Cuentas precargadas:**
  - **Administrador:** `josejavish@gmail.com`
  - **Corporativo NTT DATA:** `josejavier.sanchezhidalgo@nttdata.com`
- **Registro:** Habilitado para cuentas de dominio corporativo sin aprobación manual previa en este entorno piloto.
- **Modelos disponibles en el selector:** `reasoning-model`, `light-model-fast`, `light-model-coder`, `gemini-cloud-backup`.

---

## 3. LiteLLM Enterprise AI Gateway (vLLM Router y Gobernanza)

- **Propósito:** Router L7 de inferencia con balanceo Activo-Activo entre los servidores vLLM, control presupuestario en dólares, rate limiting y auditoría.
- **Dashboard Web:** `http://34.175.194.93:8080/ui/` (o `http://localhost:8080/ui/`)
- **Credenciales:**
  - **Usuario:** `admin`
  - **Contraseña / Master Key:** `sk-tier1-master-governance-key-2026`
- **Capacidades del Panel:**
  - Pestaña **Models:** Inspección de servidores GPU activos (Servidor 1 y Servidor 2) y estado de los modelos.
  - Pestaña **Usage / Spend:** Desglose analítico de tokens y presupuesto consumido por departamento.
  - Pestaña **API Keys:** Generación y revocación en caliente de claves virtuales con cuotas en dólares.
  - Pestaña **Logs:** Trazabilidad de cada solicitud con latencia TTFT, tokens generados y respuesta devuelta.

---

## 4. Claves de API y Conexión para Clientes (IDE Continue.dev, Cursor, Curl)

El router expone un endpoint estándar compatible al 100% con la especificación de OpenAI:
- **Base URL:** `http://34.175.194.93:8080/v1` (o `http://localhost:8080/v1`)

### Claves Emitidas y Cuotas:
| Nombre de Clave | Token de Acceso | Cuota Máxima | Modelos Autorizados |
| :--- | :--- | :--- | :--- |
| **Master Governance Key** | `sk-tier1-master-governance-key-2026` | Ilimitada | Todos (`*`) |
| **IDE Continue / Coding** | `sk-9od6eun2IyOt7Qj8NZFeVQ` | \$50.00 | `light-model-coder`, `reasoning-model` |
| **VM Linux Client Demo** | `sk-litellm-linux-client-2026` | \$25.00 | `light-model-fast`, `reasoning-model` |

### Catálogo de Modelos del Router:
1. `reasoning-model`: Modelo principal para razonamiento profundo (Mistral-7B / Qwen-2.5-32B).
2. `light-model-fast`: Modelo ultrarrápido para resúmenes, extracción y chat general.
3. `light-model-coder`: Modelo asistido con LoRA especializado en programación e integración con IDE.
4. `gemini-cloud-backup`: Ruta de desborde elástico (*Cloud Bursting*) a Google Gemini Cloud cuando la GPU física está en contención.

### Configuración para IDE Continue (`~/.continue/config.json`):
```json
{
  "models": [
    {
      "title": "Private Enterprise LLM",
      "provider": "openai",
      "model": "light-model-coder",
      "apiKey": "sk-9od6eun2IyOt7Qj8NZFeVQ",
      "apiBase": "http://34.175.194.93:8080/v1"
    }
  ]
}
```

---

## 5. Grafana (Observabilidad de Hardware y Rendimiento en Tiempo Real)

- **URL Dashboard Directo:** `http://34.175.194.93:8082/d/enterprise-ai-cluster-overview?refresh=5s`
- **Credenciales:**
  - **Usuario:** `admin`
  - **Contraseña:** `tier1_grafana_pass_2026`
- **Métricas Monitorizadas:**
  - Cómputo de Streaming Multiprocessors (`sm%`) en las 4x GPUs NVIDIA L4.
  - Consumo y porcentaje de saturación de VRAM (`fb_used` vs `fb_free`).
  - Utilización dinámica de KV Cache y PagedAttention en vLLM (`gpu_cache_usage_factor`).
  - Cola de peticiones en espera (`num_requests_waiting`).
  - Throughput global de tokens/segundo y latencia TTFT (P50, P90, P99).

---

## 6. Comandos Operativos de Automatización

Para gestionar el ciclo de vida sin recordar comandos manuales:

### Arrancar y Verificar Todo Automáticamente:
```bash
python3 pocs/elastic-multi-gpu-inference/scripts/up_and_verify.py
```

### Verificar Sin Reescalar (si ya está encendido):
```bash
python3 pocs/elastic-multi-gpu-inference/scripts/up_and_verify.py --skip-resize
```

### Congelar / Hibernar Plataforma (Coste = $0.00/h):
```bash
gcloud container clusters resize poc-gpu-cluster-ch --node-pool=gpu-pool --num-nodes=0 --zone=europe-west6-b --quiet && \
gcloud container clusters resize poc-gpu-cluster-ch --node-pool=default-pool --num-nodes=0 --zone=europe-west6-b --quiet && \
pkill -f "kubectl port-forward" 2>/dev/null || true
```
