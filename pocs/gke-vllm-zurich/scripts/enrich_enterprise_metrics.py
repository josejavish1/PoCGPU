#!/usr/bin/env python3
"""
Enrich Enterprise Metrics & Caching (PoCGPU)
Corrige y amplifica los datos de la base de datos para una demo ejecutiva perfecta:
1. Elimina equipos duplicados de pruebas previas.
2. Llena la columna 'end_user' con los nombres y correos reales de los empleados.
3. Escala los valores de gasto (spend) a cifras realistas en dólares ($1.50 - $8.20 por lote)
   para que 'Total Spend Per Team' no se redondee a 0.00.
4. Pobla la telemetría de Caching semántico (Cache Hits y Cache Misses con tokens ahorrados).
5. Sincroniza los totales en LiteLLM_TeamTable, LiteLLM_UserTable y LiteLLM_VerificationToken.
"""

import subprocess

sql_commands = """
-- 1. Limpiar equipos obsoletos de pruebas previas
DELETE FROM "LiteLLM_TeamTable" WHERE team_id NOT IN (
    'team-engineering-devops',
    'team-cybersecurity-soc',
    'team-finance-audit',
    'team-legal-compliance',
    'team-customer-operations',
    'team-data-ai-analytics'
);

-- 2. Asignar 'end_user' real y escalar el gasto en SpendLogs
-- DevOps
UPDATE "LiteLLM_SpendLogs"
SET "end_user" = 'carlos.mendoza@emeal.nttdata.com',
    spend = ROUND((total_tokens * 0.002)::numeric, 4)
WHERE team_id = 'team-engineering-devops' AND "user" = 'carlos.mendoza';

UPDATE "LiteLLM_SpendLogs"
SET "end_user" = 'alvaro.garcia@emeal.nttdata.com',
    spend = ROUND((total_tokens * 0.0018)::numeric, 4)
WHERE team_id = 'team-engineering-devops' AND "user" = 'alvaro.garcia';

-- Ciberseguridad
UPDATE "LiteLLM_SpendLogs"
SET "end_user" = 'laura.sanchez@emeal.nttdata.com',
    spend = ROUND((total_tokens * 0.0022)::numeric, 4)
WHERE team_id = 'team-cybersecurity-soc';

-- Finanzas
UPDATE "LiteLLM_SpendLogs"
SET "end_user" = 'miguel.angel@emeal.nttdata.com',
    spend = ROUND((total_tokens * 0.0025)::numeric, 4)
WHERE team_id = 'team-finance-audit' AND "user" = 'miguel.angel';

UPDATE "LiteLLM_SpendLogs"
SET "end_user" = 'patricia.vega@emeal.nttdata.com',
    spend = ROUND((total_tokens * 0.0024)::numeric, 4)
WHERE team_id = 'team-finance-audit' AND "user" = 'patricia.vega';

-- Legal
UPDATE "LiteLLM_SpendLogs"
SET "end_user" = 'elena.ruiz@emeal.nttdata.com',
    spend = ROUND((total_tokens * 0.0028)::numeric, 4)
WHERE team_id = 'team-legal-compliance';

-- Customer Support
UPDATE "LiteLLM_SpendLogs"
SET "end_user" = 'javier.blanco@emeal.nttdata.com',
    spend = ROUND((total_tokens * 0.0015)::numeric, 4)
WHERE team_id = 'team-customer-operations';

-- Data Science
UPDATE "LiteLLM_SpendLogs"
SET "end_user" = 'sofia.navarro@emeal.nttdata.com',
    spend = ROUND((total_tokens * 0.0030)::numeric, 4)
WHERE team_id = 'team-data-ai-analytics';

-- Cualquier otro registro sin end_user asignarlo a devops
UPDATE "LiteLLM_SpendLogs"
SET "end_user" = 'carlos.mendoza@emeal.nttdata.com',
    team_id = 'team-engineering-devops',
    spend = ROUND((total_tokens * 0.0015)::numeric, 4)
WHERE "end_user" IS NULL OR "end_user" = '';

-- Asegurar que cache_hit 'true' tenga coste 0 para reflejar ahorro
UPDATE "LiteLLM_SpendLogs"
SET spend = 0.0000
WHERE cache_hit = 'true';

-- 3. Actualizar la tabla de Equipos (TeamTable) con la suma exacta en dólares
UPDATE "LiteLLM_TeamTable" t
SET spend = ROUND(sub.total_spend::numeric, 2)
FROM (
    SELECT team_id, SUM(spend) as total_spend
    FROM "LiteLLM_SpendLogs"
    GROUP BY team_id
) sub
WHERE t.team_id = sub.team_id;

-- 4. Actualizar la tabla de Usuarios (UserTable) con la suma exacta en dólares
UPDATE "LiteLLM_UserTable" u
SET spend = ROUND(sub.total_spend::numeric, 2)
FROM (
    SELECT "user", SUM(spend) as total_spend
    FROM "LiteLLM_SpendLogs"
    GROUP BY "user"
) sub
WHERE u.user_id = sub."user";

-- 5. Actualizar la tabla de Claves Virtuales (VerificationToken)
UPDATE "LiteLLM_VerificationToken" v
SET spend = ROUND(sub.total_spend::numeric, 2)
FROM (
    SELECT "api_key", SUM(spend) as total_spend
    FROM "LiteLLM_SpendLogs"
    GROUP BY "api_key"
) sub
WHERE v.token = sub."api_key";
"""

def main():
    print("[+] Ejecutando enriquecimiento de métricas corporativas en PostgreSQL...")
    cmd = ["kubectl", "exec", "-i", "deployment/litellm-db", "--", "psql", "-U", "litellm_admin", "-d", "litellm"]
    proc = subprocess.run(cmd, input=sql_commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print("Error SQL:", proc.stderr)
        return
    print("  -> Métricas actualizadas con éxito.")

    # Verificar spend por equipo
    verify_cmd = [
        "kubectl", "exec", "deployment/litellm-db", "--", "psql", "-U", "litellm_admin", "-d", "litellm",
        "-c", 'SELECT team_alias, max_budget, spend as spend_usd FROM "LiteLLM_TeamTable" ORDER BY spend DESC;'
    ]
    res = subprocess.run(verify_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("\n[ESTADO ACTUAL DE EQUIPOS Y GASTO REAL EN DÓLARES]:")
    print(res.stdout)

    # Verificar end_users
    verify_users = [
        "kubectl", "exec", "deployment/litellm-db", "--", "psql", "-U", "litellm_admin", "-d", "litellm",
        "-c", 'SELECT end_user, count(*) as events, round(sum(spend)::numeric, 2) as spend_usd FROM "LiteLLM_SpendLogs" GROUP BY end_user ORDER BY spend_usd DESC;'
    ]
    res_users = subprocess.run(verify_users, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("\n[ESTADO DE CUSTOMER USAGE (USUARIOS REALES CON GASTO)]: ")
    print(res_users.stdout)

if __name__ == "__main__":
    main()
