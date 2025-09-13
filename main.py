from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from auth import criar_token
from db import get_connection

app = FastAPI()

# Configuração de templates e arquivos estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================================================
# SUPORTE A PWA (Manifest + Service Worker)
# ==========================================================

# Rota para expor o service worker na raiz
@app.get("/sw.js")
def sw_alias():
    return FileResponse("static/service-worker.js", media_type="application/javascript")

# ==========================================================
# Lista fixa de lojas
# ==========================================================
LOJAS_FIXAS = [
    {"id": 1, "nome": "LOJA 01"},
    {"id": 2, "nome": "LOJA 03"},
    {"id": 3, "nome": "LOJA 06"},
    {"id": 4, "nome": "LOJA 09"},
    {"id": 5, "nome": "LOJA 10"},
    {"id": 6, "nome": "LOJA 11"},
    {"id": 7, "nome": "LOJA 12"},
    {"id": 8, "nome": "LOJA 14"},
]

# ==========================================================
# Rotas API de teste
# ==========================================================
@app.get("/health")
def health():
    return {"status": "ok"}

# ==========================================================
# Rotas HTML (Login / Root)
# ==========================================================
@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/login-page")

@app.get("/login-page", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login-page", response_class=HTMLResponse)
async def login_action(request: Request, role: str = Form(...)):
    try:
        if role == "ADMIN":
            return RedirectResponse(url="/admin-code", status_code=302)

        if role == "GERENTE":
            return RedirectResponse(url="/dashboard-gerente", status_code=302)

        if role == "FISCAL":
            return RedirectResponse(url="/dashboard-fiscal", status_code=302)

        return RedirectResponse(url="/dashboard", status_code=302)

    except Exception:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Erro no servidor"})

# ==========================================================
# Tela de código para Admin
# ==========================================================
@app.get("/admin-code", response_class=HTMLResponse)
async def admin_code_page(request: Request):
    return templates.TemplateResponse("admin_code.html", {"request": request, "error": None})

@app.post("/admin-code", response_class=HTMLResponse)
async def admin_code_action(request: Request, code: str = Form(...)):
    ADMIN_SECRET = "BRUNA123"

    if code == ADMIN_SECRET:
        token = criar_token({"sub": "ADMIN", "papel": "admin"})
        return RedirectResponse(url="/dashboard-admin", status_code=302)
    else:
        return templates.TemplateResponse("admin_code.html", {"request": request, "error": "Código inválido"})

# ==========================================================
# Dashboard genérico
# ==========================================================
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, usuario: str = "Visitante"):
    return templates.TemplateResponse("dashboard.html", {"request": request, "usuario": usuario})

# ==========================================================
# ROTAS DE CHAMADOS (Gerente)
# ==========================================================
class ChamadoCreate(BaseModel):
    loja_id: int
    descricao: str
    prioridade: str
    solicitado_por: str

# Criar um chamado
@app.post("/chamados/gerente")
def criar_chamado(chamado: ChamadoCreate):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO chamados (loja_id, descricao, prioridade, solicitado_por, status, criado_em, atualizado_em)
        VALUES (%s, %s, %s, %s, 'aberto', NOW(), NOW())
        RETURNING id;
    """, (chamado.loja_id, chamado.descricao, chamado.prioridade, chamado.solicitado_por))

    chamado_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    loja_nome = next((l["nome"] for l in LOJAS_FIXAS if l["id"] == chamado.loja_id), "Loja desconhecida")

    return {
        "message": "Chamado criado com sucesso",
        "chamado": {
            "id": chamado_id,
            "loja": loja_nome,
            "descricao": chamado.descricao,
            "prioridade": chamado.prioridade,
            "status": "aberto",
            "solicitado_por": chamado.solicitado_por,
        }
    }

# Listar chamados
@app.get("/chamados/gerente")
def listar_chamados():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, loja_id, descricao, prioridade, status, solicitado_por, criado_em, atualizado_em
        FROM chamados
        ORDER BY criado_em DESC;
    """)

    chamados = cur.fetchall()
    conn.close()

    resultado = [
        {
            "id": c[0],
            "loja": next((l["nome"] for l in LOJAS_FIXAS if l["id"] == c[1]), f"Loja {c[1]}"),
            "descricao": c[2],
            "prioridade": c[3],
            "status": c[4],
            "solicitado_por": c[5],
            "criado_em": c[6],
            "atualizado_em": c[7],
        }
        for c in chamados
    ]

    return {"chamados": resultado}

# Concluir chamado
@app.put("/chamados/{chamado_id}/concluir")
def concluir_chamado(chamado_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, loja_id, status FROM chamados WHERE id = %s;", (chamado_id,))
    chamado = cur.fetchone()

    if not chamado:
        conn.close()
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if chamado[2] == "concluído":
        conn.close()
        return {"message": "Chamado já estava concluído"}

    cur.execute("""
        UPDATE chamados
        SET status = 'concluído', atualizado_em = NOW()
        WHERE id = %s;
    """, (chamado_id,))
    conn.commit()
    conn.close()

    loja_nome = next((l["nome"] for l in LOJAS_FIXAS if l["id"] == chamado[1]), f"Loja {chamado[1]}")

    return {
        "message": "Chamado concluído com sucesso",
        "chamado": {
            "id": chamado[0],
            "loja": loja_nome,
            "status": "concluído"
        }
    }

# ==========================================================
# ROTAS DE CHAMADOS (Fiscal)
# ==========================================================

@app.get("/chamados/fiscal")
def listar_chamados_fiscal():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, loja_id, descricao, prioridade, status, solicitado_por, criado_em, atualizado_em
        FROM chamados
        ORDER BY 
            CASE 
                WHEN prioridade = 'alta' THEN 1
                WHEN prioridade = 'média' THEN 2
                WHEN prioridade = 'baixa' THEN 3
                ELSE 4
            END,
            criado_em DESC;
    """)

    chamados = cur.fetchall()
    conn.close()

    resultado = [
        {
            "id": c[0],
            "loja": next((l["nome"] for l in LOJAS_FIXAS if l["id"] == c[1]), f"Loja {c[1]}"),
            "descricao": c[2],
            "prioridade": c[3],
            "cor": "vermelho" if c[3].lower() == "alta" else "amarelo" if c[3].lower() == "média" else "verde",
            "status": c[4],
            "solicitado_por": c[5],
            "criado_em": c[6],
            "atualizado_em": c[7],
        }
        for c in chamados
    ]

    return {"chamados": resultado}

@app.put("/chamados/{chamado_id}/visualizar")
def visualizar_chamado(chamado_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, loja_id, status FROM chamados WHERE id = %s;", (chamado_id,))
    chamado = cur.fetchone()

    if not chamado:
        conn.close()
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    cur.execute("""
        UPDATE chamados
        SET status = 'visualizado', atualizado_em = NOW()
        WHERE id = %s AND status != 'concluído';
    """, (chamado_id,))
    conn.commit()
    conn.close()

    loja_nome = next((l["nome"] for l in LOJAS_FIXAS if l["id"] == chamado[1]), f"Loja {chamado[1]}")

    return {
        "message": "Chamado visualizado com sucesso",
        "chamado": {
            "id": chamado[0],
            "loja": loja_nome,
            "status": "visualizado"
        }
    }

# ==========================================================
# FRONTEND GERENTE
# ==========================================================

@app.get("/dashboard-gerente", response_class=HTMLResponse)
async def dashboard_gerente(request: Request):
    return templates.TemplateResponse("dashboard_gerente.html", {"request": request})

@app.get("/gerente/abrir-chamado", response_class=HTMLResponse)
async def abrir_chamado_form(request: Request):
    return templates.TemplateResponse("chamado_form.html", {"request": request, "lojas": LOJAS_FIXAS})

@app.post("/gerente/abrir-chamado", response_class=HTMLResponse)
async def abrir_chamado_action(request: Request, loja_id: int = Form(...), descricao: str = Form(...), prioridade: str = Form(...), solicitado_por: str = Form(...)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO chamados (loja_id, descricao, prioridade, solicitado_por, status, criado_em, atualizado_em)
        VALUES (%s, %s, %s, %s, 'aberto', NOW(), NOW());
    """, (loja_id, descricao, prioridade, solicitado_por))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/gerente/listar-chamados", status_code=302)

@app.get("/gerente/listar-chamados", response_class=HTMLResponse)
async def listar_chamados_gerente(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, loja_id, descricao, prioridade, status, solicitado_por
        FROM chamados
        ORDER BY criado_em DESC;
    """)
    chamados = [
        {
            "id": c[0],
            "loja": next((l["nome"] for l in LOJAS_FIXAS if l["id"] == c[1]), f"Loja {c[1]}"),
            "descricao": c[2],
            "prioridade": c[3],
            "status": c[4],
            "solicitado_por": c[5],
        }
        for c in cur.fetchall()
    ]
    conn.close()
    return templates.TemplateResponse("chamado_list.html", {"request": request, "chamados": chamados})

@app.post("/gerente/concluir/{chamado_id}", response_class=HTMLResponse)
async def concluir_chamado_front(request: Request, chamado_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE chamados SET status = 'concluído', atualizado_em = NOW() WHERE id = %s;", (chamado_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/gerente/listar-chamados", status_code=302)

# ==========================================================
# FRONTEND FISCAL
# ==========================================================

@app.get("/dashboard-fiscal", response_class=HTMLResponse)
async def dashboard_fiscal(request: Request):
    return templates.TemplateResponse("dashboard_fiscal.html", {"request": request})


@app.get("/fiscal/listar-chamados", response_class=HTMLResponse)
async def listar_chamados_fiscal_front(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, loja_id, descricao, prioridade, status, solicitado_por
        FROM chamados
        ORDER BY 
            CASE 
                WHEN prioridade = 'alta' THEN 1
                WHEN prioridade = 'média' THEN 2
                WHEN prioridade = 'baixa' THEN 3
                ELSE 4
            END,
            criado_em DESC;
    """)
    chamados = [
        {
            "id": c[0],
            "loja": next((l["nome"] for l in LOJAS_FIXAS if l["id"] == c[1]), f"Loja {c[1]}"),
            "descricao": c[2],
            "prioridade": c[3].strip().lower() if c[3] else None,  # 🔴 força minúsculo
            "status": c[4],
            "solicitado_por": c[5],
        }
        for c in cur.fetchall()
    ]
    conn.close()
    return templates.TemplateResponse("fiscal_list.html", {"request": request, "chamados": chamados})


@app.post("/fiscal/visualizar/{chamado_id}", response_class=HTMLResponse)
async def visualizar_chamado_front(request: Request, chamado_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE chamados
        SET status = 'visualizado', atualizado_em = NOW()
        WHERE id = %s AND status != 'concluído';
    """, (chamado_id,))
    conn.commit()

    # Recarregar lista de chamados
    cur.execute("""
        SELECT id, loja_id, descricao, prioridade, status, solicitado_por
        FROM chamados
        ORDER BY 
            CASE 
                WHEN prioridade = 'alta' THEN 1
                WHEN prioridade = 'média' THEN 2
                WHEN prioridade = 'baixa' THEN 3
                ELSE 4
            END,
            criado_em DESC;
    """)
    chamados = [
        {
            "id": c[0],
            "loja": next((l["nome"] for l in LOJAS_FIXAS if l["id"] == c[1]), f"Loja {c[1]}"),
            "descricao": c[2],
            "prioridade": c[3].strip().lower() if c[3] else None,  # 🔴 força minúsculo
            "status": c[4],
            "solicitado_por": c[5],
        }
        for c in cur.fetchall()
    ]
    conn.close()

    # Enviar mensagem para o template
    return templates.TemplateResponse(
        "fiscal_list.html",
        {
            "request": request,
            "chamados": chamados,
            "mensagem": f"Chamado #{chamado_id} visualizado com sucesso ✅"
        }
    )


@app.post("/fiscal/concluir/{chamado_id}", response_class=HTMLResponse)
async def concluir_chamado_fiscal_front(request: Request, chamado_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE chamados
        SET status = 'concluído', atualizado_em = NOW()
        WHERE id = %s;
    """, (chamado_id,))
    conn.commit()

    # Recarregar lista para mostrar feedback
    cur.execute("""
        SELECT id, loja_id, descricao, prioridade, status, solicitado_por
        FROM chamados
        ORDER BY 
            CASE 
                WHEN prioridade = 'alta' THEN 1
                WHEN prioridade = 'média' THEN 2
                WHEN prioridade = 'baixa' THEN 3
                ELSE 4
            END,
            criado_em DESC;
    """)
    chamados = [
        {
            "id": c[0],
            "loja": next((l["nome"] for l in LOJAS_FIXAS if l["id"] == c[1]), f"Loja {c[1]}"),
            "descricao": c[2],
            "prioridade": c[3].strip().lower() if c[3] else None,  # 🔴 força minúsculo
            "status": c[4],
            "solicitado_por": c[5],
        }
        for c in cur.fetchall()
    ]
    conn.close()

    return templates.TemplateResponse(
        "fiscal_list.html",
        {
            "request": request,
            "chamados": chamados,
            "mensagem": f"Chamado #{chamado_id} concluído com sucesso ✅"
        }
    )

# ==========================================================
# FRONTEND ADMIN
# ==========================================================

@app.get("/dashboard-admin", response_class=HTMLResponse)
async def dashboard_admin(request: Request):
    return templates.TemplateResponse("dashboard_admin.html", {"request": request})


@app.get("/admin/listar-chamados", response_class=HTMLResponse)
async def listar_chamados_admin(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, loja_id, descricao, prioridade, status, solicitado_por
        FROM chamados
        ORDER BY criado_em DESC;
    """)
    chamados = [
        {
            "id": c[0],
            "loja": next((l["nome"] for l in LOJAS_FIXAS if l["id"] == c[1]), f"Loja {c[1]}"),
            "descricao": c[2],
            "prioridade": c[3],
            "status": c[4],
            "solicitado_por": c[5],
        }
        for c in cur.fetchall()
    ]
    conn.close()
    return templates.TemplateResponse("admin_list.html", {"request": request, "chamados": chamados})


# --- Tela de edição ---
@app.get("/admin/editar/{chamado_id}", response_class=HTMLResponse)
async def editar_chamado_form(request: Request, chamado_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, loja_id, descricao, prioridade, status, solicitado_por
        FROM chamados
        WHERE id = %s;
    """, (chamado_id,))
    c = cur.fetchone()
    conn.close()

    if not c:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    chamado = {
        "id": c[0],
        "loja": next((l["nome"] for l in LOJAS_FIXAS if l["id"] == c[1]), f"Loja {c[1]}"),
        "descricao": c[2],
        "prioridade": c[3],
        "status": c[4],
        "solicitado_por": c[5],
    }

    return templates.TemplateResponse("admin_edit.html", {"request": request, "chamado": chamado})


# --- Ação de edição ---
@app.post("/admin/editar/{chamado_id}", response_class=HTMLResponse)
async def editar_chamado_action(
    request: Request,
    chamado_id: int,
    descricao: str = Form(...),
    prioridade: str = Form(...),
    status: str = Form(...)
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE chamados
        SET descricao = %s, prioridade = %s, status = %s, atualizado_em = NOW()
        WHERE id = %s;
    """, (descricao, prioridade, status, chamado_id))
    conn.commit()
    conn.close()

    return RedirectResponse(url="/admin/listar-chamados", status_code=302)


# --- Concluir chamado ---
@app.post("/admin/concluir/{chamado_id}", response_class=HTMLResponse)
async def concluir_chamado_admin(request: Request, chamado_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE chamados
        SET status = 'concluído', atualizado_em = NOW()
        WHERE id = %s AND status != 'concluído';
    """, (chamado_id,))
    conn.commit()
    conn.close()

    return RedirectResponse(url="/admin/listar-chamados", status_code=302)


# --- Excluir chamado ---
@app.post("/admin/deletar/{chamado_id}", response_class=HTMLResponse)
async def deletar_chamado_admin(request: Request, chamado_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM chamados WHERE id = %s;", (chamado_id,))
    conn.commit()
    conn.close()

    return RedirectResponse(url="/admin/listar-chamados", status_code=302)
