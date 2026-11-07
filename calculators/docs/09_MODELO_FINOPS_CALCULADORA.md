# 09_MODELO_FINOPS_CALCULADORA.md: Especificación Matemática de Sizing y Chargeback LLM

> **DOCUMENTO DE GOBERNANZA TIER-1 / FINOPS DE INFERENCIA**  
> Modelo analítico de dos fases para el dimensionamiento de hardware silicio (Capacidad) y economía unitaria por token (Chargeback/TCO), alineado con las metodologías de **SemiAnalysis (InferenceX)**, **vLLM PagedAttention** y **Databricks MosaicML**.

---

## 1. El Paradigma FinOps: Desacoplamiento de Cómputo y Tráfico

En arquitecturas empresariales modernas de inferencia privada, el coste de infraestructura no debe abordarse como un problema de encendido/apagado por petición. Gracias al runtime unificado con **Multi-LoRA y PagedAttention**, el modelo base permanece inmutable en memoria y los adaptadores específicos se inyectan a coste cero de VRAM adicional.

El sistema se gobierna mediante dos calculadoras independientes:

```
                      [ DEMANDA EMPRESARIAL ]
           (Parámetros, Precisión, Contexto, Concurrencia)
                                 │
                                 ▼
                 ┌───────────────────────────────┐
                 │    CALCULADORA A: SIZING      │
                 │   (La Física del Silicio)     │
                 └───────────────┬───────────────┘
                                 │
                                 ▼
                     [ TOPOLOGÍA HARDWARE ]
             (Nº GPUs, VRAM, TP/PP, Coste $/Hora)
                                 │
                                 ▼
                 ┌───────────────────────────────┐
                 │   CALCULADORA B: CHARGEBACK   │
                 │   (La Economía del Negocio)   │
                 └───────────────┬───────────────┘
                                 │
                                 ▼
                   [ TARIFARIO $/1M TOKENS ]
         (Input, Output Asimétrico, Cache, Break-Even)
```

---

## 2. Calculadora A: Sizing y Física del Silicio (Roofline Model)

### A. Memoria Estática de Pesos ($M_{weights}$)
$$M_{weights} = \frac{P_{total} \times 10^9 \times B_{precision}}{1024^3} \quad [\text{GB}]$$
- **FP16 / BF16:** $B_{precision} = 2.0$ bytes/parámetro.
- **FP8 / INT8:** $B_{precision} = 1.0$ byte/parámetro.
- **INT4 / AWQ / GPTQ:** $B_{precision} = 0.55$ bytes/parámetro (incluye escalas y ceros).

### B. Memoria Dinámica de KV Cache con Grouped-Query Attention ($M_{kv}$)
La arquitectura Transformer moderna reduce drásticamente el KV Cache agrupando cabezas ($H_{kv} \ll H_q$). El consumo por cada token individual acumulado en todas las capas es:
$$\text{Bytes/Token} = 2 \times L \times H_{kv} \times d_{head} \times B_{kv}$$
Donde $2$ representa los tensores de Keys y Values, $L$ es el número de capas, $d_{head}$ la dimensión de cabeza y $B_{kv}$ la precisión de caché (FP16=2.0, FP8=1.0).

El buffer elástico total requerido bajo pico de tráfico es:
$$M_{kv} = \frac{\text{Concurrencia} \times \text{Contexto\_Máximo} \times \text{Bytes/Token}}{1024^3} \quad [\text{GB}]$$

### C. Sobrecarga de Activaciones y Reserva CUDA ($M_{total}$)
Durante el forward pass, los buffers intermedios y el runtime CUDA consumen memoria transitoria:
$$M_{act} \approx M_{weights} \times 0.08 \times \log_2(\text{Concurrencia})$$
$$M_{total} = M_{weights} + M_{kv} + M_{act}$$

### D. Selección de Silicio y Topología Distribuida
El número de GPUs necesarias respeta la reserva de seguridad de vLLM (`gpu_memory_utilization = 0.90`):
$$\text{GPUs}_{\text{raw}} = \left\lceil \frac{M_{total}}{\text{VRAM}_{\text{GPU}} \times 0.90} \right\rceil$$

Se ajusta a potencias de 2 para **Tensor Parallelism ($TP$)**:
- Si $\text{GPUs} \le 8 \rightarrow TP = \text{GPUs}, PP = 1$.
- Si $\text{GPUs} > 8 \rightarrow TP = 8, PP = \lceil \text{GPUs}/8 \rceil$.

### E. Latencia Roofline (SLA Simulado)
- **Prefill (Compute-Bound / TTFT):**
  $$\text{TTFT (s)} = \frac{2 \times P_{active} \times \text{Tokens}_{prompt}}{\text{TFLOPS}_{cluster} \times \text{MFU} \times \text{Bus\_Factor}}$$
- **Decode (Memory-Bandwidth Bound / TPOT):**
  $$\text{TPOT (s/tok)} = \frac{M_{weights} + M_{kv\_active}}{\text{Bandwidth}_{cluster} \times \text{Bus\_Factor}}$$
  $$\text{Throughput Agregado} = \frac{\text{Concurrencia}}{\text{TPOT}} \quad [\text{tokens/s}]$$

---

## 3. Calculadora B: FinOps, TCO y Facturación Asimétrica (Chargeback)

### A. TCO Real con Ventana de Hibernación (Duty Cycle)
En entornos corporativos reales, el cómputo solo opera en horario laboral (11h/día, 22 días/mes = 242 h/mes frente a 730 h continuas):
$$\text{Horas}_{\text{activas}} = \begin{cases} 242 \text{ h/mes} & \text{Con Hibernación (\$0/h en valles)} \\ 730 \text{ h/mes} & \text{24/7 Continuo} \end{cases}$$

$$\text{TCO Mensual} = (\text{Coste}_{\text{GPU/h}} \times \text{Horas}_{\text{activas}}) + (\text{Coste}_{\text{CPU\_Mgmt}} \times \text{Horas}_{\text{activas}}) + \text{Storage}_{\text{SSD}} + \text{Egress}$$

### B. Capacidad Productiva Mensual
Considerando un factor de utilización real del **30%** (picos de ráfaga y pausas entre lecturas de usuarios):
$$\text{Tokens}_{\text{mes}} = \text{Throughput Agregado} \times (\text{Horas}_{\text{activas}} \times 3600) \times \text{Utilización (0.30)}$$

### C. Tarificación Asimétrica (Penalización de Ancho de Banda)
Generar un token de salida (decode) satura el bus de memoria y cuesta **3x más silicio** que procesar un token de entrada (prefill). En un tráfico corporativo estándar (ratio 3:1 input:output):
$$U_{ponderadas} = (Tokens_{mes} \times 0.75 \times 1.0) + (Tokens_{mes} \times 0.25 \times 3.0)$$
$$\text{Coste Base Input (1M)} = \frac{\text{TCO Mensual}}{U_{ponderadas}} \times 10^6$$
$$\text{Coste Base Output (1M)} = 3.0 \times \text{Coste Base Input (1M)}$$
$$\text{Coste Prompt Caching (1M)} = 0.20 \times \text{Coste Base Input (1M)} \quad (\text{80\% descuento por Cache Hit})$$

### D. Tarifa Departamental Billed (+Margen)
$$\text{Tarifa} = \text{Coste Base} \times (1 + \text{Margen})$$

### E. Punto de Equilibrio (Break-Even) vs Frontier APIs (OpenAI / Anthropic)
Compara el TCO del clúster frente a una factura equivalente en GPT-4o ($2.50 input / $10.00 output = $4.375/1M ponderado):
$$\text{Tokens Break-Even} = \frac{\text{TCO Mensual}}{\$4.375 / 10^6}$$
*Por debajo de este volumen, la API pública es más barata; por encima, el clúster privado genera ahorro neto acumulativo.*

---

## 4. Arquitectura de Implementación y Consumo

El modelo se implementa mediante dos motores desacoplados en el paquete canónico `pocgpu` y sus interfaces en `calculators/`:

- **Calculadora A (`calculators/sizing`):** Implementada en `pocgpu.domain.capacity` y `pocgpu.application.capacity_orchestrator`. Resuelve la física del silicio, límites de VRAM, KV Cache y concurrencia máxima.
- **Calculadora B (`calculators/chargeback`):** Implementada en `pocgpu.domain.tco`, `pocgpu.domain.economics` y `pocgpu.application.economics_service`. Resuelve la amortización fully-loaded, el coste por millón de tokens y el punto de equilibrio frente a APIs comerciales.

*(Nota: El script legacy `finops_tier1_engine.py` fue migrado y sustituido por esta arquitectura modular bajo la Constitución de Ingeniería).*
