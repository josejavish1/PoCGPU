# 09_MODELO_FINOPS_CALCULADORA.md

## Abordaje Estructural del Problema FinOps en LLMs

La estimación de costes en IA Generativa se divide en dos vectores matemáticos independientes. La complejidad de "cargar y descargar modelos on-demand" se anula gracias a la arquitectura **Multi-LoRA + PagedAttention** de este clúster: el modelo base se carga una única vez (coste fijo de VRAM) y los adaptadores se inyectan en milisegundos sin coste adicional significativo. 

Por tanto, el problema pasa de ser estocástico a determinista.

---

### Calculadora A: Sizing (Dimensionamiento de Hardware)
**Objetivo:** Determinar cuántas GPUs necesitas partiendo de los requisitos del negocio.

**Variables de Entrada (Business Requirements):**
1. **Parámetros del Modelo Base (B):** Ej. 7 (Mistral), 32 (Qwen), 70 (Llama).
2. **Precisión (Q):** 16 bits (FP16/BF16) o 8/4 bits (Quantizado).
3. **Ventana de Contexto Máxima (C):** Ej. 8192 tokens.
4. **Usuarios Concurrentes Máximos (U):** Peticiones simultáneas en el pico.

**Cálculo de VRAM Necesaria:**
1. **VRAM Pesos (Estático):** `(B * 10^9) * (Q / 8) / 1024^3` GB.
   *Ejemplo Mistral 7B FP16:* `7 * 2 = 14 GB`.
2. **VRAM KV Cache (Dinámico):** `(C * U) * (2 * NumLayers * NumHeads * HeadDim) * 2 bytes / 1024^3` GB.
   *Aprox:* 1 GB por cada 4000 tokens concurrentes (en modelos 7B).
3. **VRAM Total:** `(Pesos + KV Cache) * 1.2` (20% margen seguridad CUDA).

**Salida:** Número de tarjetas L4 (24GB), A10G (24GB) o A100 (80GB) requeridas, y su coste cloud por hora.

---

### Calculadora B: Chargeback (Facturación al Usuario)
**Objetivo:** Determinar a cuánto cobrar el bloque de 1 Millón de Tokens (1M Tokens) para rentabilizar la infraestructura.

**Variables de Entrada (Infra Ops):**
1. **Coste Infraestructura Mensual (CI):** Nodos GPU + Nodos CPU + Discos ($/mes).
2. **Utilización Efectiva (Ut):** % de tiempo que las GPUs están procesando (ej. 30%).
3. **Throughput Promedio de la GPU (Th):** Tokens/segundo reales (ej. 680 tok/s en PoCGPU).
4. **Margen de Beneficio (M):** % de markup comercial.

**Cálculo del Precio por Token (PPT):**
1. **Capacidad Productiva Mensual (Tokens):** `Th * 3600 * 24 * 30 * Ut`
   *Ejemplo (680 tok/s al 30% util):* ~528 Millones de tokens al mes.
2. **Coste Crudo por 1M Tokens (Break-Even):** `(CI / Capacidad Productiva) * 1,000,000`.
3. **Precio de Venta por 1M Tokens:** `Coste Crudo * (1 + M)`.

**Salida:** Tarifario (Pricing) exacto en dólares por cada 1M tokens a inyectar en la base de datos de LiteLLM para facturar a los departamentos.
