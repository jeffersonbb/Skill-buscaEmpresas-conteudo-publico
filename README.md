# Busca de empresas com conteúdo público

Skills gratuitas para o **Claude**, em português, que usam só fontes públicas e gratuitas:

| Skill | Para quê |
|---|---|
| [**busca-empresas**](#busca-empresas-lista-de-leads) | Lista de leads por ramo e cidade, em planilha |
| [**investiga-empresa**](#investiga-empresa-conhecer-uma-empresa-ou-um-sócio) | Levantamento de **uma** empresa ou **um** sócio: quem são os sócios, em que outras empresas cada um aparece, LinkedIn e notícias |

Nunca usou o Claude Code? Comece pelo [passo a passo de instalação](#primeiro-passo-instalar-o-claude-code).

---

## busca-empresas: lista de leads

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

### Fontes usadas (todas gratuitas)

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
- LinkedIn de pessoas (para conhecer os sócios de uma empresa específica, use a [investiga-empresa](#investiga-empresa-conhecer-uma-empresa-ou-um-sócio)).

Nenhum cadastro é necessário e ninguém paga nada além do uso normal do próprio Claude.

### ⚠️ Consumo de tokens

Cada busca consome tokens do **seu** plano do Claude. Para não gastar à toa, a skill:
- **confirma** cidade, ramo e quantidade antes de rodar;
- usa **20 empresas por padrão** e **no máximo 50** por busca;
- **recusa pedidos amplos demais** ("todas as empresas do RS") e sugere um recorte menor;
- deixa o trabalho pesado para um script Python, que não gasta tokens, e só lê o resumo.

Recomendação: **uma cidade e um ramo por vez**. Uma busca de 20 empresas leva de 3 a 5 minutos.

### LGPD: leia antes de usar

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

## investiga-empresa: conhecer uma empresa ou um sócio

Para preparar uma reunião, uma apresentação ou avaliar um parceiro. **Um alvo por vez**, sem planilha: o resultado é um relatório em Markdown.

| Você informa | Você recebe |
|---|---|
| **CNPJ** | Dados cadastrais, sócios e administradores (cargo, desde quando, faixa etária), as **outras empresas de cada sócio**, LinkedIn e redes da empresa, possíveis perfis dos sócios no LinkedIn e notícias |
| **Nome da empresa** (e cidade) | Os CNPJs candidatos, para você escolher |
| **Nome de uma pessoa** | As empresas em que ela é sócia (ativas e baixadas) e possíveis perfis na web |

Como a base aberta mostra só parte do CPF do sócio, e essa parte se repete entre pessoas, o script só junta empresas com **nome igual e CPF parcial igual**. Se houver homônimos, o relatório separa cada pessoa. Para mais precisão, informe uma empresa onde a pessoa é sócia.

**Fontes (todas gratuitas):**
- [dados abertos do CNPJ](https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/consultas/dados-publicos-cnpj), pela [minhareceita.org](https://minhareceita.org);
- a [API aberta da CNPJá](https://cnpja.com/api/open), sem cadastro, com limite de 5 consultas por minuto, usada como reserva e para e-mails;
- o DuckDuckGo (só títulos e links; o LinkedIn **não** é coletado).

**LGPD:** nomes, cargos e vínculos societários de pessoas físicas são dados pessoais, mesmo públicos. Use só para uma finalidade concreta (reunião, due diligence, avaliar parceiro), com base no **legítimo interesse**. Não repasse o relatório e apague quando não precisar mais. A skill recusa investigações em massa e não levanta vida pessoal; CPF e endereço completo de MEI não aparecem. Guia: [`plugins/investiga-empresa/skills/investiga-empresa/references/lgpd.md`](plugins/investiga-empresa/skills/investiga-empresa/references/lgpd.md).

Como pedir ao Claude:
- "Quero conhecer a empresa 12.345.678/0001-90 antes da reunião de quinta"
- "Quem são os sócios da Padaria Pão Quente, de Taquara/RS?"
- "De quais empresas a Maria da Silva Souza é sócia? Ela é sócia da 12.345.678/0001-90"
- "Os sócios dessa empresa têm LinkedIn? Me faz um perfil profissional deles"

Sem Claude, na pasta `plugins/investiga-empresa/skills/investiga-empresa/scripts`:

```bash
python investigar.py --cnpj 12.345.678/0001-90
python investigar.py --empresa "Padaria Pão Quente" --cidade Taquara --uf RS
python investigar.py --socio "Maria da Silva Souza" --cnpj-ref 12345678000190
python investigar.py --help
```

---

## Primeiro passo: instalar o Claude Code

O Claude Code é o Claude que roda no terminal do seu computador. É por ele que as skills deste repositório são instaladas e atualizadas com um comando. Se você já tem, pule para [Como instalar as skills](#como-instalar-as-skills).

**Você precisa de:**
- um plano pago do Claude: **Pro, Max, Team ou Enterprise**, ou uma conta do Console da Anthropic. O plano gratuito do claude.ai **não inclui** o Claude Code;
- Windows 10 (versão 1809) ou mais novo, macOS 13 ou mais novo, ou Linux (Ubuntu 20.04+, Debian 10+);
- 4 GB de memória RAM e internet.

### 1. Abrir o terminal

- **Windows:** clique no menu Iniciar, digite **PowerShell** e abra o **Windows PowerShell**. A linha começa com `PS C:\Users\SeuNome>`. Não precisa abrir como administrador.
- **Mac:** abra o **Terminal** (Aplicativos → Utilitários, ou pesquise "Terminal" no Spotlight).
- **Linux:** abra o terminal da sua distribuição.

### 2. Colar o comando de instalação

**Windows (PowerShell):**

```powershell
irm https://claude.ai/install.ps1 | iex
```

**Windows (Prompt de Comando/CMD**, a linha começa com `C:\` sem o `PS`):

```batch
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

**Mac e Linux:**

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

A instalação não mostra uma barra de progresso. Espere terminar, **feche o terminal e abra outro**, e confira:

```bash
claude --version
```

Se aparecer um número de versão, deu certo. Se aparecer "claude não é reconhecido", veja a [ajuda oficial de instalação](https://code.claude.com/docs/en/troubleshoot-install).

> **Windows:** recomendamos instalar também o [Git for Windows](https://git-scm.com/downloads/win) (é só ir clicando em "Next"). Sem ele o Claude Code também funciona, usando o PowerShell.

Alternativa no Windows: `winget install Anthropic.ClaudeCode` (essa versão não se atualiza sozinha; para atualizar, use `winget upgrade Anthropic.ClaudeCode`).

### 3. Entrar com a sua conta

No terminal, digite:

```bash
claude
```

Na primeira vez, o navegador abre para você entrar com a sua conta do Claude. Depois disso, é só digitar `claude` sempre que quiser usar. A instalação pelo comando acima se atualiza sozinha.

> Prefere não usar o terminal? Existe o [aplicativo Claude para computador](https://claude.com/download), que também roda o Claude Code. Os comandos `/plugin` abaixo são para o Claude Code no terminal.

Guia oficial completo (em inglês): [code.claude.com/docs/en/setup](https://code.claude.com/docs/en/setup).

### 4. Instalar o Python (para as skills deste repositório)

As skills usam scripts em Python. Baixe o **Python 3.9 ou mais novo** em [python.org](https://www.python.org/downloads/). No Windows, marque **"Add Python to PATH"** na primeira tela da instalação. Não precisa instalar nenhum pacote extra.

---

## Como instalar as skills

### Opção 1: Claude Code (recomendada; atualiza por comando)

No Claude Code, digite:

```
/plugin marketplace add jeffersonbb/Skill-buscaEmpresas-conteudo-publico
/plugin install busca-empresas@skills-conteudo-publico
/plugin install investiga-empresa@skills-conteudo-publico
```

Instale só a que quiser.

Reinicie o Claude Code. Pronto.

**Para atualizar** quando houver novidades:

```
/plugin marketplace update skills-conteudo-publico
```

Depois abra `/plugin`, vá em **Installed** e atualize cada skill, se aparecer uma versão nova. As novidades ficam no [CHANGELOG](CHANGELOG.md).

Requisito: o **Python** instalado (veja o [passo 4](#4-instalar-o-python-para-as-skills-deste-repositório) acima).

### Opção 2: Claude no navegador ou no app (claude.ai)

1. Baixe o arquivo **`busca-empresas.zip`** ou **`investiga-empresa.zip`** da página [Releases](../../releases/latest).
2. No Claude, abra **Configurações → Capacidades** e ative a **execução de código**.
3. Na mesma tela, libere o **acesso à internet** da execução de código para **todos os domínios**. A skill precisa acessar o IBGE, a minhareceita.org, a CNPJá, o DuckDuckGo e os sites das empresas.
4. Em **Skills**, clique em enviar e escolha o zip.

**Para atualizar:** baixe o zip da versão nova em Releases, apague a skill antiga e envie de novo.

> Se a sua conta só permitir alguns domínios, a skill ainda funciona no modo **só Receita**: peça "sem busca web".

### Opção 3: Sem Claude (só o script da busca-empresas)

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

## Como pedir ao Claude (busca-empresas)

- "Quero 20 escritórios de contabilidade em Taquara/RS"
- "Me passa 15 academias em Gramado, RS, só com dados da Receita"
- "Lista de 10 pet shops em Novo Hamburgo com WhatsApp"
- "Refaz a busca de contabilidade em Taquara, excluindo os CNPJs do arquivo nao-contatar.txt"

## Como a busca-empresas garante que o site é da empresa certa

Muitas empresas têm nomes iguais em cidades diferentes. Um site só entra na planilha se citar a **cidade**, o **CNPJ** ou o **telefone** da empresa. Se tiver só o nome parecido, ele aparece em "Observações" como **não confirmado**, e nenhum contato dele é usado.

## Limitações da busca-empresas

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
plugins/investiga-empresa/
  .claude-plugin/plugin.json
  skills/investiga-empresa/
    SKILL.md
    scripts/investigar.py                 levantamento de empresa ou sócio
    references/lgpd.md                    LGPD para levantamento de pessoas
```

Novas skills serão adicionadas em `plugins/` e listadas no `marketplace.json`.

## Créditos

- [minha-receita](https://codeberg.org/cuducos/minha-receita), de Eduardo Cuducos: API aberta dos dados do CNPJ.
- [IBGE](https://servicodados.ibge.gov.br/api/docs): APIs de localidades e CNAE.
- [CNPJá](https://cnpja.com/api/open): API aberta de consulta de CNPJ.

## Licença

[MIT](LICENSE): use, copie e modifique à vontade, mantendo o aviso de licença.
