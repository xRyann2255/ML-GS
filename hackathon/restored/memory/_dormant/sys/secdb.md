---
domain: sys
subject: secdb
title: SecDB — Platform Architecture, Slang, Procmon, Database Patterns
created: 2026-01-01
updated: 2026-03-30
tags: [secdb, slang, platform, gs-internal, risk, pnl, booking, procmon]
status: dormant
source: GS EngHub (enghub-solutions/secdb, well-architected-platform-docs/secdb)
---

# SecDB Platform

## Visão Geral

SecDb é o sistema central de booking, risk e P&L do Goldman Sachs. É um **banco de dados distribuído de objetos financeiros** com uma linguagem de programação própria (Slang). A plataforma suporta trades, posições, precificação, risco e toda a cadeia de processamento financeiro da firma.

## Arquitetura Fundamental

### Database como Key-Value Store
- SecDb databases são essencialmente **key-value stores**
- **Keys**: strings ASCII de 31 caracteres (Security Names)
- **Values**: listas ordenadas de dados binários codificados
- Encoding: **streaming** (serialização) / **unstreaming** (deserialização)
- Diferente de gRPC streaming — aqui é binary encoding

### Modelo de Consistência — Eventual Consistency
- SecDb segue **eventual consistency**, NÃO é ACID
- Bancos de dados físicos são organizados em **rings** (topologia estrela, apesar do nome)
- Write em um DB físico → replicado para os outros DBs do ring via **secsync**
- Propagação global: segundos, não minutos
- **NÃO há locking nativo** (two-phase commit não existe)
- Tentativa de criar locks via objetos: **não funciona** (pode gerar conflitos no próprio lock)

### Write Conflicts
- Quando múltiplas write transactions ao mesmo objeto chegam de fontes diferentes "ao mesmo tempo":
  - DB não sabe qual aplicar
  - Cria **conflict object** (estado travado)
  - **Nenhuma atualização é aplicada** até resolução manual humana
  - Conflicts bloqueiam transações subsequentes → cascata de problemas
- Notificação via email quando conflict ocorre
- **Resolução deve ser imediata**

### Transactions (T maiúsculo — SecDB-specific)
- Cada mensagem ao banco é uma **Transaction**
- Transaction é **atômica no DB físico**, mas **NÃO atômica pelo ring**
- NÃO é ACID: atomicidade local, eventual consistency global
- **secsync** envia Transactions entre DBs como pacotes atômicos
- Bundling operações em uma Transaction reduz tráfego e carga

#### Boas práticas de Transaction
```slang
Check( Transaction( "Team rota" )   // nome descritivo e único
{
    ForEach( Sec, Secs )
        Check( UpdateSecurity( Sec ) );
} );
```
- **Sempre** usar Transaction blocks ao atualizar múltiplos objetos
- Dar nomes **descritivos e únicos** às Transactions (evitar "write", "update")
- Usar `TransactionCommit( parts_threshold, size_threshold )` para controlar tamanho
- Usar `TransactionAbort` para controlar atomicidade parcial
- Wrap Transaction em `Check()` para error handling

## UFOs, Value Types e Graph

### UFO (Universal Financial Object)
- Unidade fundamental no SecDb
- Cada objeto tem um **Security Name** (31 chars ASCII) como identificador único
- Objetos contêm **Value Types (VTs)** — atributos calculados ou armazenados

### Value Types (VTs)
- Dois tipos:
  - **Instream VTs**: dados armazenados (persistidos) no banco — binary encoded
  - **Calculated VTs**: derivados em runtime a partir de outros VTs
- VTs são o mecanismo principal de acesso a dados e computação
- Cada VT tem um nome, tipo de retorno e implementação (Slang function ou code)

### Graph Framework
- Sistema de dependência entre VTs
- Calculações são **lazy** e **cached** — VT só é computado quando requisitado
- Mudanças em VTs de entrada invalidam automaticamente VTs dependentes
- **Graph nodes** representam VTs no grafo de dependência

## Slang — Linguagem de Programação

### Características
- Linguagem proprietária do SecDb
- Suporta funções, controle de fluxo e estruturas de programa
- Tipagem forte (argumentos e retornos declarados)
- Integração com SecDb database (leitura/escrita de objetos)

### Scripts
- **_PROCM** scripts: entry points para Procmon (scheduling)
- **_LIB** scripts: bibliotecas de business logic (testáveis, cobertura de código)
- **_CFG** scripts: configurações
- **_UT** scripts: unit tests

### Boas práticas
- Nunca usar `Print` (vai para stdout, interfere com reports) → usar `Procmon::Message()` (vai para stderr)
- `Pricing Date("Security Database")` e `@Procmon::Pricing Date Get()` retornam a data agendada (não wall clock)
- Business logic em `_LIB`, não em `_PROCM`
- IDE: VS Code com extensão Slang

### Integrações
- **Python**: via `python-slang` (call Slang from Python)
- **Java**: via JSI (Java Slang Integration)
- **Slang-IMSL**: integração com bibliotecas matemáticas

## Procmon — Scheduling & Process Management

### Conceito
- Sistema de agendamento e monitoramento de processos em SecDb
- Processos configurados via **proc files** (não scripts)
- Controle via **ProcFellow** (editor/deploy) e **Procnosticator** (monitoramento)

### Estrutura de um Proc File

```
Master:      ep                           # master do processo (ep, fx, irp...)
Directory:   ep/secdb/arch/test           # hierarquia determina forest e permissões
Process:     ep/secdb/arch/test/example   # nome completo (dashes, não espaços)
PSRP Region: secdb_arch_emea             # preferir PSRP sobre hosts fixos
System Acct: p2secdbinfra                 # p2id com permissões necessárias
```

### Elementos-chave
- **Master**: contexto do job (ep, fx, irp) — preferir mesmo master de dependências
- **Forest**: determinado pelo diretório; controla permissões de execução
- **PSRP** (preferred): abstrai hardware, protege contra mudanças de máquina
- **TEMPLATE file**: configuração master para tudo rodando no diretório
- **Dependencies**: preferir sobre time-based start times; usar em vez de polling
- **Notifyees**: usar grupo/DL, não indivíduos
- **Keytab**: configurar em `_CFG Procmon Keytab Settings`

### _PROCM Script — Boilerplate

```slang
// Gerado pelo boilerplate generator
// Script Type: Process (prefixo _PROCM)

// 1. Kerberos auth via Procmon::Initialize Environment
// 2. Argumentos via Argv::GetArguments (tipados e validados)
// 3. Logic delegada para _LIB (não inline)
// 4. Try/catch com Exit(0) = sucesso, Exit(1) = falha
//    NUNCA Exit(137) = OOM, Exit(139) = segfault (reservados Linux)
```

### Comunicação com Procmon
- **Exit(0)** = sucesso → dependent jobs podem iniciar
- **Exit(N≠0)** = falha → job marcado como failed
- **Try block**: garante que exceções não-tratadas causam Exit(1)
- **Logging**: `Procmon::Message()` (stderr com timestamps)

## Naming — Convenções de Nomes de Objetos

### Estratégias de Naming

| Estratégia | Descrição | Melhor para |
|---|---|---|
| **Semantic Name** | Nome descritivo claro (ex: `LDN 22May24 Eq VOD.L B1`) | Objetos mutáveis; market data |
| **Perry's Hammer** | Nome = hash (SHA1) do conteúdo | Objetos imutáveis (enforces imutabilidade) |
| **ID-based** | Prefixo + unique ID (ex: `ISSUE 10567-620`) | Objetos com identidade única |
| **Semantic + Mush + Collision Counter** | Implied Name com hash parcial | Tradeables (padrão do SecDb) |

### Regras de naming
- Keys são **31 caracteres ASCII** — espaço limitado
- Usar **prefixo único** para evitar colisões com outros sistemas
- Gerar nomes em **funções** (não hardcoded)
- Retornar nome semântico via **Implied Name VT**
- Para unique IDs: `_Lib Database Unique ID` (baixo volume) ou `GSUID_GenerateString()` (alto volume, UUID em 29 chars)

### Perry's Hammer (hash-based naming)
```slang
Private::Name = Func( Data )
Returns( String() )
{
    SHA1 = Crypto::SHA1Hash( "My namespace;" + String( Data ) );
    Sec Name = "XX" + SubStr( JSISHA1HashToSecurityName( SHA1 ), 2 );
    Return( Sec Name );
};
// Resultado: XX,f'p1"q&2-w.om2i)vsd8[h]k0>
```

## Padrões de Escrita Segura no Banco

### 1. Favor Immutable Objects (inserir, nunca atualizar)

**Cenário**: estado simples que precisa ser atualizado de muitos lugares.

**Padrão**:
- Manter um objeto **base** mutável + muitos objetos **incremental** imutáveis
- **Write**: criar novo objeto incremental (SecurityAdd) com nome único
- **Read**: carregar base + todos incrementals, agregar em memória
- **Netting**: job periódico (EOD/fora de horário) consolida incrementals no base e deleta incrementals

**Vantagem**: sem write conflicts em runtime (writes nunca atualizam objetos existentes)

**Exceção especial do SecDb**: se dois objetos com mesmo nome e **conteúdo idêntico** são inseridos de fontes diferentes, o conflict checker aceita ambos sem conflito.

**Cuidado**: durante netting há janela de inconsistência (base atualizado mas incrementals ainda não deletados).

### 2. Split Large Mutables (dividir objetos grandes)

**Cenário**: estado complexo, infrequentemente atualizado, que não permite imutabilidade.

**Anti-pattern**: NÃO usar um único Container grande com Structure.
```slang
// NÃO FAÇA ISSO
Sec = GetSecurity( "My Container" );
Contents = Contents( Sec );
Contents[ Key ] = Value;
Check( SetValue( Contents( Sec ), Contents ) );
Check( UpdateSecurity( Sec ) );  // <-- RUIM: loga objeto inteiro na transação
```

**Problemas**:
- Cada `UpdateSecurity` loga objeto **inteiro** no transaction log (não só o diff)
- Dois processos atualizando diferentes partes → **conflict**

**Padrão correto**: facade object referenciando múltiplos underlying objects menores
```slang
My Data = Func( Self, VTI )
{
    My Data = My Data( Underlying Data Objects( Self ) );
    Return( @Array::StructureUnion( My Data ) )
};
```
- Dividir semanticamente (por dia, por semana, por domínio)
- Analisar access patterns para agrupamento
- NÃO usar handlers `@Set` no facade (complica transactions)
- Usar `GetmanySecurities` para eficiência

### 3. Use Transactions (agrupar writes)

- Sempre envolver múltiplas escritas em Transaction blocks
- TransactionCommit: controla quando enviar (por tamanho ou por parts)
- Reduz pressão no DB e tráfego inter-ring

## Ferramentas e Sistemas Relacionados

| Ferramenta | Propósito |
|---|---|
| **SecView** | UI para navegar e interagir com SecDb (CVS access) |
| **Slang Extension** | Extensão VS Code para editar, rodar e debugar Slang |
| **Procmon** | Scheduling e monitoramento de processos |
| **ProcFellow** | Editor e deploy de proc files (integrado com script review) |
| **Procnosticator** | Monitoramento de processos em execução |
| **EPSSP/FAQ System** | Base de conhecimento de perguntas e respostas sobre SecDb |
| **Graph Framework** | Framework para definir UFOs e VTs com dependências |
| **JSI** | Java Slang Integration |
| **python-slang** | Integração Python ↔ Slang |
| **BoltWeb** | Interface web para SecDB Match / TAT |
| **Freddie** | Ferramenta intraday de risk/P&L (integrada com SecDB) |

## Referências EngHub

- **enghub-solutions/secdb**: overview de soluções SecDb (Procmon, Slang patterns, Graph)
- **well-architected-platform-docs/secdb**: design patterns (naming, immutability, splitting, transactions, _PROCM)
- **secdb-platform (EngHub)**: docs completas de Slang, Graph, SecView (não no repo registry local — acessar via EngHub web)
- **EPSSP FAQ**: `https://www.epssp.site.gs.com/ssps/Current/FAQ_Main` — base canônica de conhecimento SecDb
