# 📦 Versões do Projeto

Este arquivo lista as versões publicadas do projeto, com o commit de referência, data e um resumo das principais mudanças.

## 0.1Trae (2025-11-08)
- Branch: `release/0.1Trae`
- Commit de referência: `2951ab4` (merge que inclui as mudanças da UI)
- Link: https://github.com/MurussiSarmento/GeradorDeCreditosLovable/commit/2951ab4
- Principais mudanças:
  - UI ProxyValidation: adiciona tabela de proxies com colunas chave (IP, porta, protocolo, país, anonimato, latência, validade).
  - Filtros na UI: país, validade, protocolo, latência máx (local), ordenação.
  - Ações em lote: validar selecionados, excluir inválidos, exportar (JSON/CSV), copiar selecionados.
  - Integração com endpoints `/api/v1/proxies` (listar, validar, exportar) e tratamento de rate limit.
  - Atualização de `todoListProcyValidator.md` com itens concluídos.
  - Remoção do parâmetro não suportado `max_response_time` dos endpoints; filtragem local de latência aplicada.

---

Observação: versões futuras devem incluir tag (`git tag`) e seção neste arquivo com mudanças consolidadas.