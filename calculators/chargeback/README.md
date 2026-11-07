# Calculadora B: Chargeback y TCO Empresarial (Unit Economics)

Calculadora independiente para la evaluación económica de inferencia LLM, Total Cost of Ownership (TCO) fully loaded y tarificación por token.

## Responsabilidad de Dominio

- **TCO Fully Loaded:** Cómputo del coste total de propiedad incluyendo hardware, energía, refrigeración (PUE), espacio de centro de datos y amortización.
- **Tarifario $/1M Tokens:** Desglose asimétrico de costes para tokens de entrada (Prefill), tokens de salida (Decode) y tokens cacheados (Prompt Caching).
- **Análisis de Break-Even:** Umbral de concurrencia y volumen de tokens donde la inferencia privada es más rentable que el consumo vía API cloud comercial.
- **Chargeback Departamental:** Asignación presupuestaria y gobernanza multi-inquilino.

## Desacoplamiento

Esta calculadora consume como entrada una topología de hardware dimensionada (generada por la Calculadora A o especificada manualmente) junto con políticas de amortización y pools de costes. No contiene lógica de paralelismo de tensores ni cálculo de VRAM a nivel de silicio.

## Referencias

- Especificación matemática: `calculators/docs/09_MODELO_FINOPS_CALCULADORA.md` (Sección 3).
- Catálogos de precios: `config/catalogs/pricing_catalog.json`.
- Módulo del motor canónico: `pocgpu.domain.tco`, `pocgpu.domain.economics` y `pocgpu.application.economics_service`.
