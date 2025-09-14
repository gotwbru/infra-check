import psycopg2
import os

# Pega a URL do banco do Render (Environment Variable DATABASE_URL)
DATABASE_URL = os.environ.get("DATABASE_URL")

# Script de criação das tabelas
CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL,
    papel VARCHAR(20) NOT NULL,
    ativo BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS chamados (
    id SERIAL PRIMARY KEY,
    loja_id INT NOT NULL,
    descricao TEXT NOT NULL,
    prioridade VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'aberto',
    solicitado_por VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Inserts iniciais de usuários
INSERT_USUARIOS = """
INSERT INTO usuarios (username, password, papel, ativo) VALUES
('GERENTE', '$2b$12$9H2UC2IollLqiHhu/FxLheIrxs52yIuYnbBPWt3P7ZclIsoU3NmKC', 'gerente', TRUE),
('FISCAL',  '$2b$12$sh7yWWNJLb1GWIyU6V/FH.mxaDcc/pyzLP0WI81s9g7d1b3yzR4cK', 'fiscal', TRUE),
('ADMIN',   '$2b$12$8VGYLMO.Igngq/Js29J9YeKYzJdLAqfV4ZE2hrJE5i4/stPnVQfli', 'admin', TRUE)
ON CONFLICT (username) DO NOTHING;
"""

# Inserts de chamados de exemplo
INSERT_CHAMADOS = """
INSERT INTO chamados (id, loja_id, descricao, prioridade, status, solicitado_por, criado_em, atualizado_em) VALUES
(1, 1, 'Ar-condicionado da sala de vendas não está gelando', 'alta', 'aberto', 'Ana Souza', '2025-09-12 15:55:39.403196', '2025-09-12 15:55:39.403196'),
(2, 3, 'Lâmpada queimada no estoque', 'baixa', 'aberto', 'Carlos Mendes', '2025-09-12 15:55:39.403196', '2025-09-12 15:55:39.403196'),
(4, 7, 'Vazamento na pia do banheiro', 'média', 'aberto', 'Ricardo Oliveira', '2025-09-12 15:55:39.403196', '2025-09-12 15:55:39.403196'),
(6, 2, 'Teste de funcionamento', 'média', 'aberto', 'Bruna Pedroso', '2025-09-13 19:09:40.644092', '2025-09-13 19:09:40.644092'),
(7, 6, 'Manutenção da escada', 'média', 'aberto', 'Bruna Pedroso', '2025-09-13 19:53:49.709166', '2025-09-13 19:53:49.709166')
ON CONFLICT (id) DO NOTHING;
"""

def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("✅ Conectado ao banco")

        # Cria tabelas
        cur.execute(CREATE_TABLES)
        print("📦 Tabelas criadas/verificadas")

        # Insere usuários padrão
        cur.execute(INSERT_USUARIOS)
        print("👤 Usuários inseridos (se não existirem)")

        # Insere chamados exemplo
        cur.execute(INSERT_CHAMADOS)
        print("📋 Chamados de exemplo inseridos (se não existirem)")

        conn.commit()
        cur.close()
        conn.close()
        print("🎉 Banco inicializado com sucesso")

    except Exception as e:
        print(f"❌ Erro ao inicializar o banco: {e}")

if __name__ == "__main__":
    init_db()
