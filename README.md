# PoCGPU: Plataforma Empresarial de Inferencia LLM Elástica y Gobernanza en Kubernetes

Blueprint de ingeniería de infraestructura Tier-1 para servir modelos LLM concurrentes sobre aceleradores GPU sin fragmentación estática de VRAM, integrando balanceo Activo-Activo, gobernanza de costes por departamento, observabilidad en tiempo real y consumo corporativo (Web e IDE).

---

## 1. Objetivos del Proyecto

1. **Inferencia Elástica Multi-Modelo (SOTA Tier-1):** Servir concurrentemente un modelo base de razonamiento y adaptadores especializados (LoRA) sobre un runtime unificado distribuido (`vLLM` con Tensor Parallelism `TP=2` y `PagedAttention`), permitiendo que el KV Cache absorba dinámicamente hasta el 100% de la VRAM libre sin particiones rígidas ni fallos por OOM.
2. **Gobernanza y FinOps Multi-Departamento:** Desplegar un Enterprise AI Gateway L7 (`LiteLLM Proxy`) respaldado por `PostgreSQL` en nodos CPU, aplicando cuotas presupuestarias en dólares, limitación de RPM/TPM y control de claves API para múltiples departamentos corporativos.
3. **Alta Disponibilidad Activo-Activo:** Topología desacoplada en GKE con 4x NVIDIA L4 (96 GB VRAM combinada) repartidas en 2 nodos Spot independientes, balanceadas en capa 7 y capaces de sostener más de 680 tokens/s en saturación.
4. **Consumo Corporativo Directo:** Exposición segura de endpoints compatibles con OpenAI para:
   - **Empleados:** Interfaz web corporativa privada (`OpenWebUI`) con cuentas empresariales.
   - **Ingeniería:** Asistente de programación en el IDE (`Continue.dev` / Copilot privado).
5. **Observabilidad Completa de Silicio y Gateway:** Monitorización centralizada con Prometheus y Grafana de saturación de VRAM, ocupación de KV Cache, latencias TTFT/TPOT, colas de peticiones y registro de errores.
6. **FinOps Determinista (Hibernación a $0.00/h):** Procedimiento de congelación y reactivación rápida mediante persistencia desacoplada en 4 Discos Zonales Permanentes (pesos del modelo, LoRAs, base de datos relacional y configuración de chats).

---

## 2. Topología de Infraestructura (Zúrich `europe-west6-b`)

```
                                      [ USUARIOS / CLIENTES ]
                                                 │
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │    OpenWebUI (80) / IDE Continue (8080)│
                             └───────────────────┬───────────────────┘
                                                 │
                                                 ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ NODO CPU ON-DEMAND (e2-standard-2) - Plano de Gestión y Observabilidad                │
 │                                                                                        │
 │  ┌─────────────────────────────────┐       ┌────────────────────────────────────────┐  │
 │  │ LiteLLM Enterprise AI Gateway   │◄─────►│ PostgreSQL (litellm-db-pvc)           │  │
 │  │ (Balanceo L7, Auth, Cuotas FinOps)│      │ (Cuotas, Departamentos, Logs, Gasto)   │  │
 │  └────────────────┬────────────────┘       └────────────────────────────────────────┘  │
 │                   │                                                                    │
 │  ┌────────────────┴────────────────┐       ┌────────────────────────────────────────┐  │
 │  │ Prometheus Server               │──────►│ Grafana Dashboard Oficial              │  │
 │  │ (Scrape vLLM + Gateway)         │       │ (VRAM, KV Cache, TTFT, TPOT, RPM)      │  │
 │  └─────────────────────────────────┘       └────────────────────────────────────────┘  │
 └───────────────────┬────────────────────────────────────────────────────────────────────┘
                     │ (Load Balancing L7: /v1/chat/completions)
          ┌──────────┴──────────┐
          ▼                     ▼
 ┌───────────────────┐ ┌───────────────────┐
 │ NODO GPU SPOT 1   │ │ NODO GPU SPOT 2   │
 │ (g2-standard-24)  │ │ (g2-standard-24)  │
 │                   │ │                   │
 │ 2x NVIDIA L4 24GB │ │ 2x NVIDIA L4 24GB │
 │ vLLM Servidor 1   │ │ vLLM Servidor 2   │
 │ TP=2 (48 GB VRAM) │ │ TP=2 (48 GB VRAM) │
 │ PVC: Disk-CH-1    │ │ PVC: Disk-CH-2    │
 └───────────────────┘ └───────────────────┘
```

---

## 3. Estructura del Repositorio

```text
/home/jsanchhi/PoCGPU/
├── README.md                           # Índice general y arquitectura consolidada
├── CONTEXTO_IA.md                      # Memoria técnica y operativa para agentes y orquestadores
├── 00_ARQUITECTURA_Y_PRINCIPIOS.md     # Fundamentos teóricos: Por qué fallan MIG, MPS y Time-Slicing
├── 01_VALIDACION_HARDWARE_Y_FABRIC.md  # Auditoría de interconexión NVLink/PCIe y NCCL
├── 02_STORAGE_Y_PESOS.md               # Gestión de Safetensors, cuotas VRAM y precarga
├── 03_DESPLIEGUE_MOTOR_VLLM_TP2.md     # Motor vLLM distribuido (TP=2) y Multi-LoRA
├── 04_ENTERPRISE_AI_GATEWAY.md         # Gateway L7 en CPU (LiteLLM/Envoy), auth y routing
├── 05_PRUEBAS_DE_CARGA_Y_BENCHMARK.md  # Protocolo de estrés, métricas TTFT/TPOT y Quality Gates
├── 06_GUIA_PRACTICA_POC_SATURACION.md  # Guía de campo: Dashboard web, API Keys y saturación
├── 07_VARIANTE_MINIMO_COSTE_SPOT_MISTRAL.md # Variante de coste optimizado con Spot y Mistral-7B
├── 08_ESTADO_ZURICH_Y_OPERACIONES.md   # Guía operativa: Hibernación, reactivación, credenciales y URLs
├── 09_MODELO_FINOPS_CALCULADORA.md     # Especificación FinOps: Sizing de hardware, Roofline y chargeback
├── 10_BACKLOG_FINOPS_INSTITUCIONAL.md  # Backlog técnico Tier-1: Primitivas neurosimbólicas y hoja de ruta
├── config/                             # Catálogos declarativos, taxonomías y localización (Cero Hardcoding)
│   ├── catalogs/                       # Catálogos de silicio, BOMs de chasis, modelos y multi-cloud pricing
│   │   ├── hardware_catalog.json       # Aceleradores H100, L4, A100, H200, B200, 4090, MI300X y chasis OEM
│   │   ├── models_catalog.json         # Arquitecturas Llama 3 (8B/70B/405B), DeepSeek V3 (671B), Mistral, Qwen
│   │   └── pricing_catalog.json        # Precios Spot/On-Demand GCP, AWS, Azure, RunPod y tasas FX JIT
│   ├── questionnaires/                 # Cuestionario estratégico de 5 dimensiones con pesos dinámicos
│   ├── taxonomies/                     # Taxonomía unificada de verticales de industria y frameworks regulatorios
│   └── locales.json                    # Registro simétrico i18n (EN/ES) desacoplado del código fuente
├── src/                                # Arquitectura Hexagonal Pura (100% Technical English)
│   ├── domain/                         # Núcleo de Dominio puro (Cero dependencias de framework/IO)
│   │   ├── models/                     # Entidades inmutables: Workload, Hardware, Financial, Assessment
│   │   ├── ports/                      # Puertos canónicos para registros, pricing, simulaciones y ledger
│   │   └── services/                   # 5 Motores de cálculo certificados (Roofline, Actuarial, TCO, Gate, Wizard)
│   ├── adapters/                       # Adaptadores de infraestructura (JSON loaders y Ledger SHA-256)
│   └── application/                    # Orquestador de aplicación FinOpsAdvisorService
├── tests/                              # Suite de pruebas automatizadas (70 tests pasando al 100%)
│   ├── architecture/                   # Compuertas AST de pureza de dominio y desacoplamiento lingüístico
│   ├── domain/                         # Pruebas unitarias y de propiedades matemáticas
│   ├── adapters/                       # Pruebas de integración de adaptadores y antimanipulación de ledger
│   └── integration/                    # Prueba end-to-end completa del flujo de asesoramiento FinOps
├── docs/                               # Documentación y gobernanza institucional
│   ├── RFC_063_UNIVERSAL_HYBRID_FINOPS_ADVISOR_ARGON.md # Master Blueprint: Universal Hybrid FinOps Advisor
│   ├── RFC_064_PHASE2_DOMAIN_SERVICES_SPECIFICATION_ARGON.md # Phase 2 Technical Specification
│   ├── RFC_065_ZERO_DEFECT_ZERO_HARDCODING_MASTER_PLAN_ARGON.md # Master Quality & Anti-Hardcoding Plan
│   ├── AUDIT_REPORT_PHASE1_ARGON.md    # Dictamen de auditoría de Fase 1 (100/100)
│   ├── AUDIT_REPORT_PHASE2_ARGON.md    # Dictamen de auditoría de Fase 2 (100/100)
│   ├── AUDIT_REPORT_PHASE3_ARGON.md    # Dictamen de auditoría de Fase 3 (98/100 Production Ready)
│   └── audit_screenshots/              # Evidencias fotográficas Playwright (1440px desktop y 375px móvil)
├── manifests/                          # Manifiestos YAML declarativos para Kubernetes
│   ├── 01_gpu_audit.yaml               # Pod de diagnóstico de hardware y topología NCCL
│   ├── 02_storage.yaml                 # PVC genérico y Job preloader de almacenamiento
│   ├── 02_storage_zurich.yaml          # PVC vinculado al disco persistente en Zúrich (Servidor 1)
│   ├── 02_storage_replica2.yaml        # PVC vinculado al disco persistente en Zúrich (Servidor 2)
│   ├── 03_vllm_service.yaml            # Deployment del Servidor 1 de vLLM (TP=2, 2x L4) + Service
│   ├── 03_vllm_replica2.yaml           # Deployment del Servidor 2 de vLLM (TP=2, 2x L4) + Service
│   ├── 04_gateway.yaml                 # Deployment de LiteLLM Gateway L7 + PostgreSQL + ConfigMap
│   ├── 05_linux_client.yaml            # Pod cliente Linux in-cluster para pruebas de baja latencia
│   ├── 06_openwebui.yaml               # Deployment de OpenWebUI + PVC de configuración
│   ├── 07_observability_and_alerts.yaml# Reglas de alerta Prometheus y exportadores vLLM
│   └── 08_grafana_prometheus.yaml      # Stack Prometheus + Grafana con dashboard preconfigurado
└── scripts/                            # Herramientas de automatización, tests y benchmarks
    ├── benchmark.py                    # Suite asíncrona de pruebas de carga con streaming
    ├── classify_incident.py            # Validador de inferencia de incidentes con LoRA
    ├── enrich_enterprise_metrics.py    # Generador de tráfico sintético para métricas en Grafana
    ├── finops_tier1_engine.py          # Motor FinOps Tier-1: Planificador de capacidad, Roofline y TCO
    ├── ide_copilot_simulator.py        # Simulador de peticiones concurrentes de IDE Continue.dev
    ├── interactive_chat.py             # Cliente CLI interactivo con métricas de streaming y TTFT
    ├── saturation_probe.py             # Sonda de saturación extrema de KV Cache y PagedAttention
    ├── seed_enterprise_demo.py         # Poblador de departamentos, cuotas y usuarios en PostgreSQL
    ├── simulate_enterprise_governance.py # Validador de políticas de cuota presupuestaria y RPM
    └── verify_balanced_saturation.py   # Verificador de balanceo de carga Activo-Activo entre réplicas
```

---

## 4. Secuencia de Operaciones

1. **Diseño y Fundamentos:** Consultar `00_ARQUITECTURA_Y_PRINCIPIOS.md` para el análisis de patologías descartadas (MIG, MPS, Time-Slicing).
2. **Reactivación / Despliegue:** Ejecutar los comandos de encendido y túneles detallados en `08_ESTADO_ZURICH_Y_OPERACIONES.md`.
3. **Poblado de Gobernanza:** Ejecutar `scripts/seed_enterprise_demo.py` para configurar los 6 departamentos con sus cuotas presupuestarias en la base de datos PostgreSQL.
4. **Verificación de Carga y Balanceo:** Comprobar la distribución Activo-Activo ejecutando `scripts/verify_balanced_saturation.py`.
5. **Observabilidad:** Auditar métricas de silicio, colas y costes en el dashboard de Grafana (`http://<IP>:8082`).
6. **Hibernación Segura:** Congelar el clúster a 0 nodos ($0.00/h de cómputo) siguiendo la sección 3.B de `08_ESTADO_ZURICH_Y_OPERACIONES.md`.
7. **Universal Hybrid FinOps Advisor Platform:** Iniciar el simulador web reactivo con compuerta CFO, dimensionamiento Roofline, riesgo actuarial y libro mayor SHA-256 ejecutando `python3 scripts/web_calculator.py` (accesible en `http://<IP>:8001`). Toda la suite de verificación automatizada se valida con `pytest tests/` y la auditoría visual se certifica con `python3 scripts/audit_playwright.py`.
