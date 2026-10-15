---
name: investiga-empresa
description: Levantamento minucioso de UMA empresa ou de UM sócio no Brasil, só com fontes públicas, gratuitas e sem cadastro (dados abertos do CNPJ via minhareceita.org, BrasilAPI, API aberta da CNPJá e busca web). Mostra os dados cadastrais, quem são os sócios e administradores, em que outras empresas cada sócio aparece e links públicos (LinkedIn, notícias), num relatório em Word (.docx). Use quando o usuário quiser "conhecer uma empresa", "quem são os sócios da empresa X", "de quais empresas Fulano é sócio", "levantamento da empresa", "due diligence", "OSINT de empresa", "vou fazer uma apresentação na empresa X", "perfil dos sócios" ou "o sócio tem LinkedIn?". Não serve para listas de leads (para isso, use a busca-empresas).
---

# Investigação de empresa ou sócio (fontes públicas e gratuitas)

Levantamento de **um alvo por vez**, para conhecer uma empresa ou uma pessoa antes de uma reunião, apresentação ou parceria. O trabalho pesado fica no script `scripts/investigar.py`, que só usa a biblioteca padrão do Python, sem chave de API, cadastro nem serviço pago.

**Não é lista de leads.** Se o usuário quiser várias empresas de um ramo ou cidade, use a skill `busca-empresas`. O relatório não vira planilha nem alimenta listas de contato.

## Antes de rodar

1. **Confirme o alvo e a finalidade em uma linha.** Exemplo: "Vou levantar a empresa X e os sócios dela, para preparar a sua apresentação. Leva de 1 a 3 minutos." Se a finalidade não estiver clara, pergunte. Passe a finalidade ao script com `--finalidade "..."`: ela sai no topo do relatório.
2. **Um alvo por vez.** Recuse listas de pessoas ou empresas ("investiga esses 30 nomes", "todos os sócios de empresas de Taquara") e explique: investigação em massa de pessoas foge do legítimo interesse e vira perfilamento.
3. **Recuse finalidades indevidas**, mesmo com dados públicos: localizar ou vigiar uma pessoa, assédio, cobrança fora dos canais legais, levantar a vida pessoal (família, endereço residencial, saúde, religião, política, orientação sexual). O foco é **a vida profissional e societária**.

## Passo a passo

### 1. Rodar o script no modo certo

Use o caminho completo do script (a pasta desta skill). No Windows, se `python` não existir, tente `py`. No Mac ou Linux, `python3`. Rode com tempo limite de pelo menos 10 minutos. O relatório vai para a pasta **Documentos/Investigações** (criada sozinha). Não pergunte onde salvar: informe o caminho ao entregar. Use `--saida "<pasta>"` só se o usuário pedir outra pasta.

#### Pelo CNPJ (o mais completo)

```bash
python scripts/investigar.py --cnpj 33.000.167/0001-01 --finalidade "preparar reunião comercial"
```

Traz os dados cadastrais, o quadro de sócios e administradores, as **outras empresas de cada sócio** (ativas e baixadas, com cargo e data de entrada) e links da web: o LinkedIn e as redes da empresa e possíveis perfis no LinkedIn dos sócios.

- `--max-socios N`: quantos sócios pesquisar (padrão 15). Empresas grandes, como S.A., têm muitos administradores.
- `--max-socios-web N`: quantos sócios ganham busca web (padrão 5; cada um leva uns 15 segundos).
- `--sem-web`: só dados da Receita (mais rápido).

#### Só com o nome da empresa

```bash
python scripts/investigar.py --empresa "Nome da Empresa" --cidade Taquara --uf RS
```

Só procura o CNPJ e lista os candidatos. **Mostre os candidatos ao usuário e pergunte qual é.** Depois rode com `--cnpj`. Se nada aparecer, peça o CNPJ.

#### Pelo nome de uma pessoa

Em ordem de precisão:

```bash
python scripts/investigar.py --socio "Nome Completo" --cnpj-ref <CNPJ de uma empresa dela> --finalidade "..."
python scripts/investigar.py --socio "Nome Completo" --cpf <CPF, se o usuário souber>
python scripts/investigar.py --socio "Nome Completo"
```

A base aberta mostra só 6 dígitos do CPF do sócio, e esse CPF parcial se repete entre pessoas diferentes. Por isso o script exige **nome igual e CPF parcial igual** ao mesmo tempo. Só com o nome, ele procura na web empresas ligadas ao nome e descobre o CPF parcial a partir delas. É menos preciso, por isso:
- prefira pedir ao usuário uma empresa onde a pessoa é sócia;
- se o RESUMO avisar **homônimos**, mostre as pessoas encontradas (cada uma com a empresa onde apareceu) e pergunte qual é a certa antes de aprofundar;
- o CPF completo, se o usuário informar, é usado só para gerar o CPF parcial e não aparece no relatório.

### 2. Ler o resultado

O script imprime um **RESUMO** curto e grava dois arquivos: `investigacao_<alvo>_<data>.docx`, que é o relatório para o usuário, e o `.md` de mesmo nome, que é a fonte editável. Use o RESUMO. Abra o `.md` só para responder ao que o usuário perguntar ou para escrever o perfil (passo 3).

- `BUSCA_WEB_BLOQUEADA`: o DuckDuckGo limitou as consultas. O relatório sai sem parte dos links. Ofereça rodar de novo mais tarde.
- Se a minhareceita estiver fora do ar, o script tenta a BrasilAPI (que guarda consultas recentes por 24 horas) e depois a API aberta da CNPJá (5 consultas por minuto). A busca de outras empresas do sócio depende da minhareceita; se ela falhar, a seção fica marcada como não consultada.

### 3. Perfil dos sócios (só se o usuário pedir)

Quando o usuário quiser saber "o que a pessoa faz" ou ter o perfil para a reunião:
- Use os títulos dos links do LinkedIn e das menções no relatório. O título de resultado do LinkedIn costuma trazer o cargo atual ("Nome - Cargo - Empresa | LinkedIn").
- Se precisar de mais, faça **no máximo 2 buscas web por sócio**, focadas na vida profissional (cargo, formação, palestras, entrevistas, prêmios, notícias da empresa).
- **Não abra nem colete o LinkedIn** por automação: os termos do site proíbem. Só use o que aparece no resultado da busca e sugira ao usuário abrir o perfil por conta própria.
- Escreva o perfil **no `.md` do relatório**, numa seção "Perfil profissional" de cada sócio, marcando o que é confirmado (Receita) e o que é provável (web). A finalidade já sai no topo; se o usuário mudar de ideia sobre ela, atualize essa linha. Depois de editar, gere o Word de novo:
  ```bash
  python scripts/investigar.py --docx "<caminho do .md>"
  ```
- No `.md`, use só o Markdown simples que o conversor entende: títulos `#` a `####`, parágrafos, listas com `- `, tabelas com `|`, `**negrito**`, `_itálico_` e links `[texto](url)`.
- Ao entregar, deixe claro que os links da web podem ser de homônimos.

### 4. Apresentar

Responda curto:
- a empresa, a situação cadastral e quantos sócios tem;
- para cada sócio, quantas outras empresas tem e o que chama atenção (ex.: consultoria própria, empresas baixadas recentemente, sócio em concorrentes);
- o caminho do relatório `.docx`;
- o lembrete de LGPD abaixo, em 2 linhas.

## LGPD: sempre lembrar

- Nome, cargo, faixa etária e vínculos societários de pessoas físicas **são dados pessoais**, mesmo sendo públicos (art. 7º, §§ 3º e 4º: o uso tem que respeitar a finalidade e a boa-fé).
- Base sugerida: **legítimo interesse** (art. 7º, IX e art. 10) para preparar reunião, avaliar parceiro ou fornecedor, ou fazer due diligence. Finalidade concreta, só o necessário, nada de repasse.
- O relatório é **de uso restrito**: não publicar, não repassar, apagar quando não precisar mais. Ele já sai com esse aviso.

Detalhes e fundamentos: `references/lgpd.md`. Leia esse arquivo só se o usuário fizer perguntas de LGPD.

**Limites que o script respeita e você também deve respeitar:**
- Nunca mostrar CPF (nem o parcial) no relatório. Endereço completo de MEI e empresário individual é omitido, porque pode ser residencial.
- Nada de vida pessoal: família, endereço de casa, telefone pessoal, dados sensíveis (art. 5º, II).
- Sem coleta automática do LinkedIn ou de outras redes; sem serviços pagos; sem bases compradas.
- **Só fontes livres de cadastro.** Não sugira nem use fontes que peçam chave, conta ou e-mail (ex.: API do Portal da Transparência, CNPJá paga), para que qualquer pessoa use a skill sem configurar nada.
- Não inventar vínculos. Se não achou, diga que não achou.

## Limitações conhecidas

- A base aberta da Receita é atualizada mensalmente e pode estar desatualizada. Empresas baixadas continuam aparecendo.
- MEI e empresário individual não têm quadro de sócios na base aberta.
- Sócios estrangeiros e sócios sem CPF na base não têm outras empresas pesquisadas.
- A busca só pelo nome depende de a web citar o CNPJ de uma empresa da pessoa. Nomes muito comuns geram homônimos.
- A API aberta da CNPJá tem limite de 5 consultas por minuto.
- O domínio do site é conferido no registro.br (via BrasilAPI) só para endereços `.br`.
