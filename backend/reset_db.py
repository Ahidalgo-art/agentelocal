import psycopg2

try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='Go8VNm4X',
        database='postgres'
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Terminar conexiones activas a la BD
    cursor.execute("""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = 'agente_local'
        AND pid <> pg_backend_pid()
    """)
    
    # Eliminar BD
    cursor.execute('DROP DATABASE IF EXISTS agente_local')
    print('BD agente_local eliminada')
    
    # Crear BD limpia
    cursor.execute('CREATE DATABASE agente_local')
    print('✅ BD agente_local recreada limpia')
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ Error: {e}')
