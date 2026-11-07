# Calculadora A: Sizing y Física del Silicio (Silicon Capacity)

Calculadora independiente para el dimensionamiento de hardware, memoria VRAM, KV Cache paginado y límites de throughput bajo el modelo Roofline.

## Responsabilidad de Dominio

- **Física del Silicio:** Cálculo estático de pesos ($M_{weights}$) según parámetros y cuantización (FP16, BF16, FP8, INT4).
- **KV Cache Dinámico:** Asignación de memoria para Grouped-Query Attention (GQA) en función de la longitud de contexto y concurrencia.
- **Modelo Roofline:** Determinación del régimen operativo (Memory-Bound vs Compute-Bound) y saturación de ancho de banda de memoria (HBM/GDDR).
- **Topología de Nodos:** Empaquetado en GPUs discretas respetando dominios de fallo (N+k) y Tensor/Pipeline Parallelism (TP/PP).

## Desacoplamiento

Esta calculadora opera exclusivamente sobre leyes físicas y arquitecturas de hardware. No tiene conocimiento de costes financieros, márgenes ni divisas monetarias. Su salida es una topología de hardware recomendada con especificaciones de capacidad útil.

## Referencias

- Especificación matemática: `calculators/docs/09_MODELO_FINOPS_CALCULADORA.md` (Sección 2).
- Catálogos de hardware: `config/catalogs/hardware_catalog.json`.
- Módulo del motor canónico: `pocgpu.domain.capacity` y `pocgpu.application.capacity_orchestrator`.
