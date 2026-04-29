# Análise — Testes de Integração
**Projeto:** StonksView — Gerenciador Financeiro Pessoal  
**Disciplina:** Testes e Qualidade de Software  
**Etapa:** Projeto Integrador – Etapa 2

---

## 1. Fluxos Testados

Foram implementados **34 testes de integração** em `usuarios/tests_integracao.py`, organizados em 5 classes que cobrem os principais fluxos do sistema com múltiplos módulos interagindo simultaneamente.

### Fluxo 1 — Cadastro com validação multicamada + Login (7 testes)
Classe: `IntegracaoCadastroLoginTests`

Valida a cadeia completa: `CustomPasswordValidator` → `CustomUserManager.create_user()` → `cadastro view` → sessão Django → `login_view`. Os testes verificam que senhas inválidas (curta, sem maiúscula, sem símbolo) são rejeitadas pelo validador antes de qualquer acesso ao banco, que e-mails duplicados retornam erro sem criar um segundo registro, e que após o cadastro o usuário já fica autenticado, podendo logar novamente com as mesmas credenciais.

### Fluxo 2 — Recuperação e redefinição de senha (7 testes)
Classe: `IntegracaoRecuperacaoSenhaTests`

Valida a cadeia: `recuperar_senha view` → `CustomUser.objects.get()` → `default_token_generator` → `send_mail` (mockado) → `redefinir_senha view` → `CustomPasswordValidator` → `user.set_password()`. Os testes verificam que o e-mail só é enviado quando o endereço existe no banco, que tokens inválidos redirecionam corretamente, que senhas que violam as regras do validador não são salvas, e que o login com a nova senha funciona após o reset completo.

### Fluxo 3 — Transações e cálculo do dashboard (6 testes)
Classe: `IntegracaoTransacoesDashboardTests`

Observa e valida a cadeia: `adicionar_transacao view` → `Transacao.objects.create()` → `dashboard view` → lógica de agregação Python. Os testes verificam a separação correta dos tipos (apenas `income` vai para ganhos, apenas `expense` vai para gastos), o cálculo do saldo, o isolamento entre usuários, e o reflexo imediato de exclusões no dashboard.

### Fluxo 4 — Ciclo de vida completo de metas financeiras (7 testes)
Classe: `IntegracaoMetaFinanceiraTests`

Valida a cadeia: `adicionar_meta view` → `MetaFinanceira.objects.create()` → `adicionar_progresso_meta view` → `MetaFinanceira.adicionar_progresso()` → `listar_metas_json view`. Os testes verificam o estado inicial (`Pendente`, `valor_atual = 0`), a transição de status a cada progresso, o acúmulo de múltiplos progressos parciais, a rejeição de valores negativos com HTTP 400, e a remoção da meta da listagem após exclusão.

### Fluxo 5 — Isolação de dados entre usuários (7 testes)
Classe: `IntegracaoIsolacaoDadosTests`

Valida que os filtros `usuario=request.user` presentes em todas as views funcionam de forma integrada. Dois usuários (A e B) operam simultaneamente em clientes distintos. Os testes confirmam que nenhum recurso (transação, meta, lembrete) criado por A aparece na listagem de B, e que B recebe HTTP 404 ao tentar excluir ou modificar qualquer recurso que pertença a A.

---

## 2. Problemas Encontrados

### Problema 1 — Acoplamento implícito entre `send_mail` e o módulo `usuarios.views`
No processo de escrita do Fluxo 2, constatou-se que `recuperar_senha` importa e chama o `send_mail` diretamente, sem abstração de camada de serviço. Isso tornou obrigatório o uso de `unittest.mock.patch('usuarios.views.send_mail')` para evitar chamadas SMTP reais durante os testes. O problema em si não impede a execução dos testes, mas revela um acoplamento forte entre a view e o serviço externo de e-mail.

### Problema 2 — Dashboard retorna `Decimal('0')` em vez de `int(0)` para transações vazias
No processo de teste do `dashboard` sem transações cadastradas, o contexto retornado pelo Django continha `Decimal('0')` (resultado de `sum([])`, que retorna `0` inteiro em Python, mas os valores existentes são `Decimal`). O teste precisou utilizar `Decimal('0')` nas asserções em vez de `0` para evitar falsos negativos por incompatibilidade de tipos, revelando inconsistência no tipo de retorno da view dependendo da presença ou ausência de dados.

---

## 3. Soluções Aplicadas

### Solução para o Problema 1
O mock foi aplicado com `@patch('usuarios.views.send_mail')` diretamente no nível da view, que é o local correto de interceptação no Python. Os testes verificam tanto `mock_send_mail.assert_called_once()` (e-mail existente) quanto `mock_send_mail.assert_not_called()` (e-mail inexistente), garantindo o comportamento correto sem dependência de SMTP externo.

### Solução para o Problema 2
As asserções do dashboard foram escritas com `Decimal('valor')` de forma consistente em todos os testes do Fluxo 3, alinhando o tipo esperado ao tipo efetivamente retornado pela view. Adicionalmente, o teste `test_dashboard_tipos_extras_nao_afetam_saldo` foi escrito para cobrir o caso de dashboard vazio, documentando o comportamento atual como aceito.

---

## 4. Resultado Final

```
Ran 34 tests in 5.035s

OK
```

Todos os 34 testes passaram sem falhas. A suíte de integração, somada à suíte unitária da Etapa 1, resulta em **124 testes totais** cobrindo os fluxos críticos do StonksView de forma isolada (unitária) e em conjunto (integração), garantindo as camadas do sistema se comunicam corretamente.
