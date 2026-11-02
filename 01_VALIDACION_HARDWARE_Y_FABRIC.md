# 01. Validación de Hardware, Topología y Fabric Inter-GPU

## 1. Justificación Técnica: Por qué el Fabric es Crítico en TP=2
En un modelo configurado con `tensor_parallel_size: 2`, el cálculo matricial se descompone entre las dos GPUs. Cada capa Transformer requiere que ambas GPUs sincronicen sus resultados intermedios mediante una operación colectiva llamada `All-Reduce` (vía librería NCCL de NVIDIA).
- Si el ancho de banda es bajo ($< 20\text{ GB/s}$), las GPUs gastan la mayor parte del tiempo de ejecución esperando la transferencia de datos por el bus en vez de calcular tokens.
- Si las dos GPUs están en zócalos de CPU diferentes (NUMA crossing) sin NVLink, el tráfico debe atravesar el bus UPI/QPI de la placa base, introduciendo jitter de latencia severo.

---

## 2. Despliegue del Pod de Auditoría

Aplique el manifiesto de diagnóstico ubicado en `manifests/01_gpu_audit.yaml`:

```bash
kubectl apply -f /home/jsanchhi/PoCGPU/manifests/01_gpu_audit.yaml
```

Espere a que el Pod alcance el estado `Running`:
```bash
kubectl get pod gpu-fabric-audit -w
```

---

## 3. Procedimiento de Inspección y Comandos de Auditoría

Abra una sesión interactiva en el contenedor:
```bash
kubectl exec -it gpu-fabric-audit -- bash
```

### Paso 3.1: Verificación de Detección de Dispositivos y Drivers
Ejecute:
```bash
nvidia-smi
```
**Qué auditar:**
- Ambas GPUs deben listarse con el mismo modelo, versión de driver y capacidad de VRAM.
- Estado de persistencia (`Persistence-Mode`): Debe estar en `Enabled` en el host para evitar penalizaciones de latencia en la inicialización del driver CUDA.

### Paso 3.2: Matriz de Topología Inter-GPU
Ejecute:
```bash
nvidia-smi topo -m
```

**Interpretación de la Matriz:**
```text
        GPU0    GPU1    CPU Affinity    NUMA Affinity
GPU0     X      NV12    0-31            0
GPU1    NV12     X      0-31            0
```
- **NV12 / NV#:** NVLink directo. Máximo rendimiento ($\ge 300\text{ GB/s}$).
- **PIX:** Conexión PCIe a través de un único switch PCIe local (Óptimo para servidores sin NVLink, $\ge 25\text{ GB/s}$).
- **PXB:** Conexión PCIe atravesando switches PCIe intermedios sin cruzar CPU (Aceptable).
- **NODE / PHB:** Conexión a través del bus del host en el mismo zócalo CPU (Rendimiento medio).
- **SYS (NO ACEPTABLE EN PRODUCCIÓN TIER-1):** Conexión atravesando diferentes zócalos CPU (NUMA inter-socket). Provoca degradación del 40-70% en el rendimiento de TP=2.

### Paso 3.3: Benchmark de Transferencia Peer-to-Peer (P2P)
Compile y ejecute el test de ancho de banda y latencia CUDA:

```bash
cd /tmp
git clone --depth 1 https://github.com/NVIDIA/cuda-samples.git
cd cuda-samples/Samples/5_Domain_Specific/p2pBandwidthLatencyTest
make
./p2pBandwidthLatencyTest
```

**Métricas a registrar:**
1. **P2P Enabled:** Debe indicar `Yes` entre GPU0 y GPU1 para lectura y escritura.
2. **Bidirectional Bandwidth:**
   - Enlace PCIe Gen4 x16: Mínimo $24 - 28\text{ GB/s}$.
   - Enlace PCIe Gen5 x16: Mínimo $50 - 55\text{ GB/s}$.
   - NVLink (A100/H100): Mínimo $200 - 600\text{ GB/s}$.
3. **P2P Latency:** Debe ser inferior a $2.5\ \mu\text{s}$ en NVLink o $< 5\ \mu\text{s}$ en PCIe.

### Paso 3.4: Test Colectivo NCCL (Simulación exacta de TP=2)
Compile y corra el test de `all_reduce_perf`:

```bash
cd /tmp
git clone --depth 1 https://github.com/NVIDIA/nccl-tests.git
cd nccl-tests
make CUDA_HOME=/usr/local/cuda
./build/all_reduce_perf -b 8M -e 1G -f 2 -g 2
```

**Resultado esperado:**
La columna `algbw` (ancho de banda algorítmico) debe mantenerse estable en tamaños de tensor entre 64MB y 512MB (tamaño típico de tensores en capas Transformer durante inferencia por lotes).

---

## 4. Criterios de Aprobación para Pasar a la Fase 2

1. P2P Direct Memory Access confirmado entre GPU 0 y GPU 1.
2. Ancho de banda bidireccional NCCL $\ge 24\text{ GB/s}$.
3. Montaje de `/dev/shm` verificado como memoria compartida (POSIX shared memory) con un tamaño mínimo de 4GB a 8GB (requerido por PyTorch y NCCL para evitar fallos `SIGBUS`).

---

## 5. Limpieza del Pod de Diagnóstico

Una vez auditado el hardware:
```bash
kubectl delete pod gpu-fabric-audit
```
