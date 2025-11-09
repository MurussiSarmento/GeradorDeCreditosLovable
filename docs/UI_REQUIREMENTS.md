# UI_REQUIREMENTS - Especificação Detalhada da Interface Gráfica

## Layout Principal

```
┌─────────────────────────────────────────────────────────┐
│ Mail.tm Email Manager - v1.0                      [_][□][×]
├─────────────────────────────────────────────────────────┤
│ File | Help                                             │
├─────────────────────────────────────────────────────────┤
│ ┌─Generator─┬─Inbox─┬─Settings─┬─Status─────────────┐  │
│ │                                                     │  │
│ │ [Tab Content]                                       │  │
│ │                                                     │  │
│ └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Dimensões e Responsividade
- **Tamanho inicial:** 1200×800 pixels
- **Tamanho mínimo:** 800×600 pixels
- **Redimensionável:** Sim, todos elementos respondem
- **Janelas flutuantes:** Manter proporção ao redimensionar

## ABA 1: GENERATOR (Gerador de Emails)

### Layout
```
┌─────────────────────────────────────────────┐
│ GERADOR DE EMAILS                           │
├─────────────────────────────────────────────┤
│                                             │
│ Quantidade de Emails:                       │
│ ┌─────────────────────────────────────────┐ │
│ │  [◀ 10 ▶] (spinner de 1 a 10000)       │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ ☐ Usar domínios únicos                     │
│   (Cada email terá domínio diferente)      │
│                                             │
│ ☐ Auto-delete após (segundos):             │
│   ┌──────────────┐                          │
│   │ 3600         │ (ou não deletar)         │
│   └──────────────┘                          │
│                                             │
│            ┌──────────────────────┐         │
│            │  ► GERAR EMAILS      │         │
│            └──────────────────────┘         │
│                                             │
│ Progresso: [████████░░░░░░░░] 65%           │
│ 65 / 100 emails criados                     │
│ ETA: ~15 segundos                           │
│ Velocidade: 4.3 emails/seg                  │
│                                             │
├─────────────────────────────────────────────┤
│ Email              | Domain    | Criado em  │
├─────────────────────────────────────────────┤
│ abc123@mail.tm    │ mail.tm   │ há 2 min   │
│ xyz789@mail.tm    │ mail.tm   │ há 1 min   │
│ def456@domain.com │ domain.com│ agora      │
│ ...                                         │
├─────────────────────────────────────────────┤
│ Filtro: [____________] Buscar...            │
│ Ordenar: [▼ Data]  [Copiar] [Exportar]     │
└─────────────────────────────────────────────┘
```

### Componentes Detalhados

#### 1. Spinner Quantidade
```python
# Widget: QSpinBox
- Mínimo: 1
- Máximo: 10000
- Step: 1
- Validação em tempo real
- Se valor inválido, mostrar erro red
- Tooltip: "Número de emails a criar (1-10000)"
```

#### 2. Checkboxes
```python
# Unique Domains
- Label: "Usar domínios únicos"
- Tooltip: "Se marcado, cada email usará domínio diferente"
- Enabled: Sempre
- Default: Checked

# Auto-Delete
- Label: "Auto-delete após (segundos)"
- Input spinbox: 300-86400
- Tooltip: "Deletar email automaticamente após X segundos (0 = nunca)"
- Enabled: Se checkbox marcado
- Default: 3600 (1 hora)
```

#### 3. Botão GERAR EMAILS
```python
# QPushButton
- Text: "► GERAR EMAILS"
- Size: Grande (200px width, 50px height)
- Color: Verde (#27AE60) quando disponível
- Hover: Mais claro (#229954)
- Pressed: Mais escuro (#1E8449)
- Disabled: Cinza durante criação
- Font: Bold, 14px
- Ícone: ✓ ou ⚙️
```

#### 4. Barra de Progresso
```python
# QProgressBar
- Estilo: Gradiente horizontal
- Color: Azul → Verde
- Mostrar porcentagem
- Animar movimento
- Text: "XX% - YY/ZZ emails"
```

#### 5. Tabela de Emails
```python
# QTableWidget
Colunas:
  1. Checkbox (select múltiplo)
  2. Email (monospace, copiável)
  3. Domain
  4. Criado em (tempo relativo: "há 5 min")
  5. Status (badge: "ativo" verde, "expirado" vermelho)
  6. Ações (botões: copiar, verificar, deletar)

Sorting:
  - Clicável em headers
  - Asc/desc indicador
  
Context Menu (right-click):
  - Copiar email
  - Copiar todos
  - Abrir inbox
  - Deletar
  - Exportar selecionados

Selection:
  - Multi-select com Ctrl/Cmd
  - Checkbox "Select All"
```

#### 6. Filtros e Busca
```python
# QLineEdit
- Placeholder: "Buscar por email ou domínio..."
- Busca em tempo real
- Case-insensitive
- Resultado: mostra X de Y itens

# Combo Sort
- Opções: Data, Domain, Email, Status
- Asc/Desc toggle
```

#### 7. Botões de Ação
```python
[Copiar Todos] [Exportar CSV] [Deletar Selecionados] [Atualizar]

Copiar Todos:
  - Copia todos emails para clipboard
  - Um por linha
  - Notificação: "✓ XX emails copiados"

Exportar CSV:
  - Abre dialog salvar arquivo
  - Default name: "emails_2025-11-06.csv"
  - Formato: email,domain,created_at,status

Deletar Selecionados:
  - Confirmação: "Deletar XX emails?"
  - Progresso durante deleção
  - Feedback após conclusão

Atualizar:
  - Recarregar lista do banco
```

## ABA 2: INBOX (Verificador de Mensagens)

### Layout
```
┌────────────────────────────────────────────────────────┐
│ INBOX - VERIFICADOR DE MENSAGENS                       │
├────────────────────────────────────────────────────────┤
│                                                        │
│ Email: [▼ Selecione um email...]                       │
│ ┌──────────────────────────────────────────────────┐  │
│ │ abc123@mail.tm (criado há 15 min)                │  │
│ │ xyz789@mail.tm (criado há 8 min)                 │  │
│ │ def456@mail.tm (criado há 2 min)                 │  │
│ └──────────────────────────────────────────────────┘  │
│                                                        │
│ [🔄 Verificar Agora] [↻ Auto-verificar a cada 30s]   │
│                                                        │
│ Estatísticas: 5 mensagens | 2 não lidas | 1 código   │
│                                                        │
│ ┌─────────────────────────────────────────────────┐  │
│ │De           │ Assunto         │ Recebido │ Código│  │
│ ├─────────────────────────────────────────────────┤  │
│ │noreply@... │ Verify email    │ há 5 min │ 123456│  │ ← verde
│ │support@... │ Welcome!        │ há 2 min │ ❌    │  │
│ │admin@...   │ Reset password  │ agora    │ TOKEN │  │ ← amarelo
│ │...         │ ...             │ ...      │ ...   │  │
│ └─────────────────────────────────────────────────┘  │
│                                                        │
│ ┌────────── VISUALIZADOR ────────────────────────┐   │
│ │ De: noreply@example.com                        │   │
│ │ Assunto: Verify your email                     │   │
│ │ Recebido: 2025-11-06 20:05:00                 │   │
│ │                                                 │   │
│ │ Your verification code is:                     │   │
│ │                                                 │   │
│ │ ┌─────────────────────────────────┐           │   │
│ │ │      123456     [◐ Copiar]      │           │   │
│ │ └─────────────────────────────────┘           │   │
│ │ Tipo: OTP (6 dígitos) | Confiança: 99%        │   │
│ │                                                 │   │
│ │ ------- CONTEXTO --------                      │   │
│ │ Your verification code is: 123456              │   │
│ │                                                 │   │
│ │ Do not share this code with anyone!            │   │
│ └────────────────────────────────────────────────┘   │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### Componentes Detalhados

#### 1. Seletor de Email
```python
# QComboBox + Custom Widget
- Items: Todos emails da app
- Placeholder: "Selecione um email..."
- Mostrar: "email (criado há X tempo)"
- Filtro searchable: Sim
- On change: Carregar mensagens
```

#### 2. Botões de Ação
```python
[🔄 Verificar Agora]
  - Imediatamente buscar novas mensagens
  - Mostrar progresso
  - Desabilitar durante requisição

[☑ Auto-verificar a cada 30s]
  - Checkbox com opções
  - Valores: 10s, 30s (default), 60s, 300s
  - Background: Rodar verificação periodicamente
  - Spinner enquanto verificando
```

#### 3. Estatísticas
```python
Cards com informações:
- Total de mensagens: X
- Não lidas: X
- Com código extraído: X
- Última verificação: há X segundos
```

#### 4. Tabela de Mensagens
```python
# QTableWidget
Colunas:
  1. De (email truncado com tooltip)
  2. Assunto (truncado, monospace)
  3. Recebido em (tempo relativo)
  4. Código Extraído (verde se sim, vermelho se não)
  5. Tipo (otp_6, url_token, etc)

Row Colors:
  - Não lida: Background mais claro
  - Com código: Destaque verde
  - Sem código: Normal

Double-click: Abrir visualizador

Sorting: Clicável em headers
```

#### 5. Visualizador de Mensagem
```python
# Seção direita ou modal
Mostra:
- De: ...
- Assunto: ...
- Recebido: ...
- [Botão: Marcar como lido]

Corpo:
- Renderizado (HTML ou texto)
- Scroll se necessário
- Códigos extraídos highlighted em AMARELO

Códigos Extraídos:
- Cada código em card/badge
- Botão copiar para clipboard
- Tipo de código
- Nível de confiança (%)
- Contexto (linhas antes/depois)
- Link "Ver mensagem completa" se truncado
```

## ABA 3: SETTINGS (Configurações)

### Layout
```
┌──────────────────────────────────────────┐
│ CONFIGURAÇÕES                            │
├──────────────────────────────────────────┤
│                                          │
│ ▼ GERAL                                  │
│   Tema: [◉ Claro ◯ Escuro ◯ Sistema]  │
│   Idioma: [▼ Português]                 │
│   ☑ Iniciar minimizado na bandeja       │
│   ☑ Notificações ao encontrar código    │
│                                          │
│ ▼ MAIL.TM                                │
│   URL Base: [_________________]          │
│   [Testar Conexão] ✓ Conectado          │
│   ☑ Usar cache de domínios              │
│   TTL Cache: [3600] segundos             │
│                                          │
│ ▼ EXTRAÇÃO DE CÓDIGOS                   │
│   Padrões a usar:                        │
│   ☑ OTP 6 dígitos                       │
│   ☑ OTP 4 dígitos                       │
│   ☑ URLs de verificação                 │
│   ☑ Tokens                              │
│   ☑ Recovery codes                      │
│   ☑ Emails mencionados                  │
│   ☐ Google Authenticator                │
│   Padrão regex customizado:              │
│   [_____________________________]         │
│   [Testar Padrão] com exemplo:          │
│   [_____________________________]         │
│                                          │
│ ▼ API LOCAL                              │
│   Porta: [5000]                          │
│   Host: [0.0.0.0]                       │
│   Status: [⚪ Parado]  [Iniciar]        │
│   URL Acesso: http://localhost:5000     │
│   API Key: [Gerar Nova]                 │
│   [Copiar]                              │
│                                          │
│ ▼ BANCO DE DADOS                         │
│   Localização: ./data/emails.db         │
│   Tamanho: 45.2 MB                       │
│   [Backup Agora] [Limpar Dados Antigos] │
│   Retenção: [30] dias                   │
│                                          │
│                    [Salvar] [Cancelar]   │
└──────────────────────────────────────────┘
```

## ABA 4: STATUS (Monitoramento)

### Layout
```
┌──────────────────────────────────────────────┐
│ STATUS & MONITORAMENTO                       │
├──────────────────────────────────────────────┤
│                                              │
│ ┌─────────────┬─────────────┬──────────────┐ │
│ │ Emails      │ Mensagens   │ Códigos      │ │
│ │ Ativos: 42  │ Não Lidas: 5│ Encontrados: 3
│ │             │ Processadas │              │ │
│ │             │ 127         │              │ │
│ └─────────────┴─────────────┴──────────────┘ │
│                                              │
│ GRÁFICOS:                                    │
│ ┌──────────────────────────────┐            │
│ │ Emails Criados (24h)         │            │
│ │ [Gráfico de linha/barras]    │            │
│ │ 42 total                     │            │
│ └──────────────────────────────┘            │
│                                              │
│ ┌──────────────────────────────┐            │
│ │ Códigos por Tipo             │            │
│ │ OTP 6D: 45 | URL: 12 | Token │            │
│ │ [Gráfico de pizza]           │            │
│ └──────────────────────────────┘            │
│                                              │
│ LOG EM TEMPO REAL:                          │
│ ┌──────────────────────────────────────────┐│
│ │ [INFO] Email abc123 criado com sucesso   ││
│ │ [INFO] Mensagem recebida em xyz789       ││
│ │ [SUCCESS] Código 123456 extraído         ││
│ │ [WARNING] Falha ao conectar Mail.tm      ││
│ │ [ERROR] Database error: connection lost  ││
│ │ ...                                      ││
│ └──────────────────────────────────────────┘│
│ [Limpar Log] [Filtro: ▼ Todos]             │
│                                              │
└──────────────────────────────────────────────┘
```

## Dialogs e Modais

### 1. Confirmação de Deleção
```
┌─────────────────────────────────┐
│ ⚠️  CONFIRMAR DELEÇÃO            │
├─────────────────────────────────┤
│                                 │
│ Tem certeza que deseja deletar  │
│ 5 emails?                       │
│                                 │
│ Esta ação não pode ser desfeita!│
│                                 │
│           [Cancelar] [Deletar]  │
└─────────────────────────────────┘
```

### 2. Progresso de Operação
```
┌─────────────────────────────────┐
│ ⏳ Criando Emails...              │
├─────────────────────────────────┤
│                                 │
│ [████████░░░░░░] 55%            │
│                                 │
│ Progresso: 55 de 100 emails     │
│ Tempo restante: ~25 segundos    │
│ Velocidade: 2.2 emails/seg      │
│                                 │
│                    [Cancelar]   │
└─────────────────────────────────┘
```

### 3. Export para CSV
```
┌─────────────────────────────────┐
│ 📁 Salvar Emails Como CSV       │
├─────────────────────────────────┤
│ Nome: [emails_2025-11-06      ] │
│ Localização: /home/user/Desktop │
│ Formato: [▼ CSV]                │
│ ☑ Incluir headers               │
│ ☑ Incluir timestamps            │
│                                 │
│         [Cancelar] [Salvar]     │
└─────────────────────────────────┘
```

## Comportamentos de UX

### Notificações (Toast)
```
Posição: Canto inferior direito
Duração: 4 segundos
Tipos:
  ✓ Sucesso (verde): "2 emails copiados"
  ℹ Info (azul): "Verificação iniciada"
  ⚠️  Warning (amarelo): "Taxa limitada, aguarde"
  ❌ Erro (vermelho): "Falha ao criar email"
```

### Indicadores de Carregamento
```
- Spinner giratório: Durante requisições
- Barra de progresso: Operações em batch
- Disable de botões: Durante processamento
- Cursor: Mudar para "aguarde" durante operação
```

### Atalhos de Teclado
```
Ctrl+C / Cmd+C: Copiar selecionado
Ctrl+A / Cmd+A: Select all
Ctrl+Q / Cmd+Q: Sair
Ctrl+R / Cmd+R: Atualizar lista
F5: Verificar emails (Inbox tab)
Enter: Executar ação primária
Delete: Deletar selecionado (com confirmação)
```

---

**Versão:** 1.0  
**Última Atualização:** 2025-11-06