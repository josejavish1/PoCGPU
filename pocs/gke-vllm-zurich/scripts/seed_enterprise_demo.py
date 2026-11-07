#!/usr/bin/env python3
"""
Seed Enterprise Demo Generator (PoCGPU)
Inyecta datos corporativos realistas para una demo ejecutiva completa:
1. 6 Departamentos / Áreas (Teams) con cuotas y políticas de modelos.
2. 8 Empleados corporativos con correo @emeal.nttdata.com y claves API individuales.
3. ~350 transacciones históricas en PostgreSQL (LiteLLM_SpendLogs) en los últimos 14 días.
4. Telemetría de caché semántica (~20% Cache Hit Rate).
5. Desglose multi-modelo (Coding Agent, Reasoning Math, Mistral Base y Gemini Cloud Bursting).
6. Sincronización de usuarios en OpenWebUI para el directorio corporativo.
"""

import sys
import json
import random
import uuid
from datetime import datetime, timedelta
import subprocess

# Configuración de los 6 Departamentos Corporativos
TEAMS = [
    {
        "team_id": "team-engineering-devops",
        "team_alias": "Ingeniería de Software & DevOps",
        "max_budget": 150.0,
        "models": ["light-model-coder", "light-model-fast", "reasoning-model"],
        "rpm_limit": 120,
        "tpm_limit": 200000
    },
    {
        "team_id": "team-cybersecurity-soc",
        "team_alias": "Ciberseguridad & SOC",
        "max_budget": 80.0,
        "models": ["reasoning-model", "light-model-fast"],
        "rpm_limit": 60,
        "tpm_limit": 100000
    },
    {
        "team_id": "team-finance-audit",
        "team_alias": "Finanzas, Riesgos & Auditoría",
        "max_budget": 60.0,
        "models": ["reasoning-model", "light-model-fast"],
        "rpm_limit": 30,
        "tpm_limit": 50000
    },
    {
        "team_id": "team-legal-compliance",
        "team_alias": "Legal & Licitaciones Públicas",
        "max_budget": 50.0,
        "models": ["reasoning-model", "light-model-fast"],
        "rpm_limit": 30,
        "tpm_limit": 50000
    },
    {
        "team_id": "team-customer-operations",
        "team_alias": "Atención al Cliente & Operaciones",
        "max_budget": 90.0,
        "models": ["light-model-fast", "gemini-cloud-backup"],
        "rpm_limit": 80,
        "tpm_limit": 120000
    },
    {
        "team_id": "team-data-ai-analytics",
        "team_alias": "Data Science & Advanced Analytics",
        "max_budget": 120.0,
        "models": ["light-model-coder", "reasoning-model", "gemini-cloud-backup"],
        "rpm_limit": 90,
        "tpm_limit": 150000
    }
]

# Configuración de Empleados Corporativos
USERS = [
    {"user_id": "carlos.mendoza", "name": "Carlos Mendoza", "email": "carlos.mendoza@emeal.nttdata.com", "team": "team-engineering-devops", "role": "DevOps Tech Lead"},
    {"user_id": "laura.sanchez", "name": "Laura Sánchez", "email": "laura.sanchez@emeal.nttdata.com", "team": "team-cybersecurity-soc", "role": "Senior SOC Analyst"},
    {"user_id": "miguel.angel", "name": "Miguel Ángel García", "email": "miguel.angel@emeal.nttdata.com", "team": "team-finance-audit", "role": "Finance Controller"},
    {"user_id": "elena.ruiz", "name": "Elena Ruiz", "email": "elena.ruiz@emeal.nttdata.com", "team": "team-legal-compliance", "role": "Senior Legal Counsel"},
    {"user_id": "javier.blanco", "name": "Javier Blanco", "email": "javier.blanco@emeal.nttdata.com", "team": "team-customer-operations", "role": "Operations Manager"},
    {"user_id": "sofia.navarro", "name": "Sofía Navarro", "email": "sofia.navarro@emeal.nttdata.com", "team": "team-data-ai-analytics", "role": "Lead Data Scientist"},
    {"user_id": "alvaro.garcia", "name": "Álvaro García", "email": "alvaro.garcia@emeal.nttdata.com", "team": "team-engineering-devops", "role": "Senior Backend Architect"},
    {"user_id": "patricia.vega", "name": "Patricia Vega", "email": "patricia.vega@emeal.nttdata.com", "team": "team-finance-audit", "role": "Risk & Compliance Auditor"}
]

# Modelos disponibles y costes simulados (por 1k tokens)
MODELS_SPECS = {
    "coding-agent": {"cost_per_1k": 0.0004, "share": 0.40, "tags": ["ide-copilot", "refactoring", "unit-tests"]},
    "reasoning-math": {"cost_per_1k": 0.0006, "share": 0.25, "tags": ["legal-review", "financial-forecast", "risk-assessment"]},
    "mistral-base": {"cost_per_1k": 0.0002, "share": 0.20, "tags": ["general-qa", "email-draft", "summarization"]},
    "gemini-2.5-flash": {"cost_per_1k": 0.0008, "share": 0.15, "tags": ["cloud-bursting", "peak-hours-overflow", "multimodal"]}
}

def generate_sql_for_postgres():
    sql_lines = []

    # 1. Inyectar o actualizar Equipos (LiteLLM_TeamTable)
    for t in TEAMS:
        models_arr = "ARRAY[" + ",".join([f"'{m}'" for m in t["models"]]) + "]"
        sql = f"""
        INSERT INTO "LiteLLM_TeamTable" (team_id, team_alias, max_budget, spend, models, rpm_limit, tpm_limit, blocked, members_with_roles, admins, members, metadata)
        VALUES ('{t["team_id"]}', '{t["team_alias"]}', {t["max_budget"]}, 0.0, {models_arr}, {t["rpm_limit"]}, {t["tpm_limit"]}, false, '[{{"role": "admin", "user_id": "default_user_id"}}]'::jsonb, '{{}}'::text[], '{{}}'::text[], '{{}}'::jsonb)
        ON CONFLICT (team_id) DO UPDATE SET
            team_alias = EXCLUDED.team_alias,
            max_budget = EXCLUDED.max_budget,
            models = EXCLUDED.models,
            rpm_limit = EXCLUDED.rpm_limit,
            tpm_limit = EXCLUDED.tpm_limit;
        """
        sql_lines.append(sql.strip())

    # 2. Inyectar Usuarios y Claves Virtuales (LiteLLM_UserTable y LiteLLM_VerificationToken)
    tokens_map = {}
    for u in USERS:
        token_hash = hashlib_token = str(uuid.uuid4()).replace("-", "")
        token_preview = f"sk-{u['user_id'][:8]}-{token_hash[:6]}"
        tokens_map[u["user_id"]] = token_hash

        # UserTable
        sql_user = f"""
        INSERT INTO "LiteLLM_UserTable" (user_id, user_alias, user_email, team_id, user_role, max_budget, spend)
        VALUES ('{u["user_id"]}', '{u["name"]}', '{u["email"]}', '{u["team"]}', 'user', 50.0, 0.0)
        ON CONFLICT (user_id) DO UPDATE SET
            user_alias = EXCLUDED.user_alias,
            user_email = EXCLUDED.user_email,
            team_id = EXCLUDED.team_id;
        """
        sql_lines.append(sql_user.strip())

        # VerificationToken
        sql_token = f"""
        INSERT INTO "LiteLLM_VerificationToken" (token, key_name, key_alias, user_id, team_id, max_budget, spend)
        VALUES ('{token_hash}', '{token_preview}', '{u["name"]} (Corporate IDE/API)', '{u["user_id"]}', '{u["team"]}', 50.0, 0.0)
        ON CONFLICT (token) DO UPDATE SET
            key_alias = EXCLUDED.key_alias,
            user_id = EXCLUDED.user_id,
            team_id = EXCLUDED.team_id;
        """
        sql_lines.append(sql_token.strip())

    # 3. Generar ~360 Registros Históricos de Consumo (LiteLLM_SpendLogs) en los últimos 14 días
    now = datetime.utcnow()
    total_spend_by_team = {t["team_id"]: 0.0 for t in TEAMS}
    total_spend_by_user = {u["user_id"]: 0.0 for u in USERS}
    total_spend_by_token = {t_hash: 0.0 for t_hash in tokens_map.values()}

    model_choices = []
    for m, spec in MODELS_SPECS.items():
        model_choices.extend([m] * int(spec["share"] * 100))

    for day_offset in range(13, -1, -1):
        day_date = now - timedelta(days=day_offset)
        # Actividad mayor en días laborables (25 a 35 llamadas diarias)
        num_calls = random.randint(22, 38) if day_date.weekday() < 5 else random.randint(6, 12)

        for _ in range(num_calls):
            hour = random.randint(8, 19) if day_date.weekday() < 5 else random.randint(10, 16)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            call_time = day_date.replace(hour=hour, minute=minute, second=second)

            user = random.choice(USERS)
            token_hash = tokens_map[user["user_id"]]
            team_id = user["team"]
            model = random.choice(model_choices)
            spec = MODELS_SPECS[model]

            prompt_tokens = random.randint(120, 850)
            completion_tokens = random.randint(45, 450)
            total_tokens = prompt_tokens + completion_tokens

            # Caching semántico simulado: 18% de las peticiones fueron Cache Hits
            is_cache_hit = random.random() < 0.18
            cache_hit_str = "true" if is_cache_hit else "false"
            cache_key_str = f"cache:{uuid.uuid4().hex[:16]}" if is_cache_hit else None

            # Coste proporcional
            spend = (total_tokens / 1000.0) * spec["cost_per_1k"]
            if is_cache_hit:
                spend = 0.0 # Cache hits ahorran coste

            total_spend_by_team[team_id] += spend
            total_spend_by_user[user["user_id"]] += spend
            total_spend_by_token[token_hash] += spend

            req_id = f"req-{uuid.uuid4().hex[:12]}"
            tag = random.choice(spec["tags"])
            tags_json = json.dumps([tag, "poc-enterprise"])

            cache_key_sql = f"'{cache_key_str}'" if cache_key_str else "NULL"

            sql_log = f"""
            INSERT INTO "LiteLLM_SpendLogs" (
                request_id, call_type, api_key, spend, total_tokens, prompt_tokens, completion_tokens,
                "startTime", "endTime", model, "user", team_id, cache_hit, cache_key, request_tags
            ) VALUES (
                '{req_id}', 'chat.completion', '{token_hash}', {spend:.6f}, {total_tokens}, {prompt_tokens}, {completion_tokens},
                '{call_time.strftime("%Y-%m-%d %H:%M:%S")}', '{(call_time + timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S")}',
                '{model}', '{user["user_id"]}', '{team_id}', '{cache_hit_str}', {cache_key_sql}, '{tags_json}'::jsonb
            );
            """
            sql_lines.append(sql_log.strip())

    # 4. Actualizar totales de spend acumulados en TeamTable y UserTable
    for team_id, spend in total_spend_by_team.items():
        sql_lines.append(f"UPDATE \"LiteLLM_TeamTable\" SET spend = {spend:.4f} WHERE team_id = '{team_id}';")

    for user_id, spend in total_spend_by_user.items():
        sql_lines.append(f"UPDATE \"LiteLLM_UserTable\" SET spend = {spend:.4f} WHERE user_id = '{user_id}';")

    for token_hash, spend in total_spend_by_token.items():
        sql_lines.append(f"UPDATE \"LiteLLM_VerificationToken\" SET spend = {spend:.4f} WHERE token = '{token_hash}';")

    return "\n".join(sql_lines)

def sync_openwebui_users():
    """Sincroniza los usuarios corporativos en la base de datos de OpenWebUI."""
    print("[+] Sincronizando directorio corporativo en OpenWebUI (webui.db)...")
    py_code = """
import sqlite3, time, uuid

conn = sqlite3.connect('/app/backend/data/webui.db')
c = conn.cursor()

# Obtener hash de contraseña existente para clonarlo
admin_pwd = c.execute("SELECT password FROM auth LIMIT 1").fetchone()
default_pwd_hash = admin_pwd[0] if admin_pwd else "$2b$12$CiralBeXBcAaUgutCm"

users_data = [
    ("carlos.mendoza", "Carlos Mendoza", "carlos.mendoza@emeal.nttdata.com", "DevOps Tech Lead"),
    ("laura.sanchez", "Laura Sánchez", "laura.sanchez@emeal.nttdata.com", "Senior SOC Analyst"),
    ("miguel.angel", "Miguel Ángel García", "miguel.angel@emeal.nttdata.com", "Finance Controller"),
    ("elena.ruiz", "Elena Ruiz", "elena.ruiz@emeal.nttdata.com", "Senior Legal Counsel"),
    ("javier.blanco", "Javier Blanco", "javier.blanco@emeal.nttdata.com", "Operations Manager"),
    ("sofia.navarro", "Sofía Navarro", "sofia.navarro@emeal.nttdata.com", "Lead Data Scientist"),
    ("alvaro.garcia", "Álvaro García", "alvaro.garcia@emeal.nttdata.com", "Senior Backend Architect"),
    ("patricia.vega", "Patricia Vega", "patricia.vega@emeal.nttdata.com", "Risk & Compliance Auditor")
]

now = int(time.time())
for uid, name, email, role_bio in users_data:
    existing = c.execute("SELECT id FROM user WHERE email = ?", (email,)).fetchone()
    if not existing:
        new_id = str(uuid.uuid4())
        c.execute('''
            INSERT INTO user (id, name, email, role, profile_image_url, last_active_at, updated_at, created_at, bio)
            VALUES (?, ?, ?, 'user', '/user.png', ?, ?, ?, ?)
        ''', (new_id, name, email, now, now, now, role_bio))
        
        c.execute('''
            INSERT INTO auth (id, email, password, active)
            VALUES (?, ?, ?, 1)
        ''', (new_id, email, default_pwd_hash))

conn.commit()
print("Usuarios corporativos dados de alta en OpenWebUI con exito.")
"""
    cmd = ["kubectl", "exec", "deployment/open-webui", "--", "python3", "-c", py_code]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(res.stdout)

def main():
    print("=" * 75)
    print("INICIANDO GENERACIÓN DE DATOS DE DEMO EMPRESARIAL REALISTA (VÍA C+)")
    print("=" * 75)

    print("[+] Generando lote de transacciones históricas y estructura de gobernanza...")
    sql_payload = generate_sql_for_postgres()

    print("[+] Inyectando 6 departamentos, 8 usuarios y ~350 registros en PostgreSQL...")
    cmd = ["kubectl", "exec", "-i", "deployment/litellm-db", "--", "psql", "-U", "litellm_admin", "-d", "litellm"]
    proc = subprocess.run(cmd, input=sql_payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print(f"Error al ejecutar SQL: {proc.stderr[:300]}")
        sys.exit(1)
    print("  -> PostgreSQL actualizado con éxito en el disco persistente.")

    # Sincronizar directorio en OpenWebUI
    sync_openwebui_users()

    print("\n" + "=" * 75)
    print("DEMO EMPRESARIAL CONFIGURADA Y DISPONIBLE AL 100%")
    print("=" * 75)
    print("1. En LiteLLM Dashboard (http://34.175.194.93:8080/ui/):")
    print("   - Pestaña 'Teams': 6 departamentos con presupuestos, gastos acumulados y RPMs.")
    print("   - Pestaña 'Virtual Keys': Claves corporativas asignadas a los empleados.")
    print("   - Pestaña 'Usage': Curvas históricas de los últimos 14 días con desglose por modelo y cache hits.")
    print("2. En OpenWebUI (http://34.175.194.93):")
    print("   - Directorio de usuarios activos con correos corporativos @emeal.nttdata.com.")
    print("=" * 75)

if __name__ == "__main__":
    main()
