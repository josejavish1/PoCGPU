# CONTEXTO_IA.md: Especificación y Memoria Operativa de PoCGPU

> **DOCUMENTO PARA AGENTES IA Y ORQUESTADORES COGNITIVOS**  
> Si eres una IA que entra a esta sesión o asiste al usuario en este repositorio, lee este archivo primero. Contiene el estado mental exacto, las decisiones arquitectónicas irreversibles y el mapeo funcional del proyecto.

---

## 1. Misión y Origen del Proyecto

- **Usuario:** Ingeniero Senior de Infraestructura y Cloud (experto en Kubernetes, redes, Linux, GCP y Bare-Metal; no especializado en entrenamiento de Deep Learning).
- **Problema Planteado:** Servir concurrentemente múltiples modelos LLM sobre aceleradores GPU en Kubernetes sin fragmentación estática de VRAM, garantizando gobernanza presupuestaria empresarial, alta disponibilidad y observabilidad integral.
- **Requisito Dinámico Crítico:** La VRAM debe comportarse como un recurso compartido elástico. El modelo base de razonamiento y los adaptadores especializados deben poder absorber hasta el 100% de la capacidad de KV Cache disponible bajo carga alta y liberar la memoria a nivel de microsegundos sin provocar desbordamientos (`CUDA OutOfMemory`).

---

## 2. Decisiones de Arquitectura (Axiomas Inmutables SOTA Tier-1)

Queda terminantemente prohibido proponer o implementar las siguientes soluciones convencionales fallidas:
1. **NO a NVIDIA MIG (Multi-Instance GPU):** Partición física rígida de hardware. Fragmenta el silicio, desperdicia VRAM y no permite que un modelo aproveche la capacidad ociosa de otros slices.
2. **NO a NVIDIA MPS (Multi-Process Service):** Carece de aislamiento de memoria a nivel de driver CUDA; un `CUDA OutOfMemory` en un proceso colapsa todos los modelos concurrentes en esa GPU.
3. **NO a Kubernetes Time-Slicing:** Serializa temporalmente la GPU mediante conmutación de contexto destructiva, disparando la latencia P99 e introduciendo micro-congelamientos (stalls) en streaming.
4. **NO a Pods independientes con límites estáticos de VRAM:** Fragmenta la memoria físicamente e imposibilita la absorción del 100% de la VRAM por parte de cadenas de pensamiento largas (*Chain-of-Thought*).

### La Solución Implementada:
- **Runtime Unificado con Tensor Parallelism (TP = 2):** Motor `vLLM` distribuido sobre 2x NVIDIA L4 por nodo (48 GB VRAM por servidor). Cada instancia vLLM fusiona las 2 GPUs físicas en un único dominio de tensores mediante operaciones NCCL All-Reduce sobre PCIe.
- **Multi-LoRA en Memoria:** El modelo base (`Mistral-7B-Instruct-v0.3`) se carga de forma inmutable en VRAM. Los modelos ligeros de tareas específicas se inyectan como adaptadores **LoRA** dinámicos (<100MB) en tiempo de ejecución sin duplicar los pesos base.
- **KV Cache Dinámico (PagedAttention):** La VRAM libre tras cargar los pesos se gestiona como un heap virtual paginado en bloques de 16 tokens, asignado y reciclado dinámicamente según la longitud del contexto.
- **Topología Desacoplada Activo-Activo (Zúrich `europe-west6-b`):**
  - **Node Pool CPU On-Demand (`default-pool`):** Aloja el plano de gestión (`LiteLLM Gateway`), `PostgreSQL`, `OpenWebUI`, `Prometheus` y `Grafana`.
  - **Node Pool GPU Spot (`gpu-pool`):** 2 nodos `g2-standard-24` con 2x NVIDIA L4 cada uno (**4x GPUs L4 = 96 GB VRAM combinada**), ejecutando dos réplicas vLLM independientes balanceadas por el Gateway L7.
- **Enterprise AI Gateway L7 (`LiteLLM Proxy`):** Desplegado en CPU con backend relacional PostgreSQL. Gobierna cuotas en dólares para 6 departamentos, límites de RPM/TPM, balanceo de carga L7 y claves de API auditables.
- **FinOps Determinista e Hibernación:** Cuatro discos persistentes zonales (Zonal PD) preservan pesos, estado relacional y chats. Permite congelar el cómputo a $0.00/h en 1 paso y reactivarlo en ~90 segundos.

---

## 3. Mapeo Exhaustivo de Ficheros del Directorio `/home/jsanchhi/PoCGPU`

```text
/home/jsanchhi/PoCGPU/
├── README.md                           # Índice general, objetivos y arquitectura consolidada
├── CONTEXTO_IA.md                      # [ESTE ARCHIVO] Memoria operativa para agentes IA
├── 00_ARQUITECTURA_Y_PRINCIPIOS.md     # Teoría, diccionario infra->IA y comparativa SOTA
├── 01_VALIDACION_HARDWARE_Y_FABRIC.md  # Procedimiento de auditoría de enlaces PCIe/NVLink y NCCL
├── 02_STORAGE_Y_PESOS.md               # Gestión de Safetensors, cuotas de VRAM y precarga de pesos
├── 03_DESPLIEGUE_MOTOR_VLLM_TP2.md     # Manifiesto y lifecycle del motor distribuido vLLM con TP=2
├── 04_ENTERPRISE_AI_GATEWAY.md         # Manifiesto del Gateway LiteLLM en CPU y rutas OpenAPI
├── 05_PRUEBAS_DE_CARGA_Y_BENCHMARK.md  # Metodología de benchmarking (TTFT, TPOT, VRAM) y Quality Gates
├── 06_GUIA_PRACTICA_POC_SATURACION.md  # Procedimiento de emisión de API Keys y pruebas de saturación
├── 07_VARIANTE_MINIMO_COSTE_SPOT_MISTRAL.md # Configuración de coste mínimo en GCP Spot con Mistral-7B
├── 08_ESTADO_ZURICH_Y_OPERACIONES.md   # Guía operativa: Reactivación, hibernación, credenciales y URLs
├── 09_MODELO_FINOPS_CALCULADORA.md     # Especificación FinOps: Sizing de hardware, Roofline y chargeback
├── 10_BACKLOG_FINOPS_INSTITUCIONAL.md  # Backlog técnico Tier-1: Primitivas neurosimbólicas y hoja de ruta
├── docs/RFC_063_UNIVERSAL_HYBRID_FINOPS_ADVISOR_ARGON.md # Master Blueprint: Universal Hybrid FinOps Advisor (gemini-4-argon)
├── docs/RFC_064_PHASE2_DOMAIN_SERVICES_SPECIFICATION_ARGON.md # Phase 2 Technical Specification: Pure Domain Services (gemini-4-argon)
├── docs/RFC_065_ZERO_DEFECT_ZERO_HARDCODING_MASTER_PLAN_ARGON.md # Master Quality Plan: Universal Zero-Defect & Zero-Hardcoding (gemini-4-argon)
├── manifests/
│   ├── 01_gpu_audit.yaml               # Pod temporal para auditar topología P2P y ancho de banda NCCL
│   ├── 02_storage.yaml                 # PVC genérico y Job preloader de almacenamiento
│   ├── 02_storage_zurich.yaml          # PVC vinculado al disco persistente en Zúrich (Servidor 1)
│   ├── 02_storage_replica2.yaml        # PVC vinculado al disco persistente en Zúrich (Servidor 2)
│   ├── 03_vllm_service.yaml            # Deployment del Servidor 1 de vLLM (TP=2, 2x L4) + Service
│   ├── 03_vllm_replica2.yaml           # Deployment del Servidor 2 de vLLM (TP=2, 2x L4) + Service
│   ├── 04_gateway.yaml                 # Deployment de LiteLLM Gateway L7 + PostgreSQL + ConfigMap
│   ├── 05_linux_client.yaml            # Pod cliente Linux in-cluster para pruebas de latencia interna
│   ├── 06_openwebui.yaml               # Deployment de OpenWebUI + PVC de configuración y cuentas
│   ├── 07_observability_and_alerts.yaml# Reglas de alerta Prometheus y exportadores vLLM
│   └── 08_grafana_prometheus.yaml      # Stack Prometheus + Grafana con dashboard empresarial
└── scripts/
    ├── benchmark.py                    # Suite asíncrona de pruebas de carga con streaming (httpx)
    ├── classify_incident.py            # Validador de inferencia de incidentes con adaptador LoRA
    ├── enrich_enterprise_metrics.py    # Inyector de tráfico sintético para métricas en Grafana
    ├── finops_tier1_engine.py          # Motor FinOps Tier-1: Planificador de capacidad, Roofline y TCO
    ├── ide_copilot_simulator.py        # Simulador de peticiones concurrentes de IDE Continue.dev
    ├── interactive_chat.py             # Cliente CLI interactivo con métricas de streaming y TTFT
    ├── saturation_probe.py             # Sonda de saturación extrema de KV Cache y PagedAttention
    ├── seed_enterprise_demo.py         # Poblador de departamentos, cuotas y usuarios en PostgreSQL
    ├── simulate_enterprise_governance.py # Validador de políticas de cuota presupuestaria y RPM
    └── verify_balanced_saturation.py   # Verificador de balanceo de carga Activo-Activo entre réplicas
```

---

## 4. Parámetros Técnicos Críticos que NO Deben Modificarse a Ciegas

- `sizeLimit: 16Gi` en `/dev/shm` de los pods `vllm-inference-engine`: PyTorch IPC y NCCL requieren memoria compartida POSIX masiva para coordinar TP=2 entre GPUs. El valor por defecto de 64MB provoca colapso inmediato con `SIGBUS`.
- `--gpu-memory-utilization=0.90`: Reserva el 90% de la VRAM física de cada L4 para pesos + KV Cache, dejando el 10% restante para activaciones CUDA y sobrecarga de runtime.
- `startupProbe.failureThreshold: 30` (300 segundos): Tiempo requerido para permitir la carga de pesos Safetensors desde disco zonal y la compilación de **CUDA Graph Capture**.
- `DATABASE_URL` en LiteLLM: Conexión persistente hacia PostgreSQL (`postgresql://postgres:...@litellm-postgres-svc:5432/litellm`). Si LiteLLM arranca sin base de datos, entra en modo memoria volátil y pierde las cuotas departamentales al reiniciar.
- `PORT_FORWARDING`: El túnel local en la VM de gestión redirige los puertos `8000` (OpenWebUI), `8080` (LiteLLM Gateway) y `8082` (Grafana) con enlace a `0.0.0.0` para acceso público por IP.

---

## 5. Estado Actual del Proyecto y Roadmap

- [x] **Vía A (Interfaz Web Corporativa):** OpenWebUI operativo en puerto 80 estándar con directorio corporativo de NTT DATA.
- [x] **Vía B (Asistente de Programación):** Continue.dev enlazado con la clave `sk-9od6eun2IyOt7Qj8NZFeVQ` y el adaptador `coding-agent`.
- [x] **Vía C (Gobernanza Multi-Departamento):** 6 departamentos, cuotas presupuestarias en PostgreSQL, limitación RPM y analítica de caché.
- [x] **Observabilidad Integral:** Prometheus y Grafana operativos con dashboard `enterprise-ai-cluster-overview` auditando métricas de vLLM y LiteLLM.
- [x] **Vía D (Paso 1 - Alta Disponibilidad Activo-Activo):** 4x GPUs en 2 servidores balanceados por LiteLLM con rendimiento certificado de hasta 689 tokens/s en saturación.
- [ ] **Vía D (Paso 2 - PENDIENTE):** Prueba de Caída en Caliente (*Chaos Engineering*) deteniendo el Servidor 1 durante una ráfaga para verificar desvío al Servidor 2 sin pérdida de peticiones.
- [ ] **Vía D (Paso 3 - PENDIENTE):** Implementación de script de auto-degradación mono-GPU (`tensor-parallel-size=1`).

---

## 6. Instrucciones para la Interacción con el Usuario

1. **Perfil del Interlocutor:** Trátalo como a un par técnico de infraestructura/sistemas. Usa analogías de sistemas operativos, redes y storage para conceptos de IA (ej. KV cache = dynamic session heap; PagedAttention = MMU virtual memory paging).
2. **Estilo:** Cero fórmulas de cortesía ("Hola", "Entendido", "Por supuesto"), directo a la acción, sobrio, sin adulaciones ni celebraciones ficticias.
3. **Estado Actual:** Infraestructura hibernada a coste $0.00/h. Los 4 discos zonales y las configuraciones de red están preservados e intactos.
