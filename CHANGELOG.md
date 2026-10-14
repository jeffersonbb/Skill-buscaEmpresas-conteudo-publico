# Novidades

## 1.0.0 (2026-10-14)

Primeira versão.

- Skill `busca-empresas`: lista de leads por ramo e cidade a partir do IBGE, dos dados abertos do CNPJ (via minhareceita.org), da busca no DuckDuckGo e do site da empresa.
- Planilha Excel com as abas "Leads" e "Fontes e LGPD", mais um CSV.
- WhatsApp marcado como "confirmado" (link no site) ou "provável" (celular do cadastro).
- Site só é aceito se citar a cidade, o CNPJ ou o telefone da empresa, para evitar homônimos de outras cidades.
- Limite de 20 empresas por padrão e 50 no máximo, com avisos de consumo de tokens.
- Opções `--excluir` (lista de quem pediu para sair), `--sem-web` e `--enriquecer`.
- Nomes dos sócios e CPF de MEI são descartados (minimização de dados).
