# 02. Estrategia de Almacenamiento y Gestión de Pesos de Modelos

## 1. El Cuello de Botella de E/S en Inferencia LLM
El peso de un modelo de 32 mil millones de parámetros (32B) en precisión completa (BF16) ocupa aproximadamente $65\text{ GB}$. En un despliegue de producción:
- **Anti-Patrón:** Descargar los pesos desde Internet (Hugging Face) en el contenedor de inferencia en cada reinicio. Esto satura el ancho de banda del cluster, genera arranques en frío de 15 a 30 minutos y provoca que los `LivenessProbe` maten el Pod por timeout.
- **Estándar Tier-1:** Desacoplar el almacenamiento de pesos en volúmenes compartidos persistentes de alto rendimiento (NVMe Local, Ceph RBD o GCS Fuse) y cargarlos en GPU usando mapeo de memoria `mmap` con formato **Safetensors**.

---

## 2. Formato de Pesos y Cuantización para 2 GPUs

### Presupuesto de VRAM según el Hardware Disponible:

| Hardware | VRAM Total (2 GPUs) | Modelo Base Recomendado | Formato / Precisión | VRAM Pesos | VRAM Libre para KV Cache (Tokens) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2x NVIDIA L4 (24GB c/u)** | 48 GB | Qwen-2.5-32B-Instruct | AWQ (4-bit) | ~19 GB (9.5 GB/GPU) | **~29 GB** ($\sim 120.000$ tokens concurrentes) |
| **2x NVIDIA A100 (80GB c/u)** | 160 GB | Qwen-2.5-32B-Instruct | BF16 (16-bit nativo) | ~65 GB (32.5 GB/GPU) | **~95 GB** ($\sim 400.000$ tokens concurrentes) |

**Por qué Safetensors es obligatorio:**
1. **Seguridad (Cero Ejecución de Código Arbitrario):** A diferencia de los ficheros `.bin` o `.pt` basados en `pickle` de Python, Safetensors es un formato binario inmutable sin vectores de deserialización de código malicioso.
2. **Zero-Copy Memory Mapping (`mmap`):** Permite al motor de inferencia transferir los tensores desde el almacenamiento directamente a la memoria de la GPU sin serializarlos en la memoria RAM del contenedor.

---

## 3. Topología de Almacenamiento: GCP vs On-Premise

### En Google Cloud Platform (GCP):
1. **Opción A (Recomendada para Pilotos/Producción rápida):** Persistent Disk SSD (`pd-ssd` o `pd-extreme`) montado con `ReadWriteOnce`. Ofrece latencias de lectura sostenidas de $> 400\text{ MB/s}$.
2. **Opción B (Escala multi-nodo):** Cloud Storage FUSE CSI Driver con flag `--file-cache:max-size-mb` para mantener una caché local en los SSD efímeros del nodo.

### En On-Premise:
1. **Opción A (Máximo Rendimiento):** Local Persistent Volume (Local PV) aprovisionado directamente sobre discos NVMe locales del servidor (U.2 o PCIe directos). Rendimiento de lectura de $3.5\text{ GB/s}$ a $7\text{ GB/s}$, permitiendo arranques en frío de menos de 10 segundos.
2. **Opción B:** Ceph RBD montado sobre red de almacenamiento dedicada (100GbE RoCEv2/iWARP).

---

## 4. Despliegue del Almacenamiento y Pre-Carga de Pesos

Aplique el manifiesto de volumen y el Job de precarga ubicado en `manifests/02_storage.yaml`:

```bash
kubectl apply -f /home/jsanchhi/PoCGPU/manifests/02_storage.yaml
```

Supervise el progreso de la precarga:
```bash
kubectl logs -f job/llm-weights-preloader
```

Una vez que el Job finalice con estado `Completed`:
```bash
kubectl get jobs
```
Los pesos del modelo de razonamiento y las carpetas para adaptadores LoRA ligeros quedarán consolidados en el volumen `/models_cache` listos para ser consumidos inmediatamente por el motor vLLM.

---

## 5. Compatibilidad Estructural de Tensores en Adaptadores LoRA

En modelos Transformer, las matrices de un adaptador LoRA deben coincidir exactamente con las dimensiones de la arquitectura base:
- `Qwen-2.5-32B` tiene una dimensión oculta (`hidden_size`) de **5120** y **64 capas**.
- Si se intenta montar un adaptador LoRA entrenado para otro modelo (ej. Llama-7B con dimensión 4096 y 32 capas), el motor vLLM fallará en el arranque con un error de discrepancia de dimensiones (`RuntimeError: shape mismatch`).
- El Job de precarga (`manifests/02_storage.yaml`) descarga los pesos base de Qwen-2.5-32B y sintetiza automáticamente adaptadores LoRA compatibles con las dimensiones exactas ($5120 \times 8$), permitiendo validar la arquitectura multi-modelo de inmediato sin requerir un entrenamiento previo.
