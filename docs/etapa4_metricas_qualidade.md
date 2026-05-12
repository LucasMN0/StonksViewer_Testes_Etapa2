# Etapa 4 – Métricas de Qualidade: StonksView

**Projeto:** StonksView – Gestão Financeira Pessoal  
**Framework:** Django 5.2 / Python 3.10  
**Data da análise:** 12/05/2026  
**Ferramentas utilizadas:** coverage.py, radon 6.0.1, pylint 4.0.5, bandit 1.9.4  

---

## 1. Cobertura de Código

### 1.1 Resumo Geral

A cobertura foi regenerada executando a suíte completa de 124 testes (unitários + integração):

```
coverage run --source=usuarios manage.py test usuarios --verbosity=2
```

```
Nome                                  Stmts   Miss  Cover   Linhas não cobertas
----------------------------------------------------------------------------------
usuarios/__init__.py                      0      0   100%
usuarios/admin.py                        17      0   100%
usuarios/apps.py                          4      0   100%
usuarios/forms.py                         4      0   100%
usuarios/migrations/0001_initial.py       7      0   100%
usuarios/models.py                       80      0   100%
usuarios/tests.py                       447      8    98%   47-48, 54-55, 73-74, 117-118
usuarios/tests_integracao.py            226      0   100%
usuarios/urls.py                          4      0   100%
usuarios/validators.py                   16      0   100%
usuarios/views.py                       215     20    91%   91-92, 100-101, 183-184,
                                                            191, 202, 228, 266-267,
                                                            274, 283-284, 303-304,
                                                            311, 358-359, 366
----------------------------------------------------------------------------------
TOTAL                                  1020     28    97%
```

**Cobertura total: 97% (992/1020 linhas)**

> Nota: a cobertura total subiu de ~92% (relatório anterior) para 97% após a adição dos testes de integração do fluxo de recuperação de senha (`IntegracaoRecuperacaoSenhaTests`).

---

### 1.2 Análise por Módulo

| Módulo | Cobertura | Situação | Comentário |
|---|---|---|---|
| `models.py` | **100%** | Excelente | Toda a lógica de negócio está coberta |
| `validators.py` | **100%** | Excelente | Todas as regras de senha testadas |
| `forms.py` | **100%** | Excelente | Formulário simples, totalmente coberto |
| `admin.py` | **100%** | Excelente | Configuração de admin coberta |
| `tests_integracao.py` | **100%** | Excelente | Os próprios testes têm cobertura total |
| `tests.py` | **98%** | Muito bom | 8 linhas descobertas são caminhos de erro em `self.fail()` |
| `views.py` | **91%** | Atenção | 20 linhas descobertas em múltiplas funções |

---

### 1.3 Trechos Não Testados e Avaliação de Risco

#### `views.py` – Linhas não cobertas e risco associado

| Linhas | Função | O que não é testado | Risco |
|---|---|---|---|
| 91–92 | `redefinir_senha()` | `except:` nu após decodificação do UID – caminho de token malformado em GET | **Médio** – segurança |
| 100–101 | `redefinir_senha()` | POST com token inválido retornando redirect | **Médio** – fluxo crítico |
| 183–184 | `adicionar_transacao()` | `except Exception` ao falhar a criação da transação | Baixo – só dispara em erro interno |
| 191 | `excluir_transacao()` | `except Exception` ao falhar a exclusão | Baixo |
| 202 | `listar_metas()` | `render()` da view de lista de metas (não-JSON) | **Médio** – UI não testada |
| 228 | `adicionar_meta()` | Branch de dados incompletos num caminho específico | Baixo |
| 266–267 | `adicionar_meta()` | `except Exception` na criação da meta | Baixo |
| 274 | `adicionar_progresso_meta()` | Branch de validação de campo ausente | Baixo |
| 283–284 | `adicionar_progresso_meta()` | Branch de valor ≤ 0 via caminho alternativo | Baixo |
| 303–304 | `adicionar_progresso_meta()` | `except Exception` no progresso da meta | Baixo |
| 311 | `excluir_meta()` | `except Exception` na exclusão | Baixo |
| 358–359 | `adicionar_lembrete()` | `except Exception` na criação do lembrete | Baixo |
| 366 | `excluir_lembrete()` | `except Exception` na exclusão | Baixo |

**Observação crítica:** As linhas 91–92 e 100–101 representam o caminho de token inválido/corrompido em `redefinir_senha()`. Embora os testes de integração cubram o token inválido via GET, o `except:` nu (sem tipo de exceção) na linha 91 permanece descoberto nesse ponto exato. Trata-se de um code smell prioritário (ver seção 2).

#### `tests.py` – Linhas 47-48, 54-55, 73-74, 117-118

São blocos `self.fail("Exceção não deveria ter sido lançada")` dentro de `except` em testes de validador. Só executariam se o validador lançasse uma exceção quando não deveria — ou seja, indicam um defeito no código de produção que não existe. Risco: **nenhum**.

---

## 2. Code Smells

### 2.1 Resultados do Pylint

```
pylint usuarios/ --disable=C0114,C0115,C0116
Score: 7.05/10
```

Total de ocorrências por categoria:

| Categoria | Quantidade | Descrição |
|---|---|---|
| `E` (Error) | 27 | `no-member` em modelos Django (falso positivo do pylint) |
| `W` (Warning) | 9 | `bare-except`, `broad-exception-caught`, `unused-import`, `reimport` |
| `C` (Convention) | 23 | Ordem de imports, linhas longas, nomes não-snake_case |
| `R` (Refactor) | 2 | Uso de `sum()` sem generator |

> **Nota sobre os erros `E1101 no-member`:** O pylint não consegue inferir dinamicamente os atributos `.objects` dos modelos Django (são adicionados pela metaclasse). São **falsos positivos** e não representam bugs reais.

### 2.2 Problemas Identificados

#### 2.2.1 Bare Except — `views.py:91` (CRÍTICO)

```python
# views.py, linha 88-92
try:
    uid = urlsafe_base64_decode(uidb64).decode()
    user = User.objects.get(pk=uid)
except:                                 # ← bare except
    user = None
```

**Problema:** `except:` sem tipo captura *qualquer* exceção, incluindo `KeyboardInterrupt`, `SystemExit` e `GeneratorExit` — exceções que o sistema operacional usa para encerrar processos. Isso pode mascarar bugs silenciosamente e tornar a depuração impossível.

**Correção adequada:**
```python
except (ValueError, TypeError, User.DoesNotExist):
    user = None
```

#### 2.2.2 Captura Genérica de Exceção — `views.py` (ALTO, múltiplos locais)

```python
# Padrão repetido em linhas 183, 266, 303, 358, 366
except Exception as e:
    return JsonResponse({'error': str(e)}, status=400)
```

**Problemas:**
- Captura exceções que não são de responsabilidade da view (ex.: `AssertionError`, `AttributeError`)
- Expõe mensagens de erro internas ao cliente via API — risco de segurança (information disclosure)
- Dificulta o diagnóstico: qualquer bug vira um HTTP 400 silencioso

**Correção adequada:**
```python
except (ValidationError, InvalidOperation, TypeError) as e:
    return JsonResponse({'error': 'Dados inválidos.'}, status=400)
```

#### 2.2.3 Código Duplicado — Serialização JSON (MÉDIO)

O mesmo padrão de serialização de objetos para JSON é repetido três vezes no arquivo:

```python
# Padrão em listar_transacoes() (linhas 145-155)
data = [{'id': t.id, 'data': t.data.strftime('%Y-%m-%d'), ...} for t in transacoes]
return JsonResponse({'transacoes': data})

# Padrão em listar_metas_json() (linhas 207-221)
data = [{'id': m.id, 'nome': m.nome, ...} for m in metas]
return JsonResponse({'metas': data})

# Padrão em listar_lembretes() (linhas 322-332)
data = [{'id': l.id, 'nome': l.nome, ...} for l in lembretes]
return JsonResponse({'lembretes': data})
```

**Problema:** Duplicação de lógica de formatação de data (`strftime`), conversão de `Decimal` para `float` e estrutura de resposta. Qualquer mudança no formato exige alterações em múltiplos lugares.

**Solução:** Extrair para métodos `to_dict()` em cada model, ou adotar Django REST Framework serializers.

#### 2.2.4 Magic Numbers — `views.py:218` (BAIXO)

```python
'porcentagem': float(round((m.valor_atual / m.valor) * 100, 1)) if m.valor > 0 else 0
```

Os literais `100` (fator de porcentagem) e `1` (casas decimais) são magic numbers. O cálculo deveria estar em um método `porcentagem` do model `MetaFinanceira`, mantendo a lógica próxima aos dados.

#### 2.2.5 Ordem de Imports — Múltiplos arquivos (BAIXO)

Pylint identificou que imports da biblioteca padrão (`json`, `decimal`, `unittest.mock`) estão após imports de terceiros (Django). A PEP 8 define a ordem: stdlib → third-party → local.

#### 2.2.6 Import Não Utilizado — `tests.py:25` (BAIXO)

```python
from models import CustomUser   # ← importado mas não usado diretamente nas asserções
```

#### 2.2.7 Nome de Método com Caracter Não-ASCII — `tests.py:371` (BAIXO)

```python
def test_valor_negativo_mantém_status_pendente_quando_valor_atual_zero(self):
```

O acento em `mantém` viola a convenção PEP 8 de nomes ASCII em identificadores.

### 2.3 Classificação por Severidade

| Severidade | Problema | Arquivo | Linha |
|---|---|---|---|
| **Crítico** | `bare-except` captura exceções do sistema | `views.py` | 91 |
| **Alto** | `broad-exception-caught` expõe erros internos | `views.py` | 183, 266, 303, 358, 366 |
| **Médio** | Código duplicado (serialização JSON) | `views.py` | 145-155, 207-221, 322-332 |
| **Médio** | Magic number no cálculo de porcentagem | `views.py` | 218 |
| **Baixo** | Ordem de imports fora do padrão PEP 8 | `views.py`, `tests_integracao.py` | múltiplos |
| **Baixo** | Import não utilizado | `tests.py` | 25 |
| **Baixo** | Nome de método com caractere não-ASCII | `tests.py` | 371 |

---

## 3. Complexidade Ciclomática

### 3.1 Resultados do Radon

```
radon cc usuarios/ -s -a
```

**Complexidade média geral: A (1.50)** — considerada excelente pela escala radon.

Escala de referência:
- **A** (1–5): Baixa complexidade — simples de testar e manter
- **B** (6–10): Moderada — aceitável, mas monitorar
- **C** (11–15): Alta — difícil de testar adequadamente
- **D/E/F** (>15): Muito alta — refatoração necessária

### 3.2 Funções com Maior Complexidade em `views.py`

| Função | Linha | CC | Nota | Avaliação |
|---|---|---|---|---|
| `redefinir_senha()` | 86 | 8 | **B** | Lida com GET/POST + validação de token + validação de senha + múltiplos redirects |
| `adicionar_meta()` | 226 | 8 | **B** | Validação manual de 5 campos + criação + tratamento de erro |
| `adicionar_progresso_meta()` | 272 | 6 | B | Validação + busca de objeto + chamada de método de model |
| `cadastro()` | 41 | 5 | A | Login automático pós-cadastro justifica a ramificação |
| `dashboard()` | 126 | 5 | A | Agrega múltiplos tipos de transação |
| `login_view()` | 25 | 4 | A | Fluxo padrão de autenticação |

**Observação:** As duas funções com nota B (`redefinir_senha` e `adicionar_meta`) são as que concentram mais lógica de validação manual dentro da view, em vez de delegar para forms ou serializers. Isso é a causa direta da complexidade elevada e da dificuldade de teste.

### 3.3 Maintainability Index

```
radon mi usuarios/ -s
```

| Arquivo | MI | Nota | Interpretação |
|---|---|---|---|
| `usuarios/validators.py` | 80.68 | **A** | Alta manutenibilidade |
| `usuarios/forms.py` | 79.21 | **A** | Alta manutenibilidade |
| `usuarios/models.py` | 64.33 | **A** | Boa manutenibilidade |
| `usuarios/views.py` | 54.86 | **A** | Manutenibilidade aceitável |
| `usuarios/tests.py` | 47.23 | **A** | Aceitável (arquivo grande e repetitivo por natureza) |

> O Maintainability Index (MI) combina volume de Halstead, complexidade ciclomática e número de linhas. Todos os arquivos ficam na faixa A (>20), indicando que o código ainda é gerenciável. O MI mais baixo em `tests.py` é esperado para arquivos de teste extensos.

---

## 4. Segurança (Bandit)

### 4.1 Vulnerabilidades Encontradas

```
bandit -r usuarios/ -f txt
```

**Resultado:** Nenhum problema de severidade ALTA ou MÉDIA encontrado.

Todos os 47 findings são de **severidade BAIXA** e se referem a senhas literais em código de teste:

| Regra | Descrição | Severidade | Confiança | Arquivos afetados |
|---|---|---|---|---|
| B106 `hardcoded_password_funcarg` | Senha literal passada como argumento de função | LOW | MEDIUM | `tests.py`, `tests_integracao.py` |
| B105 `hardcoded_password_string` | Senha literal em variável ou dict | LOW | MEDIUM | `tests_integracao.py` |

**Interpretação:** Senhas como `"Senha@123"`, `"Segura@123"`, `"Admin@123"` aparecem nos arquivos de teste para criação de usuários de teste. Isso é um **falso positivo** do bandit: em contexto de testes automatizados isolados (banco in-memory), senhas hardcoded são uma prática aceitável e não representam risco real.

**O código de produção (`views.py`, `models.py`, `validators.py`) não apresenta nenhum achado do bandit**, o que é um resultado positivo. Pontos específicos verificados pelo bandit:

- Ausência de SQL injection (consultas via ORM Django)
- Ausência de execução de shell/subprocesso
- Ausência de deserialização insegura (uso de `json.loads` sem `eval`)
- Ausência de uso de `hashlib` com algoritmos fracos

---

## 5. Interpretação dos Resultados

### O que os números indicam sobre a qualidade do sistema

**Pontos fortes:**

1. **Cobertura de 97%** é um resultado excelente e demonstra comprometimento com testes. Para um projeto acadêmico integrador, está bem acima da média da indústria (tipicamente 60-80%).

2. **Complexidade ciclomática média A (1.50)** indica que as funções são, em geral, simples e lineares. Apenas duas funções atingiram a nota B, e ainda dentro de um patamar controlado.

3. **100% de cobertura em models.py** é especialmente relevante: toda a lógica de negócio (cálculo de progresso de metas, transições de status, validações de usuário) está testada. Isso reduz o risco de regressão ao refatorar.

4. **Zero achados de severidade média ou alta no bandit** confirma que o código de produção não contém vulnerabilidades de segurança óbvias.

5. **Suíte de testes com 124 casos bem organizados**, cobrindo validators, models, forms, views (unitários) e fluxos completos (integração), demonstra maturidade no design dos testes.

**Pontos de atenção:**

1. **O `bare except` na linha 91 de `views.py` é o problema mais grave identificado.** Embora a cobertura das linhas 91-92 seja baixa (poucos testes passam por ali), o pattern é errado independentemente da cobertura: uma exceção de sistema poderia ser silenciada, causando comportamento imprevisível.

2. **O pylint pontuou 7.05/10**, abaixo do limiar de 8.0 geralmente adotado em projetos profissionais. A maior causa são os padrões de tratamento de exceção genérico (`broad-exception-caught`) e problemas de organização de código (imports fora de ordem).

3. **A duplicação de código de serialização JSON** não afeta o funcionamento, mas aumenta o custo de manutenção. Se o formato da API precisar mudar (ex.: datas em ISO 8601 com timezone), serão necessárias três edições em vez de uma.

4. **As views `adicionar_meta()` e `redefinir_senha()` concentram complexidade por realizarem validação manual** que idealmente deveria estar em forms Django ou serializers DRF. Isso é uma dívida técnica que se manifesta tanto na CC nota B quanto nas linhas descobertas.

### Relação entre cobertura e qualidade

Um aspecto fundamental desta análise é que **cobertura alta não garante ausência de bugs**. O exemplo mais claro é o `bare except` na linha 91: a linha que *captura* a exceção está descoberta pelos testes, mas mesmo que fosse executada, o problema está no *tipo* da cláusula, não na ausência de teste.

Similarmente, as linhas de `except Exception` nas views estão descobertas, mas o problema real é o design: elas capturam exceções demais e revelam detalhes internos ao cliente. Nenhum teste de cobertura corrigiria isso — seria necessário refatorar o tratamento de erro.

---

## 6. Recomendações de Melhoria

### Prioridade Alta (impacto em segurança e manutenibilidade)

**R1 – Substituir bare except por exceções específicas**
```python
# Atual (views.py:91)
except:
    user = None

# Correto
except (ValueError, TypeError, User.DoesNotExist):
    user = None
```

**R2 – Restringir captura de exceção nas views**
```python
# Atual
except Exception as e:
    return JsonResponse({'error': str(e)}, status=400)

# Correto
except (ValidationError, InvalidOperation) as e:
    return JsonResponse({'error': 'Dados inválidos.'}, status=400)
# Log interno: logger.exception("Erro ao criar transação")
```

### Prioridade Média (manutenibilidade e clareza)

**R3 – Extrair serialização para métodos de model**
```python
# Em models.py
class Transacao(models.Model):
    def to_dict(self):
        return {'id': self.id, 'data': self.data.isoformat(), ...}

# Em views.py
data = [t.to_dict() for t in transacoes]
```

**R4 – Extrair cálculo de porcentagem para property do model**
```python
# Em MetaFinanceira
@property
def porcentagem(self):
    if self.valor <= 0:
        return 0.0
    return round(float(self.valor_atual / self.valor * 100), 1)
```

**R5 – Delegar validação de `adicionar_meta()` a um Form Django**, reduzindo a complexidade ciclomática de B para A e aumentando a cobertura dos caminhos de erro.

### Prioridade Baixa (convenções)

**R6 –** Corrigir ordem de imports seguindo PEP 8 (stdlib → third-party → local)  
**R7 –** Remover import não utilizado de `CustomUser` em `tests.py:25`  
**R8 –** Renomear método com acento em `tests.py:371` para nome ASCII  

---

## Apêndice – Comandos Executados

```bash
# Cobertura
coverage run --source=usuarios manage.py test usuarios --verbosity=2
coverage report -m
coverage html -d coverage_report/
coverage xml -o coverage_report/coverage.xml

# Complexidade ciclomática
radon cc usuarios/ -s -a

# Maintainability Index
radon mi usuarios/ -s

# Code smells
pylint usuarios/ --disable=C0114,C0115,C0116

# Segurança
bandit -r usuarios/ -f txt
```
