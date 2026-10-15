#!/usr/bin/env python3
"""Busca de empresas por ramo e cidade, só com fontes públicas e gratuitas.

Fontes:
  1. IBGE (servicodados.ibge.gov.br): código do município e códigos CNAE.
  2. Minha Receita (minhareceita.org): dados abertos de CNPJ da Receita Federal.
  3. DuckDuckGo (versão lite): busca do site e das redes sociais da empresa.
     Melhor esforço: se o DuckDuckGo bloquear, a busca web para sozinha.
  4. Site da própria empresa: e-mail, link de WhatsApp e redes sociais
     (respeitando o robots.txt).

Não usa chave de API, cadastro nem serviço pago. Só a biblioteca padrão do Python.

Exemplos:
  python buscar_leads.py --cidade Taquara --uf RS --ramo contabilidade --qtd 20
  python buscar_leads.py --listar-cnae "academia"
  python buscar_leads.py --cidade "Porto Alegre" --uf RS --cnae 6920601 --qtd 10 --sem-web
  python buscar_leads.py --enriquecer leads_contabilidade_taquara-rs_2026-10-14.csv
"""

import argparse
import csv
import difflib
import datetime as dt
import gzip
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
import urllib.robotparser
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

VERSAO = "1.0.3"
REPO = "https://github.com/jeffersonbb/Skill-buscaEmpresas-conteudo-publico"
UA = f"Mozilla/5.0 (compatible; busca-empresas/{VERSAO}; +{REPO})"

QTD_PADRAO = 20
QTD_MAXIMA = 50          # acima disso só com --permitir-mais
QTD_ABSOLUTA = 200       # teto mesmo com --permitir-mais
MAX_REGISTROS_RECEITA = 3000
PAUSA_BUSCA = 6          # segundos entre consultas ao DuckDuckGo

# Sites que listam CNPJs ou empresas: não são o site da empresa.
DIRETORIOS = (
    "cnpj.biz", "cnpj.info", "cnpj.ws", "cnpja.com", "casadosdados", "econodata",
    "databrasil", "consultasocio", "empresascnpj", "cnpjs.rocks", "solutudo",
    "cylex", "guiamais", "telelistas", "apontador", "encontra", "infobel",
    "hotfrog", "brasil.io", "jusbrasil", "reclameaqui", "google.", "bing.",
    "youtube.", "wikipedia", "linkedin.com", "twitter.com", "x.com", "tiktok.com",
    "receita", "gov.br", "listamais", "achei", "guia", "empresite", "cnpjbrasil",
    "informecadastral", "consultacnpj", "situacao-cadastral", "meudinheiroweb",
    "serasa", "mapquest", "yelp", "foursquare", "waze", "kekanto", "doctoralia",
    "olx.", "mercadolivre", "glassdoor", "indeed", "catho", "duckduckgo",
    "instagram.com", "facebook.com", "whatsapp.com", "wa.me", "minhareceita",
)
DOMINIOS_EMAIL_GRATIS = (
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.com.br",
    "bol.com.br", "uol.com.br", "terra.com.br", "live.com", "icloud.com",
    "ig.com.br", "globo.com", "msn.com", "hotmail.com.br", "outlook.com.br",
)
FONTE_RECEITA = "Receita Federal (via minhareceita.org)"
FONTE_BUSCA = "busca web"
FONTE_SITE = "site da empresa"


class BuscaBloqueada(Exception):
    pass


def avisar(msg):
    print(msg, file=sys.stderr, flush=True)


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


def so_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def http_get(url, timeout=30, tentativas=2, ua=UA, dados=None):
    erro = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, data=dados, headers={"User-Agent": ua, "Accept-Language": "pt-BR,pt;q=0.9"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                bruto = resp.read(20_000_000)
                if bruto[:2] == b"\x1f\x8b":  # alguns servidores (IBGE) mandam gzip sem pedir
                    bruto = gzip.decompress(bruto)
                cs = resp.headers.get_content_charset() or "utf-8"
                return resp.status, bruto.decode(cs, errors="replace")
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ConnectionError, ValueError) as e:
            erro = e
            if isinstance(e, urllib.error.HTTPError) and e.code in (403, 404, 410):
                break
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"falha ao acessar {url}: {erro}")


def http_json(url, timeout=60):
    for i in range(3):
        try:
            return json.loads(http_get(url, timeout=timeout, tentativas=3)[1])
        except json.JSONDecodeError:  # resposta cortada no meio: tenta de novo
            if i == 2:
                raise RuntimeError(f"resposta incompleta de {url}; tente de novo em alguns minutos")
            time.sleep(3)


# ---------------------------------------------------------------- IBGE

def achar_municipio(cidade, uf):
    lista = http_json(f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios")
    alvo = normalizar(cidade)
    for m in lista:
        if normalizar(m["nome"]) == alvo:
            return m["id"], m["nome"]
    nomes = {normalizar(m["nome"]): m["nome"] for m in lista}
    parecidos = [nomes[n] for n in difflib.get_close_matches(alvo, nomes, n=5, cutoff=0.75)]
    parecidos += [m["nome"] for m in lista if alvo in normalizar(m["nome"]) and m["nome"] not in parecidos]
    dica = f" Parecidos: {', '.join(parecidos[:8])}." if parecidos else ""
    raise SystemExit(f"ERRO: município '{cidade}' não encontrado em {uf}.{dica}")


# Nomes populares de ramos -> palavras da descrição oficial do CNAE.
SINONIMOS = {
    "academia": "condicionamento fisico", "academias": "condicionamento fisico",
    "advocacia": "advocaticios", "advogado": "advocaticios", "advogados": "advocaticios",
    "dentista": "odontologica", "dentistas": "odontologica", "odontologia": "odontologica",
    "clinica medica": "medica ambulatorial", "medico": "medica ambulatorial", "medicos": "medica ambulatorial",
    "salao de beleza": "cabeleireiros", "salao": "cabeleireiros", "cabeleireiro": "cabeleireiros",
    "pet shop": "animais de estimacao", "petshop": "animais de estimacao",
    "veterinario": "veterinarias", "veterinaria": "veterinarias",
    "imobiliaria": "corretagem na compra e venda", "imobiliarias": "corretagem na compra e venda",
    "farmacia": "produtos farmaceuticos", "farmacias": "produtos farmaceuticos",
    "oficina mecanica": "manutencao e reparacao mecanica de veiculos", "mecanica": "manutencao e reparacao mecanica de veiculos",
    "escola de idiomas": "ensino de idiomas", "autoescola": "formacao de condutores", "auto escola": "formacao de condutores",
    "contador": "contabilidade", "contadores": "contabilidade", "contabil": "contabilidade",
    "padaria": "padaria", "restaurante": "restaurantes", "lanchonete": "lanchonetes",
    "psicologo": "psicologia", "psicologa": "psicologia", "fisioterapeuta": "fisioterapia",
    "arquiteto": "arquitetura", "arquitetos": "arquitetura", "engenharia": "engenharia",
    "marketing": "agencias de publicidade", "agencia de publicidade": "agencias de publicidade",
    "informatica": "desenvolvimento de programas de computador", "software": "desenvolvimento de programas de computador",
}


def buscar_cnaes(termo):
    lista = http_json("https://servicodados.ibge.gov.br/api/v2/cnae/subclasses")
    termo = SINONIMOS.get(normalizar(termo), termo)
    palavras = [p for p in normalizar(termo).split() if len(p) > 2]
    achados = []
    for s in lista:
        desc = normalizar(s["descricao"])
        if all(p in desc for p in palavras):
            achados.append((s["id"], s["descricao"].capitalize()))
    return achados


# ---------------------------------------------------------------- Receita

def listar_empresas(cod_municipio, cnae):
    url_base = f"https://minhareceita.org/?municipio={cod_municipio}&cnae_fiscal={cnae}&limit=200"
    cursor, total = None, []
    while True:
        url = url_base + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
        dados = http_json(url, timeout=90)
        total.extend(dados.get("data") or [])
        cursor = dados.get("cursor")
        if not cursor or len(total) >= MAX_REGISTROS_RECEITA:
            return total
        time.sleep(1)


def limpar_telefone(bruto):
    num = so_digitos(bruto)
    if num.startswith("55") and len(num) in (12, 13):
        num = num[2:]
    if len(num) not in (10, 11) or set(num) == {"0"}:
        return None
    # Celular antigo sem o nono dígito (ex.: 51 9759-1074).
    if len(num) == 10 and num[2] in "6789":
        num = num[:2] + "9" + num[2:]
    return num


def formatar_telefone(num):
    if len(num) == 11:
        return f"({num[:2]}) {num[2:7]}-{num[7:]}"
    return f"({num[:2]}) {num[2:6]}-{num[6:]}"


def eh_celular(num):
    return len(num) == 11 and num[2] == "9"


def eh_pessoa_fisica(emp):
    nat = normalizar(emp.get("natureza_juridica"))
    return bool(emp.get("opcao_pelo_mei")) or "empresario (individual)" in nat or "empresario individual" in nat


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


def cidades_do_ddd(ddd):
    """Cidades atendidas por um DDD (BrasilAPI). Lista vazia se falhar."""
    if ddd not in _ddds:
        try:
            dados = json.loads(http_get(f"https://brasilapi.com.br/api/ddd/v1/{ddd}", timeout=20, tentativas=1)[1])
            _ddds[ddd] = [normalizar(c) for c in dados.get("cities") or []]
        except (RuntimeError, json.JSONDecodeError):
            _ddds[ddd] = []
    return _ddds[ddd]


# ---------------------------------------------------------------- Web

UA_BUSCA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
_buscas_bloqueadas = set()


def _ddg(versao, consulta):
    """Uma consulta numa das versões simples do DuckDuckGo. Devolve a lista de links."""
    params = {"q": consulta, "kl": "br-pt"}
    if versao == "html":
        status, pagina = http_get("https://html.duckduckgo.com/html/", timeout=25, tentativas=1,
                                  ua=UA_BUSCA, dados=urllib.parse.urlencode(params).encode())
        padrao = r'class="result__a" href="([^"]+)"'
    else:
        status, pagina = http_get("https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode(params),
                                  timeout=25, tentativas=1, ua=UA_BUSCA)
        padrao = r"href=\"([^\"]+)\" class='result-link'"
    hrefs = re.findall(padrao, pagina)
    if status == 202 or (not hrefs and "anomaly" in pagina):
        raise BuscaBloqueada()
    links = []
    for href in hrefs:
        href = html.unescape(href)
        alvo = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0]
        if alvo.startswith("//"):
            alvo = "https:" + alvo
        if alvo.startswith("http"):
            links.append(alvo)
    return links


def busca_web(consulta):
    """Tenta as duas versões do DuckDuckGo; só desiste quando as duas bloqueiam."""
    for versao in ("html", "lite"):
        if versao in _buscas_bloqueadas:
            continue
        try:
            return _ddg(versao, consulta)
        except BuscaBloqueada:
            _buscas_bloqueadas.add(versao)
    raise BuscaBloqueada()


def dominio(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def raiz(url):
    u = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    return f"{u.scheme}://{u.netloc}/"


PALAVRAS_GENERICAS = {
    "ltda", "me", "epp", "eireli", "sa", "ss", "s/s", "cia", "de", "da", "do", "das", "dos", "e",
    "contabilidade", "contabil", "contabeis", "contadores", "contador", "assessoria", "consultoria",
    "servicos", "solucoes", "escritorio", "empresarial", "empresa", "gestao", "associados", "grupo",
}


def nome_no_dominio(url, linha):
    """O domínio leva o nome da empresa? Ex.: Prescon -> presconcontabil.com.br."""
    rotulo = re.sub(r"[^a-z0-9]", "", dominio(url).split(".")[0])
    for nome in (linha["Nome"], linha["Razão social"]):
        palavras = [p for p in re.findall(r"[a-z0-9&]+", normalizar(nome)) if p not in PALAVRAS_GENERICAS]
        if any(len(p) >= 4 and p in rotulo for p in palavras):
            return True
        sigla = "".join(re.sub(r"[^a-z0-9]", "", p) for p in palavras)
        if len(sigla) >= 2 and rotulo.startswith(sigla):
            return True
    return False


def classificar_links(links, linha):
    sites, instagram, facebook = [], None, None
    for l in links:
        d = dominio(l)
        if "instagram.com" in d:
            if not instagram and re.search(r"instagram\.com/[A-Za-z0-9_.]+/?$", l):
                instagram = l
        elif "facebook.com" in d:
            if not facebook and "/posts/" not in l and "/photos" not in l:
                facebook = l
        elif not any(x in d for x in DIRETORIOS) and nome_no_dominio(l, linha) and raiz(l) not in sites:
            sites.append(raiz(l))
    return sites[:2], instagram, facebook


_robots = {}


def pode_acessar(url):
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(url))
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            _, txt = http_get(base + "/robots.txt", timeout=10, tentativas=1)
            rp.parse(txt.splitlines())
        except Exception:
            rp.parse([])  # sem robots.txt: acesso permitido
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
RE_WHATS = re.compile(r"(?:wa\.me/|whatsapp\.com/send/?\?phone=)\+?(\d{10,13})")
RE_INSTA = re.compile(r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)/?")
RE_FACE = re.compile(r"https?://(?:www\.|pt-br\.|m\.)?facebook\.com/([A-Za-z0-9_.-]+)/?")


def email_valido(e):
    e = e.lower().strip(".")
    if re.search(r"\.(png|jpe?g|gif|svg|webp|css|js)$", e):
        return False
    return not any(x in e for x in ("example", "sentry", "wixpress", "seudominio", "email@", "nome@", "domain"))


def raspar_site(site):
    """Lê a página inicial e até 2 páginas de contato do mesmo domínio."""
    achados = {"emails": [], "whats": [], "instagram": None, "facebook": None, "textos": []}
    fila, vistos = [site], set()
    while fila and len(vistos) < 3:
        url = fila.pop(0)
        if url in vistos:
            continue
        vistos.add(url)
        if not pode_acessar(url):
            continue
        try:
            _, pagina = http_get(url, timeout=15, tentativas=1)
        except Exception:
            continue
        achados["textos"].append(normalizar(re.sub(r"<[^>]+>", " ", pagina))[:200_000])
        for e in RE_EMAIL.findall(pagina.replace("&#64;", "@").replace("[at]", "@")):
            if email_valido(e) and e.lower() not in achados["emails"]:
                achados["emails"].append(e.lower())
        for w in RE_WHATS.findall(pagina):
            num = limpar_telefone(w)
            if num and num not in achados["whats"]:
                achados["whats"].append(num)
        m = RE_INSTA.search(pagina)
        if m and not achados["instagram"] and m.group(1) not in ("p", "explore", "reel"):
            achados["instagram"] = f"https://instagram.com/{m.group(1)}"
        m = RE_FACE.search(pagina)
        if m and not achados["facebook"] and m.group(1) not in ("sharer", "sharer.php", "tr", "plugins", "dialog"):
            achados["facebook"] = f"https://facebook.com/{m.group(1)}"
        if url == site:
            for href in re.findall(r"href=[\"']([^\"'#]+)[\"']", pagina):
                if re.search(r"contato|contact|fale|atendimento", href, re.I):
                    absoluto = urllib.parse.urljoin(site, href)
                    if dominio(absoluto) == dominio(site) and absoluto not in fila:
                        fila.append(absoluto)
    return achados


def site_confere(textos, linha):
    """O site parece ser da empresa se o CNPJ, um telefone ou a cidade aparecem nele."""
    texto = " ".join(textos)
    digitos = so_digitos(texto)
    cnpj = so_digitos(linha["CNPJ"])
    if cnpj and (cnpj in digitos or cnpj[:8] in digitos):
        return True
    for campo in ("Telefone 1", "Telefone 2"):
        num = so_digitos(linha[campo])
        if num and num[-8:] in digitos:
            return True
    cidade = normalizar(linha["Cidade/UF"].split("/")[0])
    return bool(cidade) and cidade in texto


def adicionar_fonte(linha, fonte):
    if fonte not in linha["Fontes"]:
        linha["Fontes"] += f"; {fonte}"


def visitar_site(linha, site, anotar=True):
    """Devolve True se o site foi confirmado como da empresa e os contatos foram lidos."""
    reg = dominio_br(site)
    if reg and reg.get("status") != "REGISTERED":
        # Domínio .br livre ou vencido: o site não é mais da empresa (ou nunca foi).
        if anotar:
            linha["Observações"] = juntar(linha["Observações"], f"Domínio não registrado ou vencido: {site}")
        return False
    achados = raspar_site(site)
    if not achados["textos"]:
        if anotar:
            linha["Observações"] = juntar(linha["Observações"], f"Site não abriu ou bloqueia robôs: {site}")
        return False
    if not site_confere(achados["textos"], linha):
        # Nome igual não basta: há muitas empresas homônimas em outras cidades.
        if anotar:
            linha["Observações"] = juntar(linha["Observações"], f"Site com nome parecido, não confirmado (pode ser de outra cidade): {site}")
        return False
    linha["Site"] = site
    adicionar_fonte(linha, FONTE_SITE)
    if not linha["E-mail"] and achados["emails"]:
        linha["E-mail"] = achados["emails"][0]
    if achados["whats"]:
        linha["WhatsApp"] = formatar_telefone(achados["whats"][0])
        linha["WhatsApp (status)"] = "Confirmado (link no site)"
    linha["Instagram"] = linha["Instagram"] or achados["instagram"] or ""
    linha["Facebook"] = linha["Facebook"] or achados["facebook"] or ""
    return True


def juntar(*partes):
    return " ".join(p for p in partes if p).strip()


def enriquecer_com_busca(linha, uf):
    cidade = linha["Cidade/UF"].split("/")[0]
    links = busca_web(f"{linha['Nome']} {cidade} {uf}")
    sites, insta, face = classificar_links(links, linha)
    if not sites and normalizar(linha["Nome"]) != normalizar(linha["Razão social"]):
        time.sleep(PAUSA_BUSCA)
        s2, i2, f2 = classificar_links(busca_web(f"{linha['Razão social']} {cidade} {uf}"), linha)
        sites, insta, face = s2, insta or i2, face or f2
    if insta or face:
        linha["Instagram"] = linha["Instagram"] or insta or ""
        linha["Facebook"] = linha["Facebook"] or face or ""
        adicionar_fonte(linha, FONTE_BUSCA)
    return sites


def site_pelo_email(linha):
    """Um e-mail com domínio próprio (não gmail, hotmail...) indica o site."""
    if "@" in linha["E-mail"]:
        dom = linha["E-mail"].split("@")[-1]
        if dom not in DOMINIOS_EMAIL_GRATIS:
            return f"https://{dom}/"
    return None


def completar_whatsapp(linha):
    if linha["WhatsApp"]:
        return
    for campo in ("Telefone 1", "Telefone 2"):
        n = so_digitos(linha[campo])
        if n and eh_celular(n):
            linha["WhatsApp"] = linha[campo]
            linha["WhatsApp (status)"] = "Provável (é celular; não verificado)"
            return


# ---------------------------------------------------------------- Planilha

COLUNAS = [
    "Nome", "Razão social", "CNPJ", "Tipo", "Porte", "Atividade", "Início da atividade",
    "Endereço", "Bairro", "CEP", "Cidade/UF", "Telefone 1", "Telefone 2", "WhatsApp",
    "WhatsApp (status)", "E-mail", "Site", "Instagram", "Facebook", "Fontes",
    "Data da coleta", "Observações",
]


def montar_linha(emp, cidade, hoje):
    pf = eh_pessoa_fisica(emp)
    razao = re.sub(r"\s*\b\d{11}\b", "", emp.get("razao_social") or "").strip()  # MEI: tira o CPF
    fones = []
    for t in (emp.get("ddd_telefone_1"), emp.get("ddd_telefone_2")):
        n = limpar_telefone(t)
        if n and n not in fones:
            fones.append(n)
    end = " ".join(x for x in [emp.get("descricao_tipo_de_logradouro"), emp.get("logradouro")] if x)
    if emp.get("numero"):
        end += f", {emp['numero']}"
    if emp.get("complemento"):
        end += f" - {emp['complemento']}"
    c = emp["cnpj"]
    obs = ["Dados de pessoa física: cuidado redobrado (LGPD)."] if pf else []
    alvo = normalizar(cidade)
    for n in fones:
        cidades = cidades_do_ddd(n[:2])
        if cidades and alvo not in cidades:
            obs.append(f"Telefone com DDD {n[:2]}, de outra região: pode estar desatualizado.")
    return {
        "Nome": (emp.get("nome_fantasia") or razao).title(),
        "Razão social": razao,
        "CNPJ": f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}",
        "Tipo": "Pessoa física (MEI/empresário individual)" if pf else "Pessoa jurídica",
        "Porte": (emp.get("porte") or "").title(),
        "Atividade": emp.get("cnae_fiscal_descricao") or "",
        "Início da atividade": emp.get("data_inicio_atividade") or "",
        "Endereço": end.title(),
        "Bairro": (emp.get("bairro") or "").title(),
        "CEP": emp.get("cep") or "",
        "Cidade/UF": f"{cidade}/{emp.get('uf', '')}",
        "Telefone 1": formatar_telefone(fones[0]) if fones else "",
        "Telefone 2": formatar_telefone(fones[1]) if len(fones) > 1 else "",
        "WhatsApp": "",
        "WhatsApp (status)": "",
        "E-mail": (emp.get("email") or "").lower(),
        "Site": "",
        "Instagram": "",
        "Facebook": "",
        "Fontes": FONTE_RECEITA,
        "Data da coleta": hoje,
        "Observações": " ".join(obs),
    }


def texto_sobre(pedido, hoje):
    return [
        ["SOBRE ESTA LISTA"],
        ["Gerada em", hoje],
        ["Pedido", pedido],
        ["Ferramenta", f"busca-empresas {VERSAO} ({REPO})"],
        [""],
        ["FONTES (TODAS PÚBLICAS E GRATUITAS)"],
        ["IBGE", "servicodados.ibge.gov.br: código do município e da atividade (CNAE)"],
        ["Receita Federal", "Dados abertos do CNPJ, consultados via minhareceita.org (projeto aberto e gratuito)"],
        ["Busca web", "DuckDuckGo ou a busca do próprio Claude, só para achar o site e as redes sociais da empresa"],
        ["Site da empresa", "Página inicial e de contato, respeitando o robots.txt do site"],
        ["BrasilAPI", "brasilapi.com.br: situação do domínio .br no registro.br e cidades de cada DDD (sem cadastro)"],
        ["Não usado", "Google Maps (os termos de uso proíbem coleta automática), serviços pagos, chaves de API e qualquer fonte que exija cadastro"],
        [""],
        ["LGPD: LEIA ANTES DE USAR"],
        ["1", "Quem usa esta lista é o CONTROLADOR dos dados (LGPD, art. 5º, VI) e responde pelo uso que fizer dela."],
        ["2", "Dados de empresa (CNPJ, razão social) não são dados pessoais. Telefone, e-mail e nome de MEI ou empresário individual SÃO."],
        ["3", "Base legal sugerida para prospecção B2B: legítimo interesse (art. 7º, IX e art. 10), com teste de balanceamento documentado."],
        ["4", "Dado público pode ser tratado, mas respeitando a finalidade, a boa-fé e os direitos do titular (art. 7º, §§ 3º, 4º e 7º)."],
        ["5", "No primeiro contato: diga quem você é, de onde veio o contato e ofereça um jeito simples de não receber mais mensagens."],
        ["6", "Quem pedir para sair vai para uma lista de exclusão (opção --excluir nas próximas buscas)."],
        ["7", "Não venda nem repasse esta lista. Apague os contatos que não virarem relacionamento."],
        ["8", "Os nomes dos sócios (QSA) são descartados de propósito (minimização, art. 6º, III)."],
        ["9", "WhatsApp 'provável' só indica um celular. Respeite os termos do WhatsApp e não faça disparo em massa."],
        [""],
        ["Este aviso é orientativo e não substitui a análise do seu encarregado (DPO) ou advogado."],
    ]


def col_letra(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def sheet_xml(linhas, larguras, tabela=True):
    cols = "".join(f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>' for i, w in enumerate(larguras))
    rows = []
    for r, linha in enumerate(linhas, start=1):
        cells = []
        for c, v in enumerate(linha):
            v = "" if v is None else str(v)
            negrito = (tabela and r == 1) or (not tabela and len(linha) == 1 and v.isupper())
            estilo = ' s="1"' if negrito else ""
            cells.append(f'<c r="{col_letra(c)}{r}" t="inlineStr"{estilo}><is><t xml:space="preserve">{escape(v)}</t></is></c>')
        rows.append(f'<row r="{r}">{"".join(cells)}</row>')
    painel, filtro = "", ""
    if tabela and linhas:
        painel = '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        filtro = f'<autoFilter ref="A1:{col_letra(len(linhas[0]) - 1)}{len(linhas)}"/>'
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'{painel}<cols>{cols}</cols><sheetData>{"".join(rows)}</sheetData>{filtro}</worksheet>')


def salvar_xlsx(caminho, leads, sobre):
    larguras = [32, 36, 20, 22, 14, 28, 12, 36, 18, 10, 18, 16, 16, 16, 26, 30, 30, 34, 34, 40, 12, 40]
    ct = "application/vnd.openxmlformats-officedocument.spreadsheetml"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    arquivos = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/xl/workbook.xml" ContentType="{ct}.sheet.main+xml"/>'
            f'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="{ct}.worksheet+xml"/>'
            f'<Override PartName="/xl/worksheets/sheet2.xml" ContentType="{ct}.worksheet+xml"/>'
            f'<Override PartName="/xl/styles.xml" ContentType="{ct}.styles+xml"/></Types>'),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>'),
        "xl/workbook.xml": (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="{rel}">'
            '<sheets><sheet name="Leads" sheetId="1" r:id="rId1"/><sheet name="Fontes e LGPD" sheetId="2" r:id="rId2"/></sheets>'
            f'<definedNames><definedName name="_xlnm._FilterDatabase" localSheetId="0" hidden="1">Leads!$A$1:${col_letra(len(COLUNAS) - 1)}${len(leads) + 1}</definedName></definedNames></workbook>'),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/worksheet" Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{rel}/worksheet" Target="worksheets/sheet2.xml"/>'
            f'<Relationship Id="rId3" Type="{rel}/styles" Target="styles.xml"/></Relationships>'),
        "xl/styles.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'),
        "xl/worksheets/sheet1.xml": sheet_xml([COLUNAS] + [[l[c] for c in COLUNAS] for l in leads], larguras),
        "xl/worksheets/sheet2.xml": sheet_xml(sobre, [36, 120], tabela=False),
    }
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in arquivos.items():
            z.writestr(nome, conteudo)


def salvar(base, leads, pedido):
    hoje = dt.date.today().isoformat()
    salvar_xlsx(base + ".xlsx", leads, texto_sobre(pedido, hoje))
    with open(base + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(COLUNAS)
        for l in leads:
            w.writerow([l[c] for c in COLUNAS])


def ler_csv(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    faltando = [c for c in COLUNAS if linhas and c not in linhas[0]]
    if faltando:
        raise SystemExit(f"ERRO: o CSV não tem as colunas {', '.join(faltando)}. Use o CSV gerado por este script.")
    return [{c: (l.get(c) or "").strip() for c in COLUNAS} for l in linhas]


def ler_exclusoes(caminho):
    if not caminho:
        return set()
    with open(caminho, encoding="utf-8-sig") as f:
        return {so_digitos(linha) for linha in f if so_digitos(linha)}


def slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", normalizar(texto)).strip("-")[:40]


def resumo(leads, base, extra=""):
    def conta(campo):
        return sum(1 for l in leads if l[campo])

    confirmados = sum(1 for l in leads if l["WhatsApp (status)"].startswith("Confirmado"))
    pf = sum(1 for l in leads if l["Tipo"].startswith("Pessoa física"))
    sem_site = [l["Nome"] for l in leads if not l["Site"]]
    print(f"RESUMO: {len(leads)} empresas{extra}")
    print(f"  Telefone: {conta('Telefone 1')} | WhatsApp: {conta('WhatsApp')} (confirmado: {confirmados}) | "
          f"E-mail: {conta('E-mail')} | Site: {conta('Site')} | Instagram: {conta('Instagram')} | Facebook: {conta('Facebook')}")
    if pf:
        print(f"  Atenção: {pf} são MEI/empresário individual (dados de pessoa física).")
    print(f"  Sem site: {len(sem_site)}")
    print(f"  Planilha: {base}.xlsx")
    print(f"  CSV:      {base}.csv")


# ---------------------------------------------------------------- Modos

def modo_listar_cnae(termo):
    achados = buscar_cnaes(termo)
    if not achados:
        print(f"Nenhuma atividade CNAE com '{termo}'. Tente outra palavra.")
    for cod, desc in achados[:40]:
        print(f"{cod}  {desc}")
    if len(achados) > 40:
        print(f"... e mais {len(achados) - 40}. Use palavras mais específicas.")


def modo_buscar(args, p):
    if not (args.cidade and args.uf and (args.ramo or args.cnae)):
        p.error("informe --cidade, --uf e --ramo (ou --cnae)")
    limite = QTD_ABSOLUTA if args.permitir_mais else QTD_MAXIMA
    if args.qtd < 1 or args.qtd > limite:
        raise SystemExit(f"ERRO: --qtd deve ficar entre 1 e {limite}."
                         + ("" if args.permitir_mais else " Para mais, use --permitir-mais (demora e consome mais)."))

    uf = args.uf.upper()
    cod_mun, cidade = achar_municipio(args.cidade, uf)
    if args.cnae:
        cnaes = [so_digitos(c) for c in args.cnae.split(",") if so_digitos(c)]
    else:
        achados = buscar_cnaes(args.ramo)
        if not achados:
            raise SystemExit(f"ERRO: nenhuma atividade CNAE com '{args.ramo}'. Use --listar-cnae com outra palavra.")
        if len(achados) > 1:
            print(f"O ramo '{args.ramo}' combina com {len(achados)} atividades. Escolha e rode de novo com --cnae:")
            for cod, desc in achados[:25]:
                print(f"{cod}  {desc}")
            sys.exit(2)
        cnaes = [achados[0][0]]

    avisar(f"Buscando na Receita: CNAE {', '.join(cnaes)} em {cidade}/{uf}...")
    exclusoes = ler_exclusoes(args.excluir)
    todas, vistos = [], set()
    for cnae in cnaes:
        for emp in listar_empresas(cod_mun, cnae):
            if emp.get("situacao_cadastral") == 2 and emp["cnpj"] not in vistos and emp["cnpj"] not in exclusoes:
                vistos.add(emp["cnpj"])
                todas.append(emp)
    if not todas:
        raise SystemExit(f"Nenhuma empresa ativa encontrada para CNAE {', '.join(cnaes)} em {cidade}/{uf}.")

    # Prioriza quem tem telefone, depois quem tem nome fantasia, depois as mais antigas.
    todas.sort(key=lambda e: (
        not any(limpar_telefone(t) for t in (e.get("ddd_telefone_1"), e.get("ddd_telefone_2"))),
        not e.get("nome_fantasia"),
        e.get("data_inicio_atividade") or "9999",
    ))
    hoje = dt.date.today().isoformat()
    leads = [montar_linha(e, cidade, hoje) for e in todas[:args.qtd]]

    busca_ativa = not args.sem_web
    for i, l in enumerate(leads, 1):
        if args.sem_web:
            break
        avisar(f"[{i}/{len(leads)}] {l['Nome']}")
        candidatos = []
        if busca_ativa:
            try:
                candidatos = enriquecer_com_busca(l, uf)
            except BuscaBloqueada:
                avisar("   O DuckDuckGo bloqueou a busca automática; sigo sem busca web.")
                busca_ativa = False
            except Exception as e:
                avisar(f"   aviso: {e}")
            time.sleep(PAUSA_BUSCA)
        pelo_email = site_pelo_email(l)
        if pelo_email and pelo_email not in candidatos:
            candidatos.insert(0, pelo_email)
        for n, site in enumerate(candidatos):
            try:
                if visitar_site(l, site, anotar=(n == len(candidatos) - 1)):
                    if site != pelo_email:
                        adicionar_fonte(l, FONTE_BUSCA)
                    break
            except Exception as e:
                avisar(f"   aviso no site: {e}")
    for l in leads:
        completar_whatsapp(l)

    os.makedirs(args.saida, exist_ok=True)
    base = os.path.join(os.path.abspath(args.saida), f"leads_{slug(args.ramo or cnaes[0])}_{slug(cidade)}-{uf.lower()}_{hoje}")
    pedido = f"{args.ramo or 'CNAE ' + ', '.join(cnaes)} em {cidade}/{uf}, até {args.qtd} empresas"
    salvar(base, leads, pedido)
    extra = f" ativas de {len(todas)} encontradas ({cidade}/{uf}, CNAE {', '.join(cnaes)})"
    resumo(leads, base, extra)
    if not args.sem_web and not busca_ativa:
        print("  BUSCA_WEB_BLOQUEADA: complete os sites com outra busca e rode --enriquecer no CSV.")


def modo_enriquecer(caminho, sites_informados):
    """Visita os sites preenchidos no CSV (ou passados com --site) e extrai os contatos."""
    leads = ler_csv(caminho)
    for item in sites_informados or []:
        cnpj, _, url = item.partition("=")
        alvo = [l for l in leads if so_digitos(l["CNPJ"]) == so_digitos(cnpj)]
        if not alvo or not url.strip():
            raise SystemExit(f"ERRO: --site '{item}' inválido ou CNPJ fora da lista. Formato: CNPJ=https://site")
        alvo[0]["Site"] = url.strip()
        alvo[0]["Fontes"] = alvo[0]["Fontes"].replace(f"; {FONTE_SITE}", "")
    pendentes = [l for l in leads if l["Site"] and FONTE_SITE not in l["Fontes"]]
    avisar(f"{len(pendentes)} sites para visitar...")
    for i, l in enumerate(pendentes, 1):
        site = raiz(l["Site"])
        avisar(f"[{i}/{len(pendentes)}] {l['Nome']}: {site}")
        l["Site"] = ""
        adicionar_fonte(l, FONTE_BUSCA)
        try:
            visitar_site(l, site)
        except Exception as e:
            avisar(f"   aviso no site: {e}")
    for l in leads:
        if l["Instagram"] or l["Facebook"]:
            adicionar_fonte(l, FONTE_BUSCA)
        completar_whatsapp(l)
    base = os.path.splitext(os.path.abspath(caminho))[0]
    salvar(base, leads, f"lista enriquecida a partir de {os.path.basename(caminho)}")
    resumo(leads, base, f" ({len(pendentes)} sites visitados)")


def pasta_padrao():
    docs = Path.home() / "Documents"
    return str((docs if docs.is_dir() else Path.home()) / "Leads")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Lista de empresas por ramo e cidade, só com fontes públicas e gratuitas.")
    p.add_argument("--cidade", help="Nome do município, ex.: Taquara")
    p.add_argument("--uf", help="Sigla do estado, ex.: RS")
    p.add_argument("--ramo", help="Palavras do ramo, ex.: contabilidade (procurado na tabela CNAE do IBGE)")
    p.add_argument("--cnae", help="Código(s) CNAE de 7 dígitos separados por vírgula, ex.: 6920601")
    p.add_argument("--qtd", type=int, default=QTD_PADRAO, help=f"Quantidade de empresas (padrão {QTD_PADRAO}, máximo {QTD_MAXIMA})")
    p.add_argument("--permitir-mais", action="store_true", help=f"Libera até {QTD_ABSOLUTA} empresas (mais demorado)")
    p.add_argument("--sem-web", action="store_true", help="Só dados da Receita, sem busca web nem visita aos sites")
    p.add_argument("--excluir", help="Arquivo .txt com CNPJs que pediram para não ser contatados (um por linha)")
    p.add_argument("--saida", default=pasta_padrao(), help="Pasta onde salvar a planilha (padrão: Documentos/Leads)")
    p.add_argument("--listar-cnae", metavar="TERMO", help="Só mostra os códigos CNAE que combinam com o termo")
    p.add_argument("--enriquecer", metavar="CSV", help="Visita os sites preenchidos num CSV já gerado e completa os contatos")
    p.add_argument("--site", action="append", metavar="CNPJ=URL", help="Com --enriquecer: informa o site de uma empresa (pode repetir)")
    args = p.parse_args()

    if args.listar_cnae:
        modo_listar_cnae(args.listar_cnae)
    elif args.enriquecer:
        modo_enriquecer(args.enriquecer, args.site)
    else:
        modo_buscar(args, p)


if __name__ == "__main__":
    main()
