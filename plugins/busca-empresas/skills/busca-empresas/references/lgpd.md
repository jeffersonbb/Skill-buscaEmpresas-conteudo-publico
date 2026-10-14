# LGPD e prospecção B2B com dados públicos

Referência para responder dúvidas do usuário. Os artigos citados são da Lei nº 13.709/2018 (LGPD).

## O que é e o que não é dado pessoal na lista

| Dado | É dado pessoal? | Por quê |
|---|---|---|
| CNPJ, razão social, porte, atividade de **pessoa jurídica** | Não | A LGPD protege pessoa natural (art. 1º e art. 5º, I) |
| Telefone e e-mail **genéricos da empresa** (contato@, recepção) | Em geral não | Não identificam uma pessoa |
| Nome, telefone e e-mail de **MEI ou empresário individual** | **Sim** | A empresa se confunde com a pessoa física |
| Celular ou e-mail com nome de uma pessoa (joao@...) | **Sim** | Identifica uma pessoa natural |
| Nome dos sócios (QSA) | **Sim** | Por isso o script descarta |

## Base legal

- **Legítimo interesse** (art. 7º, IX e art. 10) é a base mais usada para prospecção B2B. Exige:
  - finalidade legítima e concreta (oferecer um serviço relacionado à atividade da empresa);
  - uso só dos dados estritamente necessários (art. 10, § 1º);
  - transparência (art. 10, § 2º);
  - respeito às legítimas expectativas do titular;
  - teste de balanceamento documentado (o Guia de Legítimo Interesse da ANPD traz um modelo).
- **Dados de acesso público** (art. 7º, § 3º), como o cadastro aberto do CNPJ: o tratamento deve considerar a finalidade, a boa-fé e o interesse público que justificaram a divulgação.
- **Dados tornados manifestamente públicos pelo titular** (art. 7º, § 4º), como o contato que a empresa põe no próprio site: dispensam consentimento, mas os direitos do titular e os princípios continuam valendo.
- **Uso para nova finalidade** (art. 7º, § 7º): só com propósito legítimo e específico e preservando os direitos do titular.

## Princípios mais relevantes (art. 6º)

- **Finalidade e adequação**: usar o contato para algo compatível com a atividade da empresa.
- **Necessidade e minimização**: não coletar mais que o necessário (por isso sem sócios e sem CPF).
- **Transparência**: dizer de onde veio o contato.
- **Qualidade dos dados**: registrar a fonte e a data da coleta (a planilha já faz isso).

## Boas práticas para o primeiro contato

1. Identifique-se (nome, empresa, CNPJ).
2. Diga de onde veio o contato: "encontrei seu contato no cadastro público do CNPJ" ou "no site da empresa".
3. Seja breve e relevante para a atividade da empresa.
4. Ofereça uma saída simples: "Se não quiser receber novos contatos, é só responder SAIR."
5. Registre quem pediu para sair e use o `--excluir` nas próximas buscas.

## Direitos do titular (art. 18)

Se um MEI ou empresário individual pedir:
- **Acesso**: diga quais dados você tem e de onde vieram (a planilha registra isso).
- **Eliminação ou oposição**: apague e inclua na lista de exclusão.
- **Prazo**: responda sem demora. O art. 19, II prevê até 15 dias para a declaração completa.

## WhatsApp

- Os termos do WhatsApp proíbem mensagens automáticas ou em massa não solicitadas.
- Prefira um primeiro contato individual. Se usar o WhatsApp Business, respeite as políticas da plataforma.

## Retenção

- Guarde só enquanto houver negociação ou relacionamento.
- Apague os contatos que não responderam depois de um prazo razoável que você definir (ex.: 6 meses).

## Fontes usadas e por que são permitidas

| Fonte | Natureza | Observação |
|---|---|---|
| IBGE (servicodados.ibge.gov.br) | API pública oficial | Códigos de município e de atividade (CNAE) |
| Receita Federal, dados abertos do CNPJ | Publicação oficial (Lei de Acesso à Informação e política de dados abertos) | Acessada pela API gratuita minhareceita.org |
| DuckDuckGo | Buscador público | Só para achar o endereço do site e das redes |
| Site da empresa | Informação publicada pela própria empresa | O script respeita o robots.txt |

**Não usadas:**
- Google Maps por coleta automática (os termos proíbem);
- bases compradas;
- serviços pagos;
- LinkedIn de pessoas.

> Este material é orientativo e não substitui a análise do seu encarregado (DPO) ou advogado.
