#!/usr/bin/env python3
"""
Calculadora FinOps para Modelos LLM Privados (PoCGPU)
Implementa el marco teórico del documento 09_MODELO_FINOPS_CALCULADORA.md
"""
import math

def calculate_sizing():
    print("\n--- CALCULADORA A: DIMENSIONAMIENTO (SIZING) ---")
    b = float(input("Parámetros del Modelo Base (Billones, ej. 7, 32, 70): ") or 7)
    q = int(input("Precisión en bits (ej. 16 para FP16, 4 para INT4): ") or 16)
    c = int(input("Ventana de contexto máxima en tokens (ej. 8192): ") or 8192)
    u = int(input("Usuarios concurrentes máximos en pico (ej. 20): ") or 20)

    # VRAM Pesos Estáticos
    # (B * 10^9) * (Q / 8) / 1024^3
    vram_pesos = (b * 1e9) * (q / 8) / (1024**3)
    
    # VRAM KV Cache Dinámico (Aproximación empírica para Mistral/Llama)
    # Asumimos ~1.2 MB por cada 1000 tokens en 7B FP16, escala linealmente con parámetros
    kv_cache_per_1k = 1.2 * (b / 7) * (q / 16)
    vram_kv_cache = ((c * u) / 1000) * kv_cache_per_1k / 1024

    vram_total_gbs = (vram_pesos + vram_kv_cache) * 1.2 # 20% Overhead CUDA

    print(f"\n[+] VRAM para Pesos del Modelo (Inmutable): {vram_pesos:.2f} GB")
    print(f"[+] VRAM para KV Cache (Sujeto a PagedAttention): {vram_kv_cache:.2f} GB")
    print(f"[+] VRAM Total Requerida (con 20% margen): {vram_total_gbs:.2f} GB")

    gpus_l4 = math.ceil(vram_total_gbs / 24)
    print(f"[*] Hardware Sugerido: {gpus_l4}x NVIDIA L4 (24GB c/u)")

def calculate_chargeback():
    print("\n--- CALCULADORA B: FACTURACIÓN A DEPARTAMENTOS (CHARGEBACK) ---")
    ci = float(input("Coste mensual de infraestructura en USD (ej. 850): ") or 850)
    ut = float(input("Utilización efectiva promedio (%) (ej. 30): ") or 30) / 100.0
    th = float(input("Throughput promedio empírico (tokens/segundo) (ej. 680): ") or 680)
    m = float(input("Margen de beneficio comercial (%) (ej. 20): ") or 20) / 100.0

    # Capacidad productiva en 1 mes (30 días)
    seconds_per_month = 3600 * 24 * 30
    total_tokens_month = th * seconds_per_month * ut

    if total_tokens_month == 0:
        print("Error: El throughput o la utilización no pueden ser 0.")
        return

    # Coste Break-Even
    cost_per_token = ci / total_tokens_month
    cost_per_1m_tokens = cost_per_token * 1_000_000
    sell_price_per_1m = cost_per_1m_tokens * (1 + m)

    print(f"\n[+] Capacidad Productiva Mensual (con util={ut*100}%): {total_tokens_month / 1e6:.2f} Millones de Tokens")
    print(f"[+] Coste Base por 1M Tokens (Break-Even): ${cost_per_1m_tokens:.4f}")
    print(f"[*] Precio Sugerido por 1M Tokens (con margen): ${sell_price_per_1m:.4f}")
    print("\n* Configura este precio en la tabla LiteLLM_TeamTable de PostgreSQL.")

if __name__ == "__main__":
    print("========================================")
    print(" CALCULADORA FINOPS TIER-1 (PoCGPU) ")
    print("========================================")
    calculate_sizing()
    print("-" * 40)
    calculate_chargeback()
    print("========================================")
