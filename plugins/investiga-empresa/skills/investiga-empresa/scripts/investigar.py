#!/usr/bin/env python3
"""Investigação de uma empresa ou de um sócio, só com fontes públicas e gratuitas.

Para preparar uma reunião ou conhecer melhor uma empresa: quem são os sócios,
em que outras empresas cada um aparece e quais links públicos existem sobre eles.
Um alvo por vez. Não gera lista de leads (para isso existe a skill busca-empresas).

Fontes:
  1. Minha Receita (minhareceita.org): dados abertos de CNPJ da Receita Federal,
     inclusive o quadro de sócios (QSA) e a busca pelo CPF parcial do sócio.
  2. BrasilAPI (brasilapi.com.br): reserva do CNPJ (repete a minhareceita, com cache
     de 24 horas) e situação do domínio .br do site no registro.br.
  3. CNPJá, API aberta (open.cnpja.com): reserva e complemento (e-mails, data de
     atualização). Limite de 5 consultas por minuto, sem cadastro.
  4. DuckDuckGo (versões simples): links públicos (site, LinkedIn, notícias).
     Os links não são visitados: só o título do resultado é registrado.

Não usa chave de API, cadastro nem serviço pago (regra do projeto: só fontes livres de
cadastro). Só a biblioteca padrão do Python.

Exemplos:
  python investigar.py --cnpj 33.000.167/0001-01 --finalidade "preparar reunião comercial"
  python investigar.py --empresa "Padaria Pão Quente" --cidade Taquara --uf RS
  python investigar.py --socio "Maria da Silva Souza" --cnpj-ref 33000167000101
  python investigar.py --socio "Maria da Silva Souza" --cpf 123.456.789-00
  python investigar.py --socio "Maria da Silva Souza"
  python investigar.py --docx investigacao_maria-da-silva-souza_2026-10-15.md

O relatório sai em Word (.docx), com uma cópia .md ao lado que pode ser editada
e convertida de novo com --docx. Pasta padrão: Documentos/Investigações.
"""

import argparse
import datetime as dt
import html
import http.client
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

VERSAO = "1.0.2"
REPO = "https://github.com/jeffersonbb/Skill-buscaEmpresas-conteudo-publico"
UA = f"Mozilla/5.0 (compatible; investiga-empresa/{VERSAO}; +{REPO})"
UA_BUSCA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

MAX_SOCIOS = 15             # sócios com outras empresas pesquisadas
MAX_SOCIOS_WEB = 5          # sócios com busca web (padrão)
MAX_REGISTROS_SOCIO = 5000  # registros lidos por sócio (filiais contam)
MAX_EMPRESAS_RELATORIO = 30
MAX_HOMONIMOS = 3
PAUSA_BUSCA = 6             # segundos entre consultas ao DuckDuckGo

FONTE_RECEITA = "Receita Federal (via minhareceita.org)"
FONTE_CNPJA = "Receita Federal (via API aberta da CNPJá)"
FONTE_BRASILAPI = "Receita Federal (via BrasilAPI)"

# Sites que só repetem o cadastro do CNPJ: não contam como menção.
DIRETORIOS = (
    "cnpj.biz", "cnpj.info", "cnpj.ws", "cnpja.com", "casadosdados", "econodata",
    "databrasil", "consultasocio", "empresascnpj", "cnpjs.rocks", "solutudo",
    "cylex", "guiamais", "telelistas", "apontador", "infobel", "hotfrog", "brasil.io",
    "listamais", "empresite", "cnpjbrasil", "informecadastral", "consultacnpj",
    "situacao-cadastral", "meudinheiroweb", "minhareceita", "duckduckgo", "google.",
    "bing.", "empresaqui", "cnpj.services", "qsa", "socios.", "transparencia.cc",
    "buscadeempresas", "maiscnpj", "antifraudebrasil", "jusbrasil", "escavador", "cnpj.today",
    "advdinamico", "portaljpa",
)


class BuscaBloqueada(Exception):
    pass


def avisar(msg):
    print(msg, file=sys.stderr, flush=True)


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", texto).split())


def so_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def http_get(url, timeout=30, tentativas=2, ua=UA, dados=None, cabecalhos=None):
    erro = None
    for i in range(tentativas):
        try:
            h = {"User-Agent": ua, "Accept-Language": "pt-BR,pt;q=0.9"}
            h.update(cabecalhos or {})
            req = urllib.request.Request(url, data=dados, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                cs = resp.headers.get_content_charset() or "utf-8"
                return resp.status, resp.read(30_000_000).decode(cs, errors="replace")
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ConnectionError, ValueError) as e:
            erro = e
            if isinstance(e, urllib.error.HTTPError) and e.code in (400, 403, 404, 410, 429):
                break
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"falha ao acessar {url}: {erro}")


def http_json(url, timeout=60, tentativas=3):
    return json.loads(http_get(url, timeout=timeout, tentativas=tentativas)[1])


# ---------------------------------------------------------------- CNPJ

def cnpj_valido(c):
    c = so_digitos(c)
    if len(c) != 14 or len(set(c)) == 1:
        return False
    for n in (12, 13):
        pesos = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(d) * p for d, p in zip(c[:n], pesos))
        dv = 0 if soma % 11 < 2 else 11 - soma % 11
        if int(c[n]) != dv:
            return False
    return True


def formatar_cnpj(c):
    c = so_digitos(c)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else c


def cpf_mascarado(cpf):
    """CPF completo -> formato da base aberta (***456789**)."""
    d = so_digitos(cpf)
    return f"***{d[3:9]}**" if len(d) == 11 else None


def mascara_valida(m):
    return bool(re.fullmatch(r"\*\*\*\d{6}\*\*", m or "")) and m[3:9] not in ("000000", "999999")


def eh_pessoa_fisica(emp):
    nat = normalizar(emp.get("natureza_juridica"))
    return bool(emp.get("opcao_pelo_mei")) or "empresario individual" in nat


def _de_cnpja(d):
    """Converte a resposta da API aberta da CNPJá para os campos da minhareceita."""
    emp, end = d.get("company") or {}, d.get("address") or {}
    fones = [f"{f.get('area', '')}{f.get('number', '')}" for f in d.get("phones") or []]
    qsa, vistos = [], set()
    for m in emp.get("members") or []:
        p = m.get("person") or {}
        chave = normalizar(p.get("name"))
        if p.get("type") == "UNKNOWN" and chave in vistos:
            continue
        vistos.add(chave)
        qsa.append({"nome_socio": (p.get("name") or "").upper(), "cnpj_cpf_do_socio": p.get("taxId") or "",
                    "qualificacao_socio": (m.get("role") or {}).get("text", ""),
                    "data_entrada_sociedade": m.get("since"), "faixa_etaria": p.get("age") or "",
                    "pais": (p.get("country") or {}).get("name")})
    return {
        "cnpj": d.get("taxId"), "razao_social": emp.get("name"), "nome_fantasia": d.get("alias") or "",
        "descricao_situacao_cadastral": ((d.get("status") or {}).get("text") or "").upper(),
        "data_situacao_cadastral": d.get("statusDate"), "data_inicio_atividade": d.get("founded"),
        "descricao_identificador_matriz_filial": "MATRIZ" if d.get("head") else "FILIAL",
        "natureza_juridica": (emp.get("nature") or {}).get("text"), "porte": (emp.get("size") or {}).get("text"),
        "capital_social": emp.get("equity"), "opcao_pelo_mei": (emp.get("simei") or {}).get("optant"),
        "cnae_fiscal": (d.get("mainActivity") or {}).get("id"),
        "cnae_fiscal_descricao": (d.get("mainActivity") or {}).get("text"),
        "cnaes_secundarios": [{"codigo": a.get("id"), "descricao": a.get("text")} for a in d.get("sideActivities") or []],
        "descricao_tipo_de_logradouro": "", "logradouro": end.get("street"), "numero": end.get("number"),
        "complemento": end.get("details") or "", "bairro": end.get("district"), "municipio": end.get("city"),
        "uf": end.get("state"), "cep": end.get("zip"),
        "ddd_telefone_1": fones[0] if fones else "", "ddd_telefone_2": fones[1] if len(fones) > 1 else "",
        "email": ", ".join(e.get("address") for e in d.get("emails") or [] if e.get("address")),
        "qsa": qsa, "_atualizado": (d.get("updated") or "")[:10],
    }


def consultar_cnpj(cnpj):
    """Busca um CNPJ na minhareceita; se falhar, na BrasilAPI (cache) e depois na CNPJá."""
    cnpj = so_digitos(cnpj)
    for url, fonte in ((f"https://minhareceita.org/{cnpj}", FONTE_RECEITA),
                       (f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}", FONTE_BRASILAPI)):
        try:
            emp = http_json(url, timeout=40, tentativas=2)
            if emp.get("cnpj"):
                emp["_fonte"] = fonte
                return emp
        except (RuntimeError, json.JSONDecodeError):
            pass
    avisar(f"minhareceita e BrasilAPI indisponíveis para {cnpj}; tentando a CNPJá")
    try:
        emp = _de_cnpja(http_json(f"https://open.cnpja.com/office/{cnpj}", timeout=40, tentativas=1))
        emp["_fonte"] = FONTE_CNPJA
        return emp
    except (RuntimeError, json.JSONDecodeError) as e:
        avisar(f"CNPJá também falhou para {cnpj} ({e})")
        return None


def complementar_cnpja(emp):
    """Acrescenta e-mails e a data de atualização da CNPJá (uma consulta)."""
    if emp.get("_fonte") == FONTE_CNPJA:
        return
    try:
        extra = _de_cnpja(http_json(f"https://open.cnpja.com/office/{emp['cnpj']}", timeout=30, tentativas=1))
    except (RuntimeError, json.JSONDecodeError):
        return
    if extra.get("email") and not emp.get("email"):
        emp["email"] = extra["email"]
    emp["_atualizado"] = extra.get("_atualizado")
    emp["_fonte"] += " e API aberta da CNPJá"


def empresas_do_socio(mascara, nome):
    """Todas as empresas em que aparece um sócio com esse CPF parcial E esse nome."""
    alvo, achados, cursor, lidos = normalizar(nome), {}, None, 0
    while True:
        url = f"https://minhareceita.org/?cnpf={urllib.parse.quote(mascara)}&limit=1000"
        if cursor:
            url += f"&cursor={urllib.parse.quote(str(cursor))}"
        dados = http_json(url, timeout=120)
        lote = dados.get("data") or []
        lidos += len(lote)
        for emp in lote:
            vinculo = next((s for s in emp.get("qsa") or [] if s.get("cnpj_cpf_do_socio") == mascara
                            and normalizar(s.get("nome_socio")) == alvo), None)
            if not vinculo:
                continue  # mesmo CPF parcial, outra pessoa
            raiz = emp["cnpj"][:8]
            atual = achados.get(raiz)
            if atual is None:
                achados[raiz] = {"emp": emp, "vinculo": vinculo, "filiais": 0}
                atual = achados[raiz]
            if emp.get("identificador_matriz_filial") == 1:
                atual["emp"], atual["vinculo"] = emp, vinculo
            else:
                atual["filiais"] += 1
        cursor = dados.get("cursor")
        if not cursor or not lote:
            return list(achados.values()), False
        if lidos >= MAX_REGISTROS_SOCIO:
            return list(achados.values()), True
        time.sleep(1)


# ---------------------------------------------------------------- BrasilAPI (sem cadastro)

_dominios, _ddds = {}, {}


def dominio_br(site):
    """Situação de um domínio .br no registro.br, via BrasilAPI. None se não for .br ou se falhar."""
    host = urllib.parse.urlparse(site if "://" in site else "https://" + site).netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    if not host.endswith(".br"):
        return None
    if host not in _dominios:
        try:
            _dominios[host] = json.loads(http_get(f"https://brasilapi.com.br/api/registrobr/v1/{host}",
                                                  timeout=20, tentativas=1)[1])
        except (RuntimeError, json.JSONDecodeError):
            _dominios[host] = None
    return _dominios[host]


# ---------------------------------------------------------------- Web

_buscas_bloqueadas = set()


def _ddg(versao, consulta):
    """Uma consulta no DuckDuckGo. Devolve [(url, título, trecho)]."""
    params = {"q": consulta, "kl": "br-pt"}
    if versao == "html":
        status, pagina = http_get("https://html.duckduckgo.com/html/", timeout=25, tentativas=1,
                                  ua=UA_BUSCA, dados=urllib.parse.urlencode(params).encode())
        padrao = r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=class="result__a"|$)'
    else:
        status, pagina = http_get("https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode(params),
                                  timeout=25, tentativas=1, ua=UA_BUSCA)
        padrao = r"href=\"([^\"]+)\" class='result-link'>(.*?)</a>(.*?)(?=class='result-link'|$)"
    achados = re.findall(padrao, pagina, re.S)
    if status == 202 or (not achados and "anomaly" in pagina):
        raise BuscaBloqueada()
    saida = []
    limpar = lambda t: " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())
    for href, titulo, resto in achados:
        href = html.unescape(href)
        alvo = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0]
        if alvo.startswith("//"):
            alvo = "https:" + alvo
        if alvo.startswith("http") and "duckduckgo.com/y.js" not in alvo:
            trecho = re.search(r"result[_-]{1,2}snippet[^>]*>(.*?)</(?:a|td)>", resto, re.S)
            saida.append((alvo, limpar(titulo), limpar(trecho.group(1)) if trecho else ""))
    return saida


def busca_web(consulta):
    for versao in ("html", "lite"):
        if versao in _buscas_bloqueadas:
            continue
        try:
            resultado = _ddg(versao, consulta)
            time.sleep(PAUSA_BUSCA)
            return resultado
        except (BuscaBloqueada, RuntimeError):
            _buscas_bloqueadas.add(versao)
    raise BuscaBloqueada()


def eh_diretorio(url):
    """Sites de consulta de CNPJ: estão na lista ou têm um CNPJ no endereço."""
    host = urllib.parse.urlparse(url).netloc.lower()
    return (any(d in host for d in DIRETORIOS) or "/socios/" in url or "/socio/" in url
            or bool(re.search(r"\d{14}|\d{2}\.\d{3}\.\d{3}", url)))


def cnpjs_nos_resultados(resultados):
    vistos = []
    for url, titulo, trecho in resultados:
        texto = f"{urllib.parse.unquote(url)} {titulo} {trecho}"
        for bruto in re.findall(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", texto):
            c = so_digitos(bruto)
            if cnpj_valido(c) and c not in vistos:
                vistos.append(c)
    return vistos


def web_empresa(emp, cidade):
    nome = nome_curto(emp)
    res = busca_web(f'"{nome}" {cidade}') + busca_web(f'"{nome}" linkedin')
    links = {"linkedin": [], "redes": [], "outros": []}
    vistos = set()
    for url, titulo, _ in res:
        if eh_diretorio(url) or url in vistos:
            continue
        vistos.add(url)
        if "linkedin.com/company" in url:
            links["linkedin"].append((url, titulo))
        elif any(r in url for r in ("instagram.com", "facebook.com", "youtube.com")):
            links["redes"].append((url, titulo))
        else:
            links["outros"].append((url, titulo))
    return {k: v[:4] for k, v in links.items()}


def site_provavel(emp, outros):
    """Domínio do e-mail corporativo; senão, o primeiro resultado da web que não é rede nem diretório."""
    gratis = ("gmail.", "hotmail.", "outlook.", "yahoo.", "bol.", "uol.", "terra.", "live.", "icloud.", "ig.com")
    for email in (emp.get("email") or "").lower().split(","):
        dom = email.strip().split("@")[-1] if "@" in email else ""
        if dom and not dom.startswith(gratis):
            return dom
    return urllib.parse.urlparse(outros[0][0]).netloc if outros else None


def linha_dominio(site):
    reg = dominio_br(site)
    if not reg:
        return None
    if reg.get("status") != "REGISTERED":
        return f"**Domínio {site}:** não registrado ou vencido no registro.br"
    vence = (reg.get("expires-at") or "")[:10]
    dns = ", ".join(reg.get("hosts") or [])
    return (f"**Domínio {reg.get('fqdn') or site}:** registrado no registro.br"
            f"{', vence em ' + vence if vence else ''}{'; servidores DNS: ' + dns if dns else ''}")


def cita_pessoa(nome, *textos):
    """O resultado cita o primeiro nome e o último sobrenome da pessoa?"""
    partes, texto = normalizar(nome).split(), normalizar(" ".join(textos))
    return partes[0] in texto and partes[-1] in texto


def nome_curto(emp):
    """Nome da empresa bom para busca: fantasia sem o sufixo da filial, ou a razão social."""
    nome = (emp.get("nome_fantasia") or "").split(" - ")[0].strip()
    return nome or " ".join((emp.get("razao_social") or "").split()[:4])


def web_pessoa(nome, empresa):
    linkedin = [(u, t) for u, t, x in busca_web(f"{nome} linkedin")
                if "linkedin.com/in/" in u and cita_pessoa(nome, t, x)][:3]
    mencoes = []
    if empresa:
        mencoes = [(u, t) for u, t, x in busca_web(f'"{nome}" {empresa}')
                   if not eh_diretorio(u) and "linkedin.com/in/" not in u and cita_pessoa(nome, t, x)][:5]
    return {"linkedin": linkedin, "mencoes": mencoes}


# ---------------------------------------------------------------- Relatório

def tipo_socio(s):
    doc = s.get("cnpj_cpf_do_socio") or ""
    if len(so_digitos(doc)) == 14:
        return "PJ"
    if s.get("pais") and normalizar(s.get("pais")) not in ("brasil", "desconhecido"):
        return "Estrangeiro"
    return "PF" if mascara_valida(doc) else "?"


def endereco(emp):
    cidade = f"{emp.get('municipio') or ''}/{emp.get('uf') or ''}"
    if eh_pessoa_fisica(emp):
        return f"{cidade} (endereço completo omitido: pode ser residencial)"
    rua = " ".join(str(p).strip() for p in (emp.get("descricao_tipo_de_logradouro"), emp.get("logradouro")) if p)
    partes = [rua, emp.get("numero"), emp.get("complemento"), emp.get("bairro")]
    return ", ".join(str(p).strip() for p in partes if p and str(p).strip()) + f", {cidade}"


def telefones(emp):
    nums = [so_digitos(emp.get(k)) for k in ("ddd_telefone_1", "ddd_telefone_2")]
    return ", ".join(f"({n[:2]}) {n[2:-4]}-{n[-4:]}" for n in nums if len(n) >= 10)


def capital(v):
    try:
        return "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return ""


def celula(t):
    return str(t or "").replace("|", "/").replace("\n", " ").strip()


def tabela(cabecalho, linhas):
    out = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    out += ["| " + " | ".join(celula(c) for c in l) + " |" for l in linhas]
    return out


def links_md(lista, vazio="nada encontrado"):
    return [f"- [{celula(t).replace('[', '(').replace(']', ')') or u}]({u.replace(')', '%29')})"
            for u, t in lista] or [f"- {vazio}"]


def bloco_empresas(achados, excedeu, excluir_raiz=None):
    itens = [a for a in achados if a["emp"]["cnpj"][:8] != excluir_raiz]
    ativas = [a for a in itens if a["emp"].get("descricao_situacao_cadastral") == "ATIVA"]
    itens.sort(key=lambda a: (a["emp"].get("descricao_situacao_cadastral") != "ATIVA",
                              a["vinculo"].get("data_entrada_sociedade") or "9"))
    linhas = []
    for a in itens[:MAX_EMPRESAS_RELATORIO]:
        e, v = a["emp"], a["vinculo"]
        fantasia = e.get("nome_fantasia")
        nome = e.get("razao_social") + (f" ({fantasia})" if fantasia and fantasia != e.get("razao_social") else "")
        linhas.append([nome, formatar_cnpj(e["cnpj"]), e.get("descricao_situacao_cadastral"),
                       v.get("qualificacao_socio"), v.get("data_entrada_sociedade") or "",
                       f"{e.get('municipio')}/{e.get('uf')}", e.get("cnae_fiscal_descricao"),
                       a["filiais"] or ""])
    out = [f"{len(itens)} empresa(s), {len(ativas)} ativa(s)."]
    if linhas:
        out += [""] + tabela(["Empresa", "CNPJ", "Situação", "Cargo", "Desde", "Cidade", "Atividade", "Filiais"], linhas)
    if len(itens) > MAX_EMPRESAS_RELATORIO:
        out.append(f"\n_Mostrando {MAX_EMPRESAS_RELATORIO} de {len(itens)}._")
    if excedeu:
        out.append(f"\n_Leitura parada em {MAX_REGISTROS_SOCIO} registros: pode haver mais empresas._")
    return out, len(itens), len(ativas)


def rodape(hoje, fontes):
    return [
        "", "---", "", "## Fontes e LGPD", "",
        *[f"- {f}" for f in fontes],
        f"- Coleta em {hoje}. Os dados da Receita podem estar desatualizados.",
        "- Links da web **não foram confirmados**: pode haver homônimos. Confira antes de usar.",
        "",
        "**Uso restrito.** Este relatório tem dados pessoais (nomes, cargos, faixa etária, vínculos societários). "
        "Use só para a finalidade informada (ex.: preparar uma reunião ou avaliar um parceiro), não repasse, "
        "não publique e apague quando não precisar mais. Base sugerida: legítimo interesse "
        "(LGPD, art. 7º, IX e art. 10), com dados de acesso público (art. 7º, §§ 3º e 4º).",
    ]


def pasta_padrao():
    docs = Path.home() / "Documents"
    return str((docs if docs.is_dir() else Path.home()) / "Investigações")


def salvar(pasta, nome, linhas):
    """Grava o .md (fonte editável) e o .docx (para o usuário). Devolve o caminho do .docx."""
    os.makedirs(pasta, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", normalizar(nome)).strip("-")[:50] or "alvo"
    caminho = os.path.join(pasta, f"investigacao_{slug}_{dt.date.today().isoformat()}.md")
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(linhas) + "\n")
    return md_para_docx(caminho)


# ---------------------------------------------------------------- Word (.docx)

W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
ESPACO_CELULA = '<w:spacing w:before="20" w:after="20"/>'
_INLINE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)|\*\*(.+?)\*\*|`([^`]+)`|(?<![\w])_(.+?)_(?![\w])")


def _run(texto, negrito=False, italico=False, mono=False, estilo=None, tamanho=None, cor=None):
    props = ""
    if estilo:
        props += f'<w:rStyle w:val="{estilo}"/>'
    if mono:
        props += '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>'
    if negrito:
        props += "<w:b/>"
    if italico:
        props += "<w:i/>"
    if cor:
        props += f'<w:color w:val="{cor}"/>'
    if tamanho:
        props += f'<w:sz w:val="{tamanho}"/>'
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(texto)}</w:t></w:r>'


def _inline(texto, links, tamanho=None, italico=False, cor=None):
    """Converte o Markdown simples de uma linha em runs do Word."""
    out, pos = [], 0
    for m in _INLINE.finditer(texto):
        if m.start() > pos:
            out.append(_run(texto[pos:m.start()], italico=italico, tamanho=tamanho, cor=cor))
        if m.group(1):
            links.append(m.group(2))
            out.append(f'<w:hyperlink r:id="rIdL{len(links)}">'
                       f'{_run(m.group(1), estilo="Hyperlink", tamanho=tamanho)}</w:hyperlink>')
        elif m.group(3):
            out.append(_run(m.group(3), negrito=True, italico=italico, tamanho=tamanho, cor=cor))
        elif m.group(4):
            out.append(_run(m.group(4), mono=True, tamanho=tamanho, cor=cor))
        else:
            out.append(_run(m.group(5), italico=True, tamanho=tamanho, cor=cor))
        pos = m.end()
    if pos < len(texto):
        out.append(_run(texto[pos:], italico=italico, tamanho=tamanho, cor=cor))
    return "".join(out)


def _par(conteudo, estilo=None, extra=""):
    ppr = (f'<w:pStyle w:val="{estilo}"/>' if estilo else "") + extra
    return f'<w:p>{"<w:pPr>" + ppr + "</w:pPr>" if ppr else ""}{conteudo}</w:p>'


def _tabela(linhas, links):
    celulas = [[c.strip() for c in l.strip().strip("|").split("|")] for l in linhas
               if not re.fullmatch(r"\|?(\s*:?-+:?\s*\|)+\s*", l.strip())]
    if not celulas:
        return ""
    n = max(len(c) for c in celulas)
    bordas = "".join(f'<w:{b} w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
                     for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
    xml = [f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblBorders>{bordas}</w:tblBorders>'
           '<w:tblCellMar><w:left w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar>'
           '<w:tblLook w:val="04A0" w:firstRow="1"/></w:tblPr><w:tblGrid>'
           + "".join("<w:gridCol/>" for _ in range(n)) + "</w:tblGrid>"]
    for i, linha in enumerate(celulas):
        cab = i == 0
        xml.append("<w:tr>" + ('<w:trPr><w:tblHeader/></w:trPr>' if cab else ""))
        for c in linha + [""] * (n - len(linha)):
            sombra = '<w:shd w:val="clear" w:color="auto" w:fill="DCE6F0"/>' if cab else ""
            corpo = _run(c, negrito=True, tamanho=18) if cab else _inline(c, links, tamanho=18)
            xml.append(f"<w:tc><w:tcPr>{sombra}</w:tcPr>{_par(corpo, extra=ESPACO_CELULA)}</w:tc>")
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml) + _par("")


_ESTILOS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Calibri" w:cs="Calibri"/>
<w:sz w:val="21"/><w:lang w:val="pt-BR"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="120" w:after="160"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="1F3864"/><w:sz w:val="36"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="2" w:color="1F3864"/></w:pBdr><w:spacing w:before="320" w:after="100"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="1F3864"/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="200" w:after="80"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:color w:val="2F5496"/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading4"><w:name w:val="heading 4"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="160" w:after="60"/><w:outlineLvl w:val="3"/></w:pPr><w:rPr><w:b/><w:i/><w:color w:val="2F5496"/></w:rPr></w:style>
<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr></w:style>
</w:styles>"""


def md_para_docx(caminho_md):
    """Converte o Markdown do relatório (subconjunto simples) num .docx, só com a biblioteca padrão."""
    linhas = open(caminho_md, encoding="utf-8").read().splitlines()
    corpo, links, i = [], [], 0
    while i < len(linhas):
        l = linhas[i].rstrip()
        if l.startswith("|"):
            bloco = []
            while i < len(linhas) and linhas[i].lstrip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            corpo.append(_tabela(bloco, links))
            continue
        i += 1
        if not l.strip() or l.strip() == "---":
            continue
        m = re.match(r"(#{1,4}) (.*)", l)
        if m:
            corpo.append(_par(_inline(m.group(2), links), f"Heading{len(m.group(1))}"))
        elif l.startswith("> "):
            corpo.append(_par(_inline(l[2:], links, italico=True, cor="595959"),
                              extra='<w:pBdr><w:left w:val="single" w:sz="12" w:space="6" w:color="BFBFBF"/></w:pBdr>'))
        elif re.match(r"\s*- ", l):
            corpo.append(_par("<w:r><w:t>•</w:t></w:r><w:r><w:tab/></w:r>" + _inline(re.sub(r"^\s*- ", "", l), links),
                              extra='<w:tabs><w:tab w:val="left" w:pos="360"/></w:tabs>'
                                    '<w:spacing w:after="40"/><w:ind w:left="360" w:hanging="240"/>'))
        else:
            corpo.append(_par(_inline(l, links)))
    secao = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
             '<w:pgMar w:top="1000" w:right="900" w:bottom="1000" w:left="900" w:header="500" w:footer="500" w:gutter="0"/></w:sectPr>')
    documento = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {W_NS}><w:body>'
                 + "".join(corpo) + secao + "</w:body></w:document>")
    rels = ['<Relationship Id="rIdS" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>']
    rels += [f'<Relationship Id="rIdL{n}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
             f'Target={quoteattr(u)} TargetMode="External"/>' for n, u in enumerate(links, 1)]
    agora = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    partes = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '</Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>',
        "docProps/core.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(linhas[0].lstrip("# ") if linhas else "Investigação")}</dc:title>'
            '<dc:creator>investiga-empresa</dc:creator>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{agora}</dcterms:created></cp:coreProperties>',
        "word/_rels/document.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(rels) + "</Relationships>",
        "word/styles.xml": _ESTILOS,
        "word/document.xml": documento,
    }
    destino = os.path.splitext(caminho_md)[0] + ".docx"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in partes.items():
            z.writestr(nome, conteudo)
    return destino


# ---------------------------------------------------------------- Modos

def modo_cnpj(args):
    hoje = dt.date.today().isoformat()
    cnpj = so_digitos(args.cnpj)
    if not cnpj_valido(cnpj):
        sys.exit(f"CNPJ inválido: {args.cnpj}")
    emp = consultar_cnpj(cnpj)
    if not emp:
        sys.exit("Não consegui consultar o CNPJ agora (minhareceita e CNPJá fora do ar). Tente mais tarde.")
    complementar_cnpja(emp)
    nome = emp.get("nome_fantasia") or emp.get("razao_social")
    avisar(f"Empresa: {emp.get('razao_social')} ({emp.get('descricao_situacao_cadastral')})")

    linhas = [f"# Investigação: {nome}", "",
              f"> Relatório gerado em {hoje} pela skill investiga-empresa. Uso restrito: veja o fim do documento.", "",
              f"**Finalidade:** {args.finalidade or 'não informada'}", "",
              "## Empresa", ""]
    secundarios = "; ".join(f"{c.get('codigo')} {c.get('descricao')}" for c in emp.get("cnaes_secundarios") or [])
    linhas += tabela(["Campo", "Valor"], [
        ["Razão social", emp.get("razao_social")], ["Nome fantasia", emp.get("nome_fantasia")],
        ["CNPJ", f"{formatar_cnpj(emp['cnpj'])} ({emp.get('descricao_identificador_matriz_filial', '').lower()})"],
        ["Situação", f"{emp.get('descricao_situacao_cadastral')} desde {emp.get('data_situacao_cadastral') or '?'}"],
        ["Abertura", emp.get("data_inicio_atividade")], ["Natureza jurídica", emp.get("natureza_juridica")],
        ["Porte", emp.get("porte")], ["Capital social", capital(emp.get("capital_social"))],
        ["Atividade principal", f"{emp.get('cnae_fiscal')} {emp.get('cnae_fiscal_descricao')}"],
        ["Atividades secundárias", secundarios[:600]], ["Endereço", endereco(emp)],
        ["Telefone", telefones(emp)], ["E-mail", emp.get("email")],
        ["Cadastro atualizado em", emp.get("_atualizado") or ""],
    ])

    web_bloqueada, outros = False, []
    if not args.sem_web:
        try:
            w = web_empresa(emp, emp.get("municipio") or "")
            outros = w["outros"]
            linhas += ["", "### Na web (não confirmado)", "", "**LinkedIn da empresa**", *links_md(w["linkedin"]),
                       "", "**Redes sociais**", *links_md(w["redes"]), "", "**Outros resultados**", *links_md(w["outros"])]
        except BuscaBloqueada:
            web_bloqueada = True
    site = site_provavel(emp, outros)
    dom = linha_dominio(site) if site else None
    if dom:
        linhas += ["", dom]

    qsa = emp.get("qsa") or []
    linhas += ["", f"## Sócios e administradores ({len(qsa)})", ""]
    if not qsa:
        linhas.append("A base aberta não traz sócios para esta empresa (é comum em MEI, empresário individual e algumas associações).")
    else:
        linhas += tabela(["Nome", "Tipo", "Cargo", "Desde", "Faixa etária"],
                         [[s.get("nome_socio"), tipo_socio(s), s.get("qualificacao_socio"),
                           s.get("data_entrada_sociedade") or "", s.get("faixa_etaria") or ""] for s in qsa])

    resumo_socios = []
    pf = [s for s in qsa if tipo_socio(s) == "PF"][:args.max_socios]
    for i, s in enumerate(pf):
        nome_s = s["nome_socio"]
        avisar(f"Sócio {i + 1}/{len(pf)}: {nome_s}")
        linhas += ["", f"## {nome_s.title()}", "", f"Cargo nesta empresa: **{s.get('qualificacao_socio')}**"
                   f"{', desde ' + s['data_entrada_sociedade'] if s.get('data_entrada_sociedade') else ''}."
                   f"{' Faixa etária: ' + s['faixa_etaria'] + '.' if s.get('faixa_etaria') else ''}", "",
                   "### Outras empresas em que aparece", ""]
        try:
            achados, excedeu = empresas_do_socio(s["cnpj_cpf_do_socio"], nome_s)
            bloco, n, n_ativas = bloco_empresas(achados, excedeu, excluir_raiz=emp["cnpj"][:8])
            linhas += bloco
            resumo_socios.append(f"{nome_s.title()}: {n} outra(s) empresa(s), {n_ativas} ativa(s)")
        except (RuntimeError, json.JSONDecodeError) as e:
            linhas.append(f"_Não foi possível consultar agora ({e})._")
            resumo_socios.append(f"{nome_s.title()}: consulta falhou")
        if not args.sem_web and not web_bloqueada and i < args.max_socios_web:
            try:
                w = web_pessoa(nome_s.title(), nome_curto(emp))
                linhas += ["", "### Na web (não confirmado)", "", "**Possíveis perfis no LinkedIn**",
                           *links_md(w["linkedin"]), "", "**Menções junto com a empresa**", *links_md(w["mencoes"])]
            except BuscaBloqueada:
                web_bloqueada = True
    outros_pj = [s for s in qsa if tipo_socio(s) == "PJ"]
    if outros_pj:
        linhas += ["", "## Sócios que são empresas", "",
                   *[f"- {s['nome_socio']} ({formatar_cnpj(s['cnpj_cpf_do_socio'])}): investigue com `--cnpj`" for s in outros_pj]]
    pulados = len([s for s in qsa if tipo_socio(s) == "PF"]) - len(pf)

    fontes = [emp["_fonte"]]
    if not args.sem_web:
        fontes.append("Busca no DuckDuckGo (só títulos e links; os sites não foram visitados)")
    if dom:
        fontes.append("BrasilAPI: situação do domínio .br no registro.br")
    caminho = salvar(args.saida, nome, linhas + rodape(hoje, fontes))

    print("RESUMO")
    print(f"Empresa: {emp.get('razao_social')} | {formatar_cnpj(emp['cnpj'])} | {emp.get('descricao_situacao_cadastral')}")
    print(f"Sócios e administradores: {len(qsa)} ({len(outros_pj)} PJ)")
    for r in resumo_socios:
        print(f"  - {r}")
    if pulados > 0:
        print(f"AVISO: {pulados} sócio(s) não pesquisado(s) (limite {args.max_socios}; use --max-socios)")
    if eh_pessoa_fisica(emp):
        print("AVISO: MEI ou empresário individual: a empresa se confunde com a pessoa física")
    if web_bloqueada:
        print("BUSCA_WEB_BLOQUEADA: o DuckDuckGo limitou as consultas; parte dos links ficou de fora")
    print(f"Relatório: {caminho}")
    print(f"Fonte editável: {os.path.splitext(caminho)[0]}.md")


def modo_empresa(args):
    local = " ".join(x for x in (args.cidade, args.uf) if x)
    try:
        res = busca_web(f"{args.empresa} CNPJ {local}".strip())
        if len(cnpjs_nos_resultados(res)) < 2:
            res += busca_web(f"{args.empresa} {local} cnpj razão social".strip())
    except BuscaBloqueada:
        sys.exit("BUSCA_WEB_BLOQUEADA: o DuckDuckGo limitou as consultas. Tente mais tarde ou informe o CNPJ.")
    palavras = [p for p in normalizar(args.empresa).split() if len(p) > 2]
    candidatos = []
    for c in cnpjs_nos_resultados(res)[:10]:
        emp = consultar_cnpj(c)
        time.sleep(1)
        if not emp:
            continue
        texto = normalizar(f"{emp.get('razao_social')} {emp.get('nome_fantasia')}")
        if palavras and not all(p in texto for p in palavras):
            continue
        if args.uf and (emp.get("uf") or "").upper() != args.uf.upper():
            continue
        candidatos.append(emp)
    print("RESUMO")
    if not candidatos:
        print("Nenhum CNPJ encontrado com esse nome. Peça o CNPJ ao usuário ou tente outro nome (razão social).")
        return
    print(f"Candidatos encontrados: {len(candidatos)} (confirme com o usuário e rode de novo com --cnpj)")
    for e in candidatos:
        print(f"  - {formatar_cnpj(e['cnpj'])} | {e.get('razao_social')} | {e.get('nome_fantasia') or '-'} | "
              f"{e.get('municipio')}/{e.get('uf')} | {e.get('descricao_situacao_cadastral')} | "
              f"{e.get('descricao_identificador_matriz_filial')}")


def mascaras_do_nome(nome, cnpjs):
    """Procura o nome no quadro de sócios de cada CNPJ e devolve {cpf parcial: empresa de referência}."""
    alvo, achadas = normalizar(nome), {}
    for c in cnpjs:
        emp = consultar_cnpj(c)
        time.sleep(1)
        for s in (emp or {}).get("qsa") or []:
            m = s.get("cnpj_cpf_do_socio")
            if normalizar(s.get("nome_socio")) == alvo and mascara_valida(m):
                achadas.setdefault(m, emp)
    return achadas


def modo_socio(args):
    hoje = dt.date.today().isoformat()
    nome = " ".join(args.socio.split())
    if len(nome.split()) < 2:
        sys.exit("Informe o nome completo do sócio (nome e sobrenome).")
    origem = ""
    if args.cpf:
        m = cpf_mascarado(args.cpf)
        if not m:
            sys.exit("CPF inválido: informe os 11 dígitos.")
        mascaras, origem = {m: None}, "CPF informado pelo usuário (usado só na forma parcial)"
    elif args.cnpj_ref:
        mascaras = mascaras_do_nome(nome, [so_digitos(args.cnpj_ref)])
        origem = f"quadro de sócios do CNPJ {formatar_cnpj(args.cnpj_ref)}"
        if not mascaras:
            sys.exit(f"'{nome}' não aparece como sócio (pessoa física) no CNPJ {formatar_cnpj(args.cnpj_ref)}. Confira a grafia.")
    else:
        try:
            res = busca_web(f"{nome} cnpj")
            if not cnpjs_nos_resultados(res):
                res += busca_web(f'"{nome}" sócio empresa')
        except BuscaBloqueada:
            sys.exit("BUSCA_WEB_BLOQUEADA: o DuckDuckGo limitou as consultas. Peça o CNPJ de uma empresa da pessoa ou o CPF.")
        mascaras = mascaras_do_nome(nome, cnpjs_nos_resultados(res)[:8])
        origem = "busca web por empresas ligadas ao nome (confirme se é a pessoa certa)"
        if not mascaras:
            print("RESUMO")
            print(f"Não achei empresas com '{nome}' no quadro de sócios. Peça ao usuário o CNPJ de uma empresa "
                  "da pessoa (--cnpj-ref) ou o CPF (--cpf).")
            return

    homonimos = len(mascaras)
    linhas = [f"# Investigação: {nome.title()}", "",
              f"> Relatório gerado em {hoje} pela skill investiga-empresa. Uso restrito: veja o fim do documento.", "",
              f"**Finalidade:** {args.finalidade or 'não informada'}", "",
              f"Ponto de partida: {origem}.", ""]
    if homonimos > 1:
        linhas += [f"**Atenção: {homonimos} pessoas diferentes com esse mesmo nome** aparecem como sócias. "
                   "Cada uma tem uma seção abaixo, identificada pela empresa onde foi encontrada.", ""]
    resumo_pessoas, empresa_ref = [], None
    for i, (m, ref) in enumerate(list(mascaras.items())[:MAX_HOMONIMOS]):
        rotulo = f"Pessoa {chr(65 + i)}" if homonimos > 1 else "Empresas"
        if ref and homonimos > 1:
            rotulo += f" (encontrada em {ref.get('razao_social')}, {ref.get('municipio')}/{ref.get('uf')})"
        linhas += [f"## {rotulo}", ""]
        try:
            achados, excedeu = empresas_do_socio(m, nome)
            bloco, n, n_ativas = bloco_empresas(achados, excedeu)
            linhas += bloco
            resumo_pessoas.append(f"{rotulo}: {n} empresa(s), {n_ativas} ativa(s)")
            if achados and not empresa_ref:
                ativas = [a for a in achados if a["emp"].get("descricao_situacao_cadastral") == "ATIVA"] or achados
                empresa_ref = nome_curto(ativas[0]["emp"])
        except (RuntimeError, json.JSONDecodeError) as e:
            linhas.append(f"_Não foi possível consultar agora ({e})._")
        linhas.append("")

    web_bloqueada = False
    if not args.sem_web:
        try:
            w = web_pessoa(nome.title(), empresa_ref if homonimos == 1 else None)
            linhas += ["## Na web (não confirmado)", "", "**Possíveis perfis no LinkedIn**", *links_md(w["linkedin"])]
            if homonimos == 1:
                linhas += ["", f"**Menções junto com {empresa_ref}**", *links_md(w["mencoes"])]
        except BuscaBloqueada:
            web_bloqueada = True

    fontes = [FONTE_RECEITA + ": busca pelo CPF parcial e conferência do nome"]
    if not args.sem_web:
        fontes.append("Busca no DuckDuckGo (só títulos e links; os sites não foram visitados)")
    caminho = salvar(args.saida, nome, linhas + rodape(hoje, fontes))

    print("RESUMO")
    print(f"Pessoa: {nome.title()} | ponto de partida: {origem}")
    if homonimos > 1:
        print(f"AVISO: {homonimos} homônimos encontrados (mostrando até {MAX_HOMONIMOS}); confirme com o usuário qual é a pessoa")
    for r in resumo_pessoas:
        print(f"  - {r}")
    if web_bloqueada:
        print("BUSCA_WEB_BLOQUEADA: o DuckDuckGo limitou as consultas; os links da web ficaram de fora")
    print(f"Relatório: {caminho}")
    print(f"Fonte editável: {os.path.splitext(caminho)[0]}.md")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Investiga uma empresa ou um sócio com fontes públicas e gratuitas. Um alvo por vez.")
    alvo = p.add_mutually_exclusive_group(required=True)
    alvo.add_argument("--cnpj", help="CNPJ da empresa: dados, sócios e as outras empresas de cada sócio")
    alvo.add_argument("--empresa", metavar="NOME", help="Nome da empresa: só procura o CNPJ e lista os candidatos")
    alvo.add_argument("--socio", metavar="NOME", help="Nome completo de uma pessoa: empresas em que ela é sócia")
    alvo.add_argument("--docx", metavar="MD", help="Só converte de novo um relatório .md (já editado) em .docx")
    p.add_argument("--cidade", help="Com --empresa: ajuda a achar o CNPJ certo")
    p.add_argument("--uf", help="Com --empresa: filtra os candidatos pelo estado")
    p.add_argument("--cnpj-ref", help="Com --socio: CNPJ de uma empresa onde a pessoa é sócia (mais preciso)")
    p.add_argument("--cpf", help="Com --socio: CPF completo, se o usuário souber (só a parte pública é usada)")
    p.add_argument("--max-socios", type=int, default=MAX_SOCIOS, help=f"Sócios pesquisados (padrão {MAX_SOCIOS})")
    p.add_argument("--max-socios-web", type=int, default=MAX_SOCIOS_WEB,
                   help=f"Sócios com busca web (padrão {MAX_SOCIOS_WEB}; cada um leva uns 15 segundos)")
    p.add_argument("--sem-web", action="store_true", help="Só dados da Receita, sem busca web")
    p.add_argument("--finalidade", help="Para que serve o levantamento (ex.: preparar reunião comercial); vai no topo do relatório")
    p.add_argument("--saida", default=pasta_padrao(), help="Pasta onde salvar o relatório (padrão: Documentos/Investigações)")
    args = p.parse_args()
    if args.docx:
        print(f"Relatório: {md_para_docx(args.docx)}")
    elif args.cnpj:
        modo_cnpj(args)
    elif args.empresa:
        modo_empresa(args)
    else:
        modo_socio(args)


if __name__ == "__main__":
    main()
