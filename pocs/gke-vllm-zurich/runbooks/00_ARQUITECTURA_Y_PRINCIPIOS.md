# 00. Arquitectura y Principios de Diseño (Tier-1 SOTA)

## 1. Diccionario de Equivalencias: De Infraestructura Tradicional a IA

Para ingenieros de sistemas, redes y Kubernetes, los conceptos de IA generativa se corresponden directamente con primitivas clásicas de infraestructura:

| Concepto de IA / LLM | Equivalente en Infraestructura Tradicional | Explicación Técnica y Por Qué Importa |
| :--- | :--- | :--- |
| **Parámetros del Modelo (ej. 32B)** | **Binario inmutable del sistema** | 32 mil millones de números flotantes (pesos) que definen la red. En 16-bit ocupan 64 GB; en 4-bit (AWQ) ocupan ~18 GB. Son de solo lectura. |
| **VRAM (Memoria GPU)** | **RAM ultrarrápida dedicada (HBM/GDDR)** | Ancho de banda de 1.000 a 3.000 GB/s (frente a los 50-100 GB/s de la RAM DDR5 de la CPU). Si los tensores no están en VRAM, la inferencia se ralentiza 30 veces. |
| **Token** | **Unidad mínima de I/O de red/texto** | Aproximadamente 4 caracteres o 0.75 palabras en inglés/español. Las peticiones y respuestas se miden en tokens, no en bytes. |
| **Prefill Phase** | **Procesamiento de Request Body (Cálculo)** | Cuando llega el prompt del usuario, la GPU procesa todos los tokens de entrada en paralelo en una sola pasada. Satura los núcleos CUDA al 100%. |
| **Decode Phase** | **Streaming Response (Generación continua)** | La GPU genera la respuesta token a token de forma secuencial. Cada nuevo token requiere leer todos los pesos del modelo de nuevo. Es intensivo en ancho de banda de memoria. |
| **KV Cache (Key-Value)** | **Buffer de sesión dinámica en memoria** | Para generar el siguiente token sin recalcular toda la conversación previa, la GPU almacena en VRAM el estado de atención de los tokens anteriores. **Este buffer crece con cada token generado**. |
| **PagedAttention** | **Paginación de Memoria Virtual (MMU / OS Paging)** | Tradicionalmente, el KV Cache requería memoria contigua en VRAM (causando 60-80% de fragmentación). PagedAttention divide la memoria en páginas de 16 tokens no contiguas, permitiendo compartir y reusar VRAM al 100%. |
| **Tensor Parallelism (TP)** | **RAID 0 de cálculo matricial** | Une 2 o más GPUs como si fueran una sola. Divide horizontalmente las matrices de cada capa entre las GPUs. Requiere sincronización inter-GPU en cada token. |
| **LoRA (Low-Rank Adaptation)** | **Parche dinámico / Shared Library (.so)** | En vez de cargar 3 modelos completos de 32B (requeriría 6 GPUs), se carga un modelo base y se inyectan matrices delgadas de especialización (<100MB) en tiempo de ejecución. |

---

## 2. Problema de Infraestructura y Restricciones
- **Recursos físicos:** Exactamente 2 GPUs (ej. NVIDIA L4 24GB, A100 80GB o H100 80GB) en un único nodo Kubernetes.
- **Cargas de trabajo:** 
  - 1 Modelo de razonamiento profundo (ej. Qwen-2.5-32B-Instruct o DeepSeek-R1-Distill-Qwen-32B).
  - 2 Modelos ligeros (especializados para tareas rápidas, clasificación, resúmenes o código).
- **Objetivo dinámico:** El modelo de razonamiento debe poder utilizar hasta el 100% de la capacidad de cómputo y memoria VRAM cuando la carga lo exija, sin que los modelos ligeros queden bloqueados permanentemente o reserven VRAM ociosa.

---

## 3. Por qué los enfoques convencionales fallan en Producción

```
ENFOQUE TRADICIONAL FALLIDO (Partición Estática):
GPU 0 (24GB) ───► [ Pod Modelo 1: 12GB fija ] | [ Pod Modelo 2: 12GB fija ]
GPU 1 (24GB) ───► [ Pod Modelo 3: 12GB fija ] | [ Espacio Ocioso Desperdiciado ]
Fallo: Si Modelo 1 recibe un prompt de razonamiento largo, explota con OOM porque no puede
usar el espacio ocioso de los otros modelos.

ENFOQUE SOTA TIER-1 (Runtime Unificado Elástico):
GPU 0 (24GB) ┐
             ├─► [ RUNTIME DISTRIBUIDO TP=2 (48GB VRAM Total Unificada) ]
GPU 1 (24GB) ┘   ├─ Pesos Base Compartidos: 19 GB (Inmutables)
                 ├─ Adaptadores LoRA Ligeros: < 1 GB (Bajo demanda)
                 └─ Pool Dinámico PagedAttention: 28 GB (Elástico hasta el 100%)
```

| Estrategia | Mecanismo | Fallo Crítico en Producción Tier-1 |
| :--- | :--- | :--- |
| **NVIDIA MIG (Multi-Instance GPU)** | Particiona silicio y VRAM físicamente (ej. 3 slices por GPU). | **Particionamiento estático:** Si el modelo de razonamiento requiere el 100% de la GPU, no puede tomar la VRAM asignada a los otros slices, aunque estén inactivos. |
| **NVIDIA MPS (Multi-Process Service)** | Multiplexa contextos CUDA en un único daemon en el host. | **Cero aislamiento de memoria:** Si uno de los modelos dispara un `CUDA OutOfMemory`, el daemon MPS falla y tumba todos los procesos concurrentes en esa GPU. |
| **Kubelet Time-Slicing** | Alterna temporalmente la ejecución entre contenedores en la misma GPU. | **Latencia P99 destruida:** Cada conmutación de contexto expulsa y recarga registros y cachés. Provoca congelamiento de tokens (stalls) inadmisibles en streaming. |
| **3 Pods independientes con límites de VRAM** | Cada Pod arranca su propio motor de inferencia con VRAM prefijada. | **Fragmentación estática:** Si fijas 30% VRAM a cada modelo ligero y 40% al pesado, el pesado nunca podrá pasar del 40%, impidiendo contextos largos de razonamiento. |

---

## 4. La Solución SOTA Tier-1: Runtime Unificado y Elástico

### A. Tensor Parallelism Distribuido (TP = 2)
En lugar de fragmentar las 2 GPUs entre múltiples contenedores, se fusionan en un único dominio de ejecución:
- Las 2 GPUs se configuran en `tensor_parallel_size: 2`.
- Las matrices de pesos de las capas de atención y MLP se dividen horizontalmente entre GPU 0 y GPU 1.
- Ambas GPUs colaboran en cada paso de generación de token mediante operaciones `All-Reduce` a través del bus de interconexión (NVLink o PCIe).

### B. Gestión Elástica de Memoria: PagedAttention y KV Cache Pooling
- La VRAM física total combinada (ej. $24\text{ GB} \times 2 = 48\text{ GB}$) se divide en dos bloques:
  1. **Pesos de los modelos (Weights Pool):** Espacio estático inmutable (~19 GB con AWQ).
  2. **Caché de Claves y Valores (KV Cache Pool):** Espacio dinámico paginado en bloques de memoria de tamaño fijo (ej. 16 tokens, ocupando ~29 GB).
- Cuando el modelo de razonamiento procesa una cadena de pensamiento larga (*Chain-of-Thought* de 8K+ tokens), el motor asigna dinámicamente bloques del KV Cache Pool hasta agotar la VRAM libre.
- Cuando la petición termina, las páginas de memoria se reciclan inmediatamente a nivel de microsegundos sin reiniciar contenedores ni reasignar recursos de Kubernetes.

### C. Estrategia Multi-Modelo: Multi-LoRA
- Se carga el modelo base de razonamiento profundo en las 2 GPUs (`TP=2`).
- Los modelos ligeros se despliegan como adaptadores **LoRA** (*Low-Rank Adaptation*) compatibles con la misma familia arquitectónica (ej. Qwen-2.5).
- El runtime carga y descarga adaptadores en milisegundos en VRAM según el campo `model` de la petición HTTP.
- Beneficio: Cero duplicación de capas base; 100% de elasticidad.

---

## 5. Topología Física y Requisitos de Fabric

```
┌────────────────────────────────────────────────────────────────────────┐
│                              HOST NUMA NODE                            │
│                                                                        │
│   ┌───────────────────────┐                  ┌──────────────────────┐  │
│   │     GPU FÍSICA 0      │◄════════════════►│     GPU FÍSICA 1     │  │
│   │   (Device /dev/nvidia0│   NVLink / PCIe  │  (Device /dev/nvidia1│  │
│   └───────────┬───────────┘    >= 25 GB/s    └───────────┬──────────┘  │
│               │                                          │             │
│               └────────────────────┬─────────────────────┘             │
│                                    ▼                                   │
│                 ┌──────────────────────────────────────┐               │
│                 │      NVIDIA Kubelet Device Plugin    │               │
│                 │   (Solicitud atómica: nvidia.com/gpu: 2)             │
│                 └──────────────────┬───────────────────┘               │
└────────────────────────────────────┼───────────────────────────────────┘
                                     │
                                     ▼
                   ┌───────────────────────────────────┐
                   │    POD DE INFERENCIA (vLLM)       │
                   │    - Worker 0 -> GPU 0            │
                   │    - Worker 1 -> GPU 1            │
                   │    - NCCL Backend vía P2P         │
                   └───────────────────────────────────┘
```

---

## 6. Matriz de Decisión: GCP (GKE) vs On-Premise

| Dimensión | Google Cloud (GKE) | On-Premise (Bare-Metal) |
| :--- | :--- | :--- |
| **Orquestador** | GKE Standard con Node Pools GPU. | Kubernetes $\ge$ 1.28 + `nvidia-gpu-operator`. |
| **Driver GPU** | Gestionado automáticamente por GKE (`gpu-driver-version: default` o `latest`). | Driver NVIDIA Data Center $\ge$ 535.xx instalado vía Operator. |
| **Interconexión** | Máquinas con GPUs L4 conectadas por PCIe o A100 conectadas por NVLink interno. | Obligatorio verificar enlace PCIe sin cruce de zócalos NUMA (`nvidia-smi topo -m`). |
| **Almacenamiento** | Persistent Disk Extreme (NVMe) o GCS CSI Fuse con caché en SSD local. | NVMe Direct-Attached Storage (Local PV) o Ceph RBD sobre red 100GbE. |
| **Ingress / L7** | Cloud Load Balancer + NEG hacia Gateway en Pods CPU. | MetalLB / BGP + Gateway (LiteLLM/Envoy) en Pods CPU. |
