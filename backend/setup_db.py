import os
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
    
    cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', ('agente_local',))
    if cursor.fetchone():
        print('✅ BD agente_local ya existe')
    else:
        cursor.execute('CREATE DATABASE agente_local')
        print('✅ BD agente_local creada')
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ Error: {e}')
