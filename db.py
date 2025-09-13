import psycopg2
import logging

def get_connection():
    try:
        conn = psycopg2.connect(
            host="localhost",
            dbname="infra_manutencao",  # seu banco
            user="postgres",            # ajuste se for outro usuário
            password="banco3107",       # troque pela senha correta
            port=5432                   # padrão do PostgreSQL
        )
        logging.info("✅ Conexão com o banco bem sucedida")
        return conn
    except Exception as e:
        logging.error(f"❌ Erro ao conectar ao banco: {e}")
        raise