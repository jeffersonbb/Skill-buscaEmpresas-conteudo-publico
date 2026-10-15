---
name: busca-empresas
description: Monta listas de leads de empresas por ramo e cidade no Brasil (ex.: "20 escritórios de contabilidade em Taquara/RS"), usando só fontes públicas e gratuitas (IBGE, dados abertos do CNPJ da Receita Federal, busca web e o site da própria empresa). Gera planilha Excel/CSV com telefone, WhatsApp, e-mail, site e redes sociais, com a fonte e a data de cada dado e um aviso de LGPD. Use quando o usuário pedir "lista de empresas", "leads", "prospecção", "contatos de empresas", "empresas de [ramo] em [cidade]", "quero falar com [tipo de empresa] na [cidade]" ou pedir telefone, WhatsApp ou e-mail de empresas de uma região.
---

# Busca de empresas (fontes públicas e gratuitas)

Gera uma lista de leads B2B de um ramo numa cidade brasileira. O trabalho pesado é feito pelo script `scripts/buscar_leads.py`, que só usa a biblioteca padrão do Python, sem chave de API, cadastro nem serviço pago.

## Regra de ouro: economizar tokens

Buscas amplas gastam muitos tokens e tempo. Por isso:

1. **Sempre confirme o pedido antes de rodar**: cidade, UF, ramo e quantidade. Se faltar algo, pergunte. Não presuma a cidade nem a quantidade.
2. **Quantidade**: o padrão é 20. Pode ir até 50, mas avise que demora mais (cerca de 10 a 15 segundos por empresa). Acima de 50, recomende dividir em buscas menores. Só use `--permitir-mais` se o usuário insistir depois do aviso.
3. **Recuse recortes amplos demais** ("todas as empresas do RS", "todos os ramos", várias cidades de uma vez) e proponha um recorte menor: uma cidade e um ramo por vez.
4. **Nunca leia a planilha inteira** para o contexto. O script imprime um RESUMO curto: use só ele. Abra o CSV apenas se o usuário pedir para ver algo específico, e mesmo assim só as colunas necessárias.
5. **Não faça buscas web por conta própria, empresa por empresa**, sem o usuário pedir. O script já faz isso de graça.

Ao confirmar o pedido, inclua uma linha como esta:
> "Vou buscar até 20 escritórios de contabilidade em Taquara/RS. Leva uns 3 a 5 minutos. Buscas maiores consomem mais tokens, por isso começo por 20."

## Passo a passo

### 1. Descobrir o código da atividade (CNAE)

Se o ramo for comum (contabilidade, advogado, dentista, academia, salão de beleza, pet shop, imobiliária, farmácia, restaurante, oficina mecânica...), o script entende direto. Para conferir ou quando houver dúvida:

```bash
python scripts/buscar_leads.py --listar-cnae "contabilidade"
```

Se aparecer mais de uma atividade, mostre as opções ao usuário e pergunte qual usar. Dá para passar várias com vírgula: `--cnae 4771701,4771702`.

### 2. Rodar a busca

```bash
python scripts/buscar_leads.py --cidade "Taquara" --uf RS --ramo contabilidade --qtd 20
```

- Use o caminho completo do script (a pasta desta skill). No Windows, se `python` não existir, tente `py`. No Mac ou Linux, `python3`.
- A planilha vai para a pasta **Documentos/Leads** (criada sozinha). Não pergunte onde salvar: informe o caminho ao entregar. Use `--saida "<pasta>"` só se o usuário pedir outra pasta.
- `--sem-web`: só dados da Receita (rápido, menos completo). Use se o usuário tiver pressa.
- `--excluir arquivo.txt`: CNPJs que pediram para não ser contatados (um por linha). Pergunte se o usuário tem essa lista quando ele já tiver feito buscas antes.
- O script demora: rode com tempo limite de pelo menos 10 minutos.

O que o script faz, em ordem:
1. Acha o município no IBGE e o CNAE.
2. Lista as empresas na base aberta do CNPJ (via minhareceita.org) e mantém só as **ativas**.
3. Prioriza as que têm telefone e nome fantasia.
4. Para cada uma, busca o site e as redes no DuckDuckGo e visita o site (respeitando o robots.txt) para achar e-mail e link de WhatsApp.
5. **Só aceita um site se ele citar a cidade, o CNPJ ou o telefone da empresa.** Sites com nome parecido mas sem essa confirmação vão para "Observações" como "não confirmado", porque há muitas empresas homônimas em outras cidades.
6. Grava `.xlsx` (aba "Leads" e aba "Fontes e LGPD") e `.csv`.

### 3. Se a busca web for bloqueada

Se o resumo trouxer `BUSCA_WEB_BLOQUEADA`, o DuckDuckGo limitou as consultas. Diga isso ao usuário e ofereça duas saídas:
- rodar de novo mais tarde só o enriquecimento; ou
- ele mesmo informar sites que conhece.

Para visitar sites informados:

```bash
python scripts/buscar_leads.py --enriquecer "<arquivo.csv>" --site "11.381.387/0001-90=https://www.exemplo.com.br"
```

O `--enriquecer` também visita qualquer site digitado à mão na coluna "Site" do CSV.

### 4. Apresentar o resultado

Responda curto:
- os números do RESUMO (quantas com telefone, WhatsApp, e-mail, site);
- o caminho da planilha;
- se houver, quantas são **MEI ou empresário individual** (dados de pessoa física);
- o lembrete de LGPD abaixo, em 2 ou 3 linhas.

Explique as colunas de WhatsApp só se perguntarem:
- **Confirmado**: o link de WhatsApp está no site da empresa.
- **Provável**: o telefone da Receita é celular, mas não foi verificado.

## LGPD: sempre lembrar

Antes da primeira busca da conversa ou ao entregar a lista, lembre em poucas linhas:
- Quem usa a lista é o **controlador** dos dados e responde pelo uso.
- Telefone e e-mail de **MEI ou empresário individual são dados pessoais**. Base sugerida para prospecção B2B: **legítimo interesse** (art. 7º, IX e art. 10 da LGPD), com teste de balanceamento.
- No primeiro contato, diga de onde veio o contato e ofereça **opt-out**. Quem pedir para sair vai para a lista do `--excluir`.
- Não vender nem repassar a lista. Não fazer disparo em massa no WhatsApp.

Detalhes e fundamentos: `references/lgpd.md`. Leia esse arquivo só se o usuário fizer perguntas de LGPD.

**Limites que esta skill respeita e você também deve respeitar:**
- Não buscar dados de **sócios** ou funcionários (nome, CPF, celular pessoal, LinkedIn pessoal). O script descarta o quadro de sócios de propósito. Se o usuário quiser conhecer os sócios de **uma** empresa específica, indique a skill `investiga-empresa` (um alvo por vez, fora da lista de leads).
- Não usar o Google Maps por coleta automática: os termos de uso proíbem.
- Não usar serviços pagos nem pedir chaves de API.
- Não inventar contatos. Se não achou, a célula fica vazia.

## Limitações conhecidas

- Telefone e e-mail da Receita podem estar desatualizados. A base aberta raramente traz e-mail.
- Escritórios pequenos muitas vezes não têm site; aí a linha fica só com os dados da Receita e as redes encontradas.
- O DuckDuckGo pode limitar as consultas em buscas grandes ou repetidas.
- A minhareceita.org é um projeto voluntário, sem garantia de disponibilidade. Se estiver fora do ar, tente mais tarde.
