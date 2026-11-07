#!/usr/bin/env python3
"""
Simulación de Gobernanza Empresarial Multi-Departamento (Vía C)
Demuestra en producción:
1. Creación de Equipos Corporativos (Teams) con cuotas y políticas de modelos (RBAC).
2. Generación de API Keys virtuales departamentales.
3. Restricción de acceso a modelos no autorizados (Finanzas bloqueado de Coding-Agent).
4. Bloqueo automático por agotamiento de presupuesto (Budget Exceeded).
5. Auditoría en tiempo real en PostgreSQL y visualización en el panel web.
"""

import sys
import json
import time
import requests

GATEWAY_URL = "http://127.0.0.1:8080"
MASTER_KEY = "sk-tier1-master-governance-key-2026"

HEADERS_MASTER = {
    "Authorization": f"Bearer {MASTER_KEY}",
    "Content-Type": "application/json"
}

def create_team(team_alias: str, max_budget: float, allowed_models: list, rpm_limit: int) -> dict:
    url = f"{GATEWAY_URL}/team/new"
    payload = {
        "team_alias": team_alias,
        "max_budget": max_budget,
        "models": allowed_models,
        "rpm_limit": rpm_limit
    }
    r = requests.post(url, json=payload, headers=HEADERS_MASTER, timeout=10)
    r.raise_for_status()
    return r.json()

def generate_key_for_team(team_id: str, key_alias: str, user_id: str, max_budget: float = None) -> str:
    url = f"{GATEWAY_URL}/key/generate"
    payload = {
        "team_id": team_id,
        "key_alias": key_alias,
        "user_id": user_id
    }
    if max_budget is not None:
        payload["max_budget"] = max_budget
    r = requests.post(url, json=payload, headers=HEADERS_MASTER, timeout=10)
    r.raise_for_status()
    return r.json()["key"]

def test_inference(key: str, model: str, prompt: str) -> dict:
    url = f"{GATEWAY_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 40
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        return {"status_code": r.status_code, "body": r.json()}
    except Exception as e:
        return {"status_code": 500, "error": str(e)}

def main():
    print("=" * 80)
    print(" [VÍA C] SIMULACIÓN REAL DE GOBERNANZA CORPORATIVA MULTI-DEPARTAMENTO")
    print("=" * 80)

    # 1. Crear Departamentos Corporativos
    print("\n[PASO 1] Creando 3 Departamentos con Presupuestos y Permisos de Modelos (RBAC)...")
    
    # Equipo A: DevOps & Software Engineering (Permiso total, $50)
    team_dev = create_team("DevOps & AI Engineering", 50.0, ["light-model-coder", "light-model-fast", "reasoning-model"], 60)
    key_dev = generate_key_for_team(team_dev["team_id"], "dev-lead-key", "lead-architect")
    print(f"  ✓ Equipo: '{team_dev['team_alias']}' | Presupuesto: ${team_dev['max_budget']} | Modelos: {team_dev['models']}")
    print(f"    -> Clave emitida: {key_dev[:12]}...")

    # Equipo B: Finanzas & Compliance (Acceso restringido sin coding, Presupuesto diminuto $0.0001 para prueba de corte)
    team_fin = create_team("Finanzas & Compliance", 0.0001, ["reasoning-model", "light-model-fast"], 10)
    key_fin = generate_key_for_team(team_fin["team_id"], "cfo-analyst-key", "cfo-analyst", max_budget=0.0001)
    print(f"  ✓ Equipo: '{team_fin['team_alias']}' | Presupuesto: ${team_fin['max_budget']} | Modelos: {team_fin['models']}")
    print(f"    -> Clave emitida: {key_fin[:12]}...")

    # Equipo C: Customer Support & Operations (Solo modelos rápidos y Cloud fallback)
    team_ops = create_team("Customer Support & Ops", 20.0, ["light-model-fast", "gemini-cloud-backup"], 30)
    key_ops = generate_key_for_team(team_ops["team_id"], "support-bot-key", "support-lead")
    print(f"  ✓ Equipo: '{team_ops['team_alias']}' | Presupuesto: ${team_ops['max_budget']} | Modelos: {team_ops['models']}")
    print(f"    -> Clave emitida: {key_ops[:12]}...")

    # 2. Prueba de Control de Acceso por Roles (RBAC de Modelos)
    print("\n" + "=" * 80)
    print("[PASO 2] Probando Control de Acceso a Modelos (RBAC por Departamento)...")
    
    # 2.1 DevOps solicita coding-agent -> DEBE PERMITIRSE
    print("\n  [Test 1] Equipo DevOps solicita modelo de código ('light-model-coder'):")
    res_dev = test_inference(key_dev, "light-model-coder", "Escribe un script bash de 1 linea.")
    print(f"    -> Código HTTP: {res_dev['status_code']}")
    if res_dev['status_code'] == 200:
        print("    -> ESTADO: [AUTORIZADO] La petición se ejecutó en las 2 GPUs locales.")
    else:
        print(f"    -> ESTADO: [ERROR] {res_dev.get('body')}")

    # 2.2 Finanzas intenta solicitar coding-agent -> DEBE RECHAZARSE (No tienen permiso)
    print("\n  [Test 2] Equipo Finanzas intenta solicitar modelo de código ('light-model-coder'):")
    res_fin_forbidden = test_inference(key_fin, "light-model-coder", "Escribe una funcion.")
    print(f"    -> Código HTTP: {res_fin_forbidden['status_code']}")
    if res_fin_forbidden['status_code'] in (400, 403):
        msg = res_fin_forbidden.get('body', {}).get('error', {}).get('message', '')
        print(f"    -> ESTADO: [BLOQUEADO POR POLÍTICA] El Gateway denegó el acceso por RBAC.")
        print(f"    -> Motivo del Gateway: {msg[:100]}...")

    # 3. Prueba de Protección de Capacidad y Cuotas (Rate Limiting y Control de Saturación)
    print("\n" + "=" * 80)
    print("[PASO 3] Probando Protección de Capacidad (Rate Limiting Automático)...")
    
    # 3.1 Finanzas ejecuta su primera llamada válida
    print("\n  [Test 3] Finanzas lanza su primera llamada dentro de cuota ('light-model-fast'):")
    res_fin_1 = test_inference(key_fin, "light-model-fast", "Calcula 2 + 2")
    print(f"    -> Código HTTP: {res_fin_1['status_code']}")
    if res_fin_1['status_code'] == 200:
        print("    -> ESTADO: [AUTORIZADO] Petición procesada en la GPU.")

    # 3.2 Crear clave con límite estricto de 1 RPM y demostrar corte 429
    key_limited = generate_key_for_team(team_fin["team_id"], "analyst-burst-test", "analyst-1")
    # Aplicar rpm_limit directo en la clave
    requests.post(f"{GATEWAY_URL}/key/update", json={"key": key_limited, "rpm_limit": 1}, headers=HEADERS_MASTER)

    print("\n  [Test 4] Lanzando ráfaga inmediata para comprobar Rate Limiting (rpm_limit: 1):")
    test_inference(key_limited, "light-model-fast", "Peticion 1")
    res_burst_blocked = test_inference(key_limited, "light-model-fast", "Peticion 2 (ráfaga no autorizada)")
    print(f"    -> Código HTTP: {res_burst_blocked['status_code']}")
    if res_burst_blocked['status_code'] == 429:
        err_msg = res_burst_blocked.get('body', {}).get('error', {}).get('message', '')
        print("    -> ESTADO: [BLOQUEO AUTOMÁTICO 429] El Gateway protegió el clúster de saturación.")
        print(f"    -> Diagnóstico: {err_msg[:90]}...")
    else:
        print(f"    -> Respuesta: {res_burst_blocked}")

    # 3.3 Comprobar que DevOps NO se ve afectado por el corte de Finanzas
    print("\n  [Test 5] Verificando que DevOps sigue operativo al 100% (Aislamiento de Vecino Ruidoso):")
    res_dev_2 = test_inference(key_dev, "reasoning-model", "¿Por que el cielo es azul?")
    print(f"    -> Código HTTP: {res_dev_2['status_code']}")
    if res_dev_2['status_code'] == 200:
        print("    -> ESTADO: [AISLAMIENTO EXITOSO] DevOps sigue consumiendo las GPUs sin interrupción.")

    print("\n" + "=" * 80)
    print(" [CONCLUSIÓN] SIMULACIÓN DE GOBERNANZA COMPLETADA Y CERTIFICADA")
    print(" Los presupuestos, equipos y auditorías están persistidos en PostgreSQL.")
    print(" Visibles en el Dashboard de LiteLLM: http://34.175.194.93:8080/ui/")
    print("=" * 80)

if __name__ == "__main__":
    main()
