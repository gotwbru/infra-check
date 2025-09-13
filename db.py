import psycopg2
import os
import logging

def get_connection():
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        logging.info("✅ Conexão com o banco bem sucedida")
        return conn
    except Exception as e:
        logging.error(f"❌ Erro ao conectar ao banco: {e}")
        raise
