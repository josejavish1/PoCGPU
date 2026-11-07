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
├── pyproject.toml                      # Definición de paquete y dependencias fijadas
├── uv.lock                             # Grafo completo de dependencias deterministas
│
├── pocs/                               # Entorno declarativo para PoCs de infraestructura Cloud/K8s
│   ├── README.md                       # Índice y guía de adición de nuevas PoCs
│   └── elastic-multi-gpu-inference/    # PoC clúster GKE Zúrich (4x L4 GPUs, TP=2, LiteLLM)
│       ├── README.md                   # Topología y comandos de arranque/hibernación
│       ├── manifests/                  # Manifiestos de Kubernetes (vLLM, Gateway, OpenWebUI)
│       ├── runbooks/                   # Guías operativas paso a paso (00_ a 08_)
│       └── scripts/                    # Scripts de benchmark de carga y sondas de saturación
│
├── calculators/                        # Calculadoras FinOps desacopladas
│   ├── README.md                       # Índice y principios de desacoplamiento
│   ├── docs/                           # Especificaciones matemáticas de Sizing y Chargeback
│   │   ├── 09_MODELO_FINOPS_CALCULADORA.md
│   │   └── 10_BACKLOG_FINOPS_INSTITUCIONAL.md
│   ├── sizing/                         # Calculadora A: Sizing y Física del Silicio (VRAM, Roofline)
│   │   ├── README.md
│   │   ├── src/
│   │   └── tests/
│   └── chargeback/                     # Calculadora B: Chargeback y TCO ($/Token, Amortización)
│       ├── README.md
│       ├── src/
│       └── tests/
│
├── src/pocgpu/                         # Motor canónico y Shared Kernel (paquete distribuible)
│   ├── domain/                         # Primitivas puras, ExactNumber, Money, Capacidad, TCO, Economics
│   ├── application/                    # Orquestadores y servicios de evaluación
│   ├── contracts/                      # Esquemas de frontera y DTOs de intercambio
│   ├── adapters/                       # Adaptadores de persistencia y catálogo
│   └── composition.py                  # Ensamblaje canónico
│
├── config/                             # Catálogos gobernados (hardware, modelos, pricing)
├── schemas/                            # Esquemas canónicos versionados (v1)
├── docs/                               # Constitución de ingeniería y ADRs
├── tests/                              # Batería de pruebas por fases de desarrollo
└── working/                            # Salidas dinámicas efímeras y ledger de auditoría
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

### A. PoC de Infraestructura Física (`pocs/elastic-multi-gpu-inference/`)
- [x] **Vía A (Interfaz Web Corporativa):** OpenWebUI operativo en puerto 80 estándar con directorio corporativo de NTT DATA.
- [x] **Vía B (Asistente de Programación):** Continue.dev enlazado con la clave `sk-9od6eun2IyOt7Qj8NZFeVQ` y el adaptador `coding-agent`.
- [x] **Vía C (Gobernanza Multi-Departamento):** 6 departamentos, cuotas presupuestarias en PostgreSQL, limitación RPM y analítica de caché.
- [x] **Observabilidad Integral:** Prometheus y Grafana operativos con dashboard `enterprise-ai-cluster-overview` auditando métricas de vLLM y LiteLLM.
- [x] **Vía D (Paso 1 - Alta Disponibilidad Activo-Activo):** 4x GPUs en 2 servidores balanceados por LiteLLM con rendimiento certificado de hasta 689 tokens/s en saturación.
- [ ] **Vía D (Paso 2 - PENDIENTE):** Prueba de Caída en Caliente (*Chaos Engineering*) deteniendo el Servidor 1 durante una ráfaga para verificar desvío al Servidor 2 sin pérdida de peticiones.
- [ ] **Vía D (Paso 3 - PENDIENTE):** Implementación de script de auto-degradación mono-GPU (`tensor-parallel-size=1`).
- **Estado de Cómputo:** Hibernado a coste $0.00/h. Discos zonales persistentes intactos en Zúrich.

### B. Calculadora A: Sizing y Física del Silicio (`calculators/sizing/`)
- [x] **Especificación Matemática:** Aprobada y documentada en `calculators/docs/09_MODELO_FINOPS_CALCULADORA.md` (VRAM pesos, KV Cache con GQA y Roofline).
- [x] **Modelo de Dominio:** Implementado en `src/pocgpu/domain/capacity/` y orquestado en `src/pocgpu/application/capacity_orchestrator.py`.
- [ ] **Empaquetado Independiente y CLI:** Puntos de entrada dedicados en `calculators/sizing/src/`.

### C. Calculadora B: Chargeback y TCO Empresarial (`calculators/chargeback/`)
- [x] **Especificación Matemática:** Aprobada y documentada en `calculators/docs/09_MODELO_FINOPS_CALCULADORA.md` (TCO amortizado, tarifario $/1M tokens y break-even).
- [x] **Modelo de Dominio:** Implementado en `src/pocgpu/domain/tco/`, `src/pocgpu/domain/economics/` y `src/pocgpu/application/economics_service.py`.
- [ ] **Empaquetado Independiente y CLI:** Puntos de entrada dedicados en `calculators/chargeback/src/`.

### D. Motor Canónico y Shared Kernel (`src/pocgpu/`)
- [x] **Fase 1 (Fundación Gobernada):** Certificada con 100% de cumplimiento de la Constitución de Ingeniería y CI determinista.
- [ ] **Fases 2 a 8:** En proceso de gobernanza según el roadmap de entrega (`docs/engineering-constitution/DELIVERY_ROADMAP.md`).

---

## 6. Instrucciones para la Interacción con el Usuario

1. **Perfil del Interlocutor:** Trátalo como a un par técnico de infraestructura/sistemas. Usa analogías de sistemas operativos, redes y storage para conceptos de IA (ej. KV cache = dynamic session heap; PagedAttention = MMU virtual memory paging).
2. **Estilo:** Cero fórmulas de cortesía ("Hola", "Entendido", "Por supuesto"), directo a la acción, sobrio, sin adulaciones ni celebraciones ficticias.
3. **Estado Actual:** Infraestructura hibernada a coste $0.00/h. Los 4 discos zonales y las configuraciones de red están preservados e intactos.
