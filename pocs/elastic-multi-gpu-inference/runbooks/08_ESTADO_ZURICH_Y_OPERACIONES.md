# 08. Operaciones del Clúster en Zúrich, Hibernación y Guía de Reactivación

Este documento recoge el estado exacto de la infraestructura, inventario de recursos persistentes y los comandos rápidos para reactivar o congelar la plataforma sin perder datos ni acumular costes.

---

## 1. Topología del Clúster Consolidado (Tier-1)

- **Región y Zona:** `europe-west6-b` (Zúrich, Suiza) — Stock garantizado de GPUs L4 y baja latencia europea (~15 ms).
- **Clúster GKE:** `poc-gpu-cluster-ch`
- **Node Pools:**
  1. `default-pool`: Nodo CPU On-Demand (`e2-standard-2`). Aloja el plano de gestión permanente (LiteLLM Gateway, PostgreSQL, OpenWebUI, Prometheus y Grafana).
  2. `gpu-pool`: 2 Nodos GPU Spot (`g2-standard-24` con 2x NVIDIA L4 cada uno). Suma **4x GPUs NVIDIA L4 (96 GB VRAM combinada)** en balanceo Activo-Activo.

---

## 2. Inventario de Almacenamiento Persistente (Preservado al 100%)

Los 4 discos residen de forma permanente en Google Cloud Storage en Zúrich (independientes del ciclo de vida de los servidores):

| Disco Físico (Zonal PD) | Tamaño | PVC de Kubernetes | Contenido Preservado |
| :--- | :--- | :--- | :--- |
| **`mistral-weights-disk-ch`** | 100 GB | `llm-weights-cache-pvc` | Pesos de Mistral-7B y adaptadores LoRA (Servidor 1). |
| **`mistral-weights-disk-ch-2`** | 100 GB | `llm-weights-cache-pvc-2` | Pesos de Mistral-7B y adaptadores LoRA (Servidor 2). |
| **`pvc-08ae554b...`** | 10 GB | `litellm-db-pvc` | Base de datos PostgreSQL (departamentos, usuarios, claves, histórico de gasto y logs de errores). |
| **`pvc-c071f625...`** | 5 GB | `openwebui-data-pvc` | Base de datos de OpenWebUI (cuentas de empleados @emeal.nttdata.com y chats). |

---

## 3. Comandos Operativos

### A. Para Reactivar el Clúster (Enciende todo en ~90 segundos)
Ejecuta desde esta máquina de gestión (`assessment`):

```bash
# 1. Encender el servidor CPU de gestión (1 nodo) y los 2 servidores de GPU (2 nodos = 4 GPUs)
gcloud container clusters resize poc-gpu-cluster-ch --node-pool=default-pool --num-nodes=1 --zone=europe-west6-b --quiet && \
gcloud container clusters resize poc-gpu-cluster-ch --node-pool=gpu-pool --num-nodes=2 --zone=europe-west6-b --quiet

# 2. Levantar los túneles locales de acceso público en background
kubectl port-forward --address 0.0.0.0 svc/open-webui-svc 8000:80 >/dev/null 2>&1 &
kubectl port-forward --address 0.0.0.0 svc/enterprise-ai-gateway-svc 8080:80 >/dev/null 2>&1 &
kubectl port-forward --address 0.0.0.0 svc/grafana-service 8082:3000 >/dev/null 2>&1 &
```

### B. Para Congelar / Hibernar el Clúster (Coste de cómputo = $0.00/h)
Ejecuta cuando termines la jornada para no pagar servidores:

```bash
# 1. Detener túneles locales
pkill -f "kubectl port-forward" 2>/dev/null || true

# 2. Redimensionar a 0 nodos (Cero gasto en CPUs y GPUs)
gcloud container clusters resize poc-gpu-cluster-ch --node-pool=gpu-pool --num-nodes=0 --zone=europe-west6-b --quiet && \
gcloud container clusters resize poc-gpu-cluster-ch --node-pool=default-pool --num-nodes=0 --zone=europe-west6-b --quiet
```
*(Nota: La máquina `assessment` donde trabajas NUNCA se apaga con estos comandos).*

---

## 4. Direcciones Web y Credenciales de Acceso

| Plataforma | URL Pública | Credenciales | Público Objetivo |
| :--- | :--- | :--- | :--- |
| **OpenWebUI** | `http://34.175.194.93` | Admin: `josejavish@gmail.com`<br>Corp: `josejavier.sanchezhidalgo@nttdata.com` | **Empleados:** ChatGPT privado corporativo. |
| **LiteLLM Gateway** | `http://34.175.194.93:8080/ui/` | Usuario: `admin`<br>Password: `sk-tier1-master-governance-key-2026` | **Dirección / IT:** Gobernanza de cuotas, 6 departamentos y costes en dólares. |
| **Grafana Oficial** | `http://34.175.194.93:8082/d/enterprise-ai-cluster-overview?refresh=5s` | Acceso directo como Viewer o Admin: `admin` / `tier1_grafana_pass_2026` | **SOC / Infraestructura:** 4x GPUs NVIDIA L4, colas vLLM y tabla de errores en vivo. |

---

## 5. Estado del Plan de la PoC (Roadmap)

- [x] **Vía A (Interfaz Web Corporativa):** OpenWebUI operativo en puerto 80 estándar con directorio corporativo de NTT DATA.
- [x] **Vía B (Asistente de Programación):** Continue.dev enlazado con la clave `sk-9od6eun2IyOt7Qj8NZFeVQ` y el adaptador `coding-agent`.
- [x] **Vía C (Gobernanza Multi-Departamento):** 6 departamentos, cuotas de $25 a $150, limitación RPM y analítica de caché.
- [ ] **Vía D (Resiliencia Extrema y Alta Disponibilidad):**
  - [x] *Paso 1:* 4x GPUs en 2 servidores Activo-Activo con rendimiento certificado de ~90 tokens/segundo (hasta 689 tok/s en saturación masiva).
  - [ ] *Paso 2 (PENDIENTE):* Prueba de Caída en Caliente (Chaos Engineering) matando el Servidor 1 durante una ráfaga para verificar desvío al Servidor 2 y Gemini sin errores.
  - [ ] *Paso 3 (PENDIENTE):* Integración del script de auto-degradación mono-GPU (`tensor-parallel-size=1`).
