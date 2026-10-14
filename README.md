# Busca de empresas com conteúdo público

Skill gratuita para o **Claude** que monta listas de leads de empresas brasileiras por **ramo e cidade**, como "20 escritórios de contabilidade em Taquara/RS". Usa **somente fontes públicas e gratuitas** e já vem com orientações de **LGPD**.

Você pede em português e recebe uma planilha Excel (e um CSV) com, quando disponíveis:

| Coluna | De onde vem |
|---|---|
| Nome, razão social, CNPJ, porte, atividade, endereço | Cadastro aberto do CNPJ (Receita Federal) |
| Telefone 1 e 2 | Cadastro do CNPJ |
| WhatsApp | Link de WhatsApp no site da empresa (**confirmado**) ou celular do cadastro (**provável**) |
| E-mail | Cadastro do CNPJ ou site da empresa |
| Site, Instagram, Facebook | Busca web e site da empresa |
| Fontes e data da coleta | Registradas em cada linha |

Só entram empresas com **situação cadastral ativa**. A planilha tem uma segunda aba, **"Fontes e LGPD"**, com as fontes usadas e os cuidados legais.

---

## Fontes usadas (todas gratuitas)

| Fonte | Para quê |
|---|---|
| [IBGE, API de localidades e CNAE](https://servicodados.ibge.gov.br/api/docs) | Código do município e da atividade econômica (CNAE) |
| [Dados abertos do CNPJ, Receita Federal](https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/consultas/dados-publicos-cnpj), consultados pela API gratuita [minhareceita.org](https://minhareceita.org) | Lista de empresas, situação cadastral, telefone, endereço |
| [DuckDuckGo](https://duckduckgo.com) | Encontrar o site e as redes sociais de cada empresa |
| Site da própria empresa | E-mail, link de WhatsApp e redes. O robots.txt é respeitado |

**O que NÃO é usado:**
- Google Maps por coleta automática (os termos de uso do Google proíbem);
- serviços pagos;
- bases compradas;
- chaves de API;
- LinkedIn de pessoas.

Nenhum cadastro é necessário e ninguém paga nada além do uso normal do próprio Claude.

## ⚠️ Consumo de tokens

Cada busca consome tokens do **seu** plano do Claude. Para não gastar à toa, a skill:
- **confirma** cidade, ramo e quantidade antes de rodar;
- usa **20 empresas por padrão** e **no máximo 50** por busca;
- **recusa pedidos amplos demais** ("todas as empresas do RS") e sugere um recorte menor;
- deixa o trabalho pesado para um script Python, que não gasta tokens, e só lê o resumo.

Recomendação: **uma cidade e um ramo por vez**. Uma busca de 20 empresas leva de 3 a 5 minutos.

## LGPD: leia antes de usar

- Quem usa a lista é o **controlador** dos dados (LGPD, art. 5º, VI) e responde pelo uso que fizer dela.
- Dados de pessoa jurídica (CNPJ, razão social) não são dados pessoais. **Telefone, e-mail e nome de MEI ou empresário individual são.** A planilha indica quais linhas são de pessoa física.
- Base legal mais usada para prospecção B2B: **legítimo interesse** (art. 7º, IX e art. 10), com teste de balanceamento documentado.
- Os **nomes dos sócios são descartados** de propósito (minimização, art. 6º, III).
- No primeiro contato:
  - diga quem você é e de onde veio o contato;
  - ofereça um jeito simples de **não receber mais mensagens**;
  - registre quem pedir para sair e use a opção `--excluir` nas próximas buscas.
- **Não venda nem repasse** a lista. **Não faça disparo em massa** no WhatsApp.

Guia completo: [`plugins/busca-empresas/skills/busca-empresas/references/lgpd.md`](plugins/busca-empresas/skills/busca-empresas/references/lgpd.md).

> Material orientativo. Não substitui a análise do seu encarregado (DPO) ou advogado.

---

## Como instalar

### Opção 1: Claude Code (recomendada; atualiza por comando)

No Claude Code, digite:

```
/plugin marketplace add jeffersonbb/Skill-buscaEmpresas-conteudo-publico
/plugin install busca-empresas@skills-conteudo-publico
```

Reinicie o Claude Code. Pronto.

**Para atualizar** quando houver novidades:

```
/plugin marketplace update skills-conteudo-publico
```

Depois abra `/plugin`, vá em **Installed** e atualize o `busca-empresas`, se aparecer uma versão nova. As novidades ficam no [CHANGELOG](CHANGELOG.md).

Requisito: **Python 3.9 ou mais novo** instalado no computador ([python.org](https://www.python.org/downloads/); no Windows, marque *"Add Python to PATH"* na instalação). Não precisa instalar nenhum pacote extra.

### Opção 2: Claude no navegador ou no app (claude.ai)

1. Baixe o arquivo **`busca-empresas.zip`** da página [Releases](../../releases/latest).
2. No Claude, abra **Configurações → Capacidades** e ative a **execução de código**.
3. Na mesma tela, libere o **acesso à internet** da execução de código para **todos os domínios**. A skill precisa acessar o IBGE, a minhareceita.org, o DuckDuckGo e os sites das empresas.
4. Em **Skills**, clique em enviar e escolha o `busca-empresas.zip`.

**Para atualizar:** baixe o zip da versão nova em Releases, apague a skill antiga e envie de novo.

> Se a sua conta só permitir alguns domínios, a skill ainda funciona no modo **só Receita**: peça "sem busca web".

### Opção 3: Sem Claude (só o script)

Precisa só do Python. Baixe o repositório (botão verde **Code → Download ZIP**), abra o terminal na pasta `plugins/busca-empresas/skills/busca-empresas/scripts` e rode:

```bash
python buscar_leads.py --cidade "Taquara" --uf RS --ramo contabilidade --qtd 20
```

Outras opções:

```bash
python buscar_leads.py --listar-cnae "academia"            # descobre o código da atividade
python buscar_leads.py --cidade Gramado --uf RS --cnae 9313100 --qtd 15
python buscar_leads.py ... --sem-web                       # só dados da Receita (rápido)
python buscar_leads.py ... --excluir nao-contatar.txt      # pula CNPJs que pediram para sair
python buscar_leads.py --enriquecer leads.csv --site "11.381.387/0001-90=https://site.com.br"
python buscar_leads.py --help                              # todas as opções
```

---

## Como pedir ao Claude

- "Quero 20 escritórios de contabilidade em Taquara/RS"
- "Me passa 15 academias em Gramado, RS, só com dados da Receita"
- "Lista de 10 pet shops em Novo Hamburgo com WhatsApp"
- "Refaz a busca de contabilidade em Taquara, excluindo os CNPJs do arquivo nao-contatar.txt"

## Como o script garante que o site é da empresa certa

Muitas empresas têm nomes iguais em cidades diferentes. Um site só entra na planilha se citar a **cidade**, o **CNPJ** ou o **telefone** da empresa. Se tiver só o nome parecido, ele aparece em "Observações" como **não confirmado**, e nenhum contato dele é usado.

## Limitações

- Telefone e e-mail do cadastro da Receita podem estar desatualizados, e o e-mail raramente aparece na base aberta.
- Empresas pequenas muitas vezes não têm site.
- O DuckDuckGo pode limitar consultas em buscas grandes ou repetidas. Nesse caso, a planilha sai só com os dados da Receita, e você pode completar depois com `--enriquecer`.
- A minhareceita.org é um projeto voluntário, sem garantia de disponibilidade.

## Estrutura do repositório

```
.claude-plugin/marketplace.json           catálogo de plugins (para o Claude Code)
plugins/busca-empresas/
  .claude-plugin/plugin.json              dados do plugin
  skills/busca-empresas/
    SKILL.md                              instruções para o Claude
    scripts/buscar_leads.py               script de coleta (Python, sem dependências)
    references/lgpd.md                    guia de LGPD
```

Novas skills serão adicionadas em `plugins/` e listadas no `marketplace.json`.

## Créditos

- [minha-receita](https://codeberg.org/cuducos/minha-receita), de Eduardo Cuducos: API aberta dos dados do CNPJ.
- [IBGE](https://servicodados.ibge.gov.br/api/docs): APIs de localidades e CNAE.

## Licença

[MIT](LICENSE): use, copie e modifique à vontade, mantendo o aviso de licença.
