from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
import jwt
import os
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

# Configurações
SECRET_KEY = os.getenv("JWT_SECRET", "chave_super_secreta")  # definida no .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hora

# Configuração do bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Funções para senha ---
def gerar_hash(senha: str) -> str:
    """Gera o hash da senha para salvar no banco"""
    return pwd_context.hash(senha)

def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """Compara senha digitada com o hash do banco"""
    return pwd_context.verify(senha, hash_armazenado)

# --- Funções para JWT ---
def criar_token(dados: dict, expira_em: Optional[int] = None):
    """Gera um token JWT"""
    to_encode = dados.copy()
    if expira_em:
        exp = datetime.utcnow() + timedelta(minutes=expira_em)
    else:
        exp = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": exp})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def validar_token(token: str):
    """Valida e decodifica um token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expirado
    except jwt.PyJWTError:
        return None  # Token inválido
