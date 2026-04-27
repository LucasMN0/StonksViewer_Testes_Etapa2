# Análise Crítica — Testes Unitários e Cobertura de Código
**Projeto:** StonksView — Gerenciador Financeiro Pessoal  
**Disciplina:** Testes e Qualidade de Software  
**Etapa:** Projeto Integrador – Etapa 1

---

## 1. Contexto e Módulo Selecionado

O StonksView é uma aplicação web desenvolvida em Django que permite ao usuário
gerenciar suas finanças pessoais por meio de transações, metas financeiras e
lembretes. Para esta etapa, foram selecionados os módulos do app `usuarios`, que
concentra toda a lógica de negócio da aplicação: validação de senhas
(`validators.py`), modelos de dados (`models.py`), formulários (`forms.py`) e
as views responsáveis pelos endpoints HTTP (`views.py`).

A escolha se justifica por esses módulos conterem as regras mais críticas do
sistema — criação e autenticação de usuários, registro de transações financeiras
e o controle de progresso de metas — tornando-os os candidatos mais relevantes
para garantia de qualidade.

---

## 2. Testes Implementados

Foram implementados **90 testes unitários** organizados em 11 classes, cobrindo
os quatro arquivos de código principal:

| Classe de Teste | Testes | Foco |
|---|---|---|
| `CustomPasswordValidatorTests` | 11 | Regras de validação de senha |
| `CustomUserManagerTests` | 7 | Criação de usuários e superusuários |
| `CustomUserModelTests` | 4 | Comportamento do model de usuário |
| `TransacaoModelTests` | 8 | Tipos e atributos de transações |
| `MetaFinanceiraAdicionarProgressoTests` | 12 | Lógica de progresso de metas |
| `MetaFinanceiraModelTests` | 2 | Defaults do model de metas |
| `LembreteModelTests` | 3 | Model de lembretes |
| `LoginFormTests` | 6 | Validação do formulário de login |
| Views (Autenticação, Perfil, Transações, Metas, Lembretes) | 37 | Endpoints HTTP |

Os testes cobrem os três tipos exigidos: **cenários principais** (fluxo feliz),
**casos de erro** (entradas inválidas, recursos inexistentes, acesso não
autorizado) e **casos de limite** (valores no exato limiar das regras, como
senha com exatamente 8 caracteres ou meta com progresso que ultrapassa o valor
alvo).

---

## 3. Cobertura de Código

A execução com a ferramenta `coverage.py` produziu os seguintes resultados:

| Arquivo | Linhas | Não cobertas | Cobertura |
|---|---|---|---|
| `validators.py` | 16 | 0 | **100%** |
| `models.py` | 80 | 0 | **100%** |
| `forms.py` | 4 | 0 | **100%** |
| `views.py` | 212 | 58 | **73%** |
| **TOTAL** | **791** | **66** | **92%** |

Os arquivos com lógica de negócio pura (`models.py` e `validators.py`)
atingiram cobertura total de 100%, demonstrando que todas as regras críticas
do domínio estão verificadas. A cobertura de `views.py` ficou em 73%, pois as
views de recuperação e redefinição de senha (`recuperar_senha` e
`redefinir_senha`) não foram cobertas — conforme detalhado na seção seguinte.

---

## 4. Lacunas Identificadas

### 4.1 Views de recuperação de senha (linhas 61–111 de views.py)
As views `recuperar_senha` e `redefinir_senha` dependem do envio real de
e-mail via SMTP e da geração/validação de tokens de segurança temporários.
Testá-las exige configuração adicional: uso de `django.test.utils.override_settings`
com backend de e-mail em memória e simulação do ciclo completo de token. Embora
tecnicamente viável, optou-se por não incluir esses testes nesta etapa para
manter o foco na lógica de negócio central. Essa é a principal lacuna da
cobertura atual.

### 4.2 Testes de integração ausentes
Os testes implementados são estritamente unitários. Não há testes de integração
que verifiquem, por exemplo, o fluxo completo de cadastro → login → criação de
meta → conclusão da meta em sequência, passando por múltiplas camadas
simultaneamente.

### 4.3 Ausência de testes de interface
Nenhum teste de front-end foi implementado. A camada HTML/CSS/JavaScript não
possui verificações automatizadas de comportamento no navegador.

---

## 5. Bugs Encontrados Através dos Testes

A execução dos testes revelou **um bug real presente em três endpoints** da
aplicação (`adicionar_transacao`, `adicionar_meta` e `adicionar_lembrete`).

**Causa:** após `Model.objects.create()` no Django 3.2 com SQLite, campos do
tipo `DateField` retornam o valor como `str` em vez de `datetime.date`. O
código das views chamava `.strftime('%Y-%m-%d')` diretamente sobre esse valor,
o que gerava `AttributeError: 'str' object has no attribute 'strftime'` e fazia
os três endpoints retornarem HTTP 400 em vez de 200.

**Correção aplicada:** adicionado `instance.refresh_from_db()` imediatamente
após cada `create()`, forçando o ORM a reler o registro do banco com os tipos
corretos antes de construir a resposta JSON.

Esse achado ilustra o valor prático dos testes unitários: um comportamento
incorreto que passaria despercebido em revisão de código foi detectado e
corrigido de forma objetiva.

---

## 6. Riscos e Melhorias Sugeridas

**Riscos:**
- A ausência de testes para o fluxo de recuperação de senha representa um risco
  de segurança: falhas na geração ou validação de tokens podem passar
  despercebidas.
- O banco SQLite utilizado em desenvolvimento não é adequado para produção,
  podendo apresentar comportamentos distintos (como o bug de `DateField`
  descrito acima) que os testes locais não detectariam em um banco PostgreSQL.

**Melhorias:**
- Implementar testes para as views de recuperação de senha utilizando o backend
  de e-mail em memória do Django (`locmem.EmailBackend`) e mock de tokens.
- Adicionar testes de integração cobrindo fluxos completos de usuário.
- Separar as configurações de desenvolvimento e produção em arquivos distintos
  (`settings/dev.py` e `settings/prod.py`), evitando que credenciais fiquem
  expostas no código.
- Migrar o banco para PostgreSQL, tornando o ambiente de testes mais fiel ao
  ambiente de produção.

---

## 7. Conclusão

Os testes implementados cobrem 92% do código total da aplicação e 100% dos
módulos de lógica de negócio pura. Além de garantir a qualidade do código
existente, o processo de escrita dos testes revelou um bug funcional em três
endpoints da API, demonstrando concretamente o valor da prática de testes
unitários. As lacunas identificadas — principalmente as views de recuperação de
senha e a ausência de testes de integração — representam trabalho futuro claro
e bem delimitado para as próximas etapas do projeto.
