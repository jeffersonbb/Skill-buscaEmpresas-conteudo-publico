# Novidades

## 1.1.1 (2026-10-15)

- `investiga-empresa` 1.0.1:
  - o relatório agora sai em **Word (.docx)**, gerado só com a biblioteca padrão do Python, com uma cópia `.md` editável ao lado (`--docx` gera o Word de novo);
  - pasta padrão **Documentos/Investigações**, sem precisar perguntar onde salvar;
  - sites que só listam sócios (ex.: páginas `/socios/`) deixam de aparecer como menções.
- `busca-empresas` 1.0.2: pasta padrão **Documentos/Leads**.

## 1.1.0 (2026-10-15)

Nova skill **`investiga-empresa`** (1.0.0): levantamento de uma empresa ou de um sócio, um alvo por vez.

- Pelo CNPJ: dados cadastrais, quadro de sócios e administradores e as outras empresas de cada sócio (ativas e baixadas, com cargo e data de entrada).
- Pelo nome da empresa: encontra os CNPJs candidatos.
- Pelo nome de uma pessoa: empresas em que ela é sócia, separando homônimos pelo CPF parcial da base aberta. Mais preciso com o CNPJ de uma empresa dela ou o CPF.
- Links públicos da web (LinkedIn da empresa e possíveis perfis dos sócios, notícias), sem coletar o LinkedIn.
- Fontes: minhareceita.org e a API aberta da CNPJá (reserva e e-mails), mais o DuckDuckGo. Tudo gratuito.
- Relatório em Markdown com a finalidade do levantamento no topo (`--finalidade`) e aviso de uso restrito. CPF e endereço completo de MEI nunca aparecem.

README: novo passo a passo para instalar o Claude Code (Windows, Mac e Linux) e o Python.

`busca-empresas` 1.0.1: indica a `investiga-empresa` quando o usuário pede os sócios de uma empresa.

## 1.0.0 (2026-10-14)

Primeira versão.

- Skill `busca-empresas`: lista de leads por ramo e cidade a partir do IBGE, dos dados abertos do CNPJ (via minhareceita.org), da busca no DuckDuckGo e do site da empresa.
- Planilha Excel com as abas "Leads" e "Fontes e LGPD", mais um CSV.
- WhatsApp marcado como "confirmado" (link no site) ou "provável" (celular do cadastro).
- Site só é aceito se citar a cidade, o CNPJ ou o telefone da empresa, para evitar homônimos de outras cidades.
- Limite de 20 empresas por padrão e 50 no máximo, com avisos de consumo de tokens.
- Opções `--excluir` (lista de quem pediu para sair), `--sem-web` e `--enriquecer`.
- Nomes dos sócios e CPF de MEI são descartados (minimização de dados).
