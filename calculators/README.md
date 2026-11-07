# Calculadoras FinOps para Inferencia LLM

Este directorio contiene las dos calculadoras independientes que gobiernan el ciclo de vida de inferencia de IA en la organización, junto con sus especificaciones matemáticas de referencia.

```text
calculators/
├── docs/                      # Especificaciones matemáticas y backlogs FinOps
│   ├── 09_MODELO_FINOPS_CALCULADORA.md
│   └── 10_BACKLOG_FINOPS_INSTITUCIONAL.md
├── sizing/                    # Calculadora A: Sizing y Física del Silicio (VRAM, Roofline, GPUs)
│   ├── README.md
│   ├── src/
│   └── tests/
└── chargeback/                # Calculadora B: Chargeback y TCO ($/Token, Amortización, Break-Even)
    ├── README.md
    ├── src/
    └── tests/
```

## Principio de Desacoplamiento

1. **Calculadora A (`sizing`):** Entrada = Demanda de tokens y concurrencia. Salida = Topología de hardware necesaria (nº GPUs, VRAM, servidores). Totalmente agnóstica de dinero o costes.
2. **Calculadora B (`chargeback`):** Entrada = Topología de hardware y parámetros de amortización/coste. Salida = TCO mensual, coste por millón de tokens y punto de equilibrio frente a APIs cloud.
3. Ambas calculadoras pueden ejecutarse de forma 100% aislada o encadenarse mediante contratos de intercambio estándar (JSON/DTO).
