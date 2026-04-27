"""
Testes Unitários - StonksView
==============================
Projeto Integrador – Etapa 1: Teste Unitário e Cobertura de Código

Módulos testados:
  - validators.py  → CustomPasswordValidator
  - models.py      → CustomUserManager, CustomUser, Transacao,
                     MetaFinanceira (adicionar_progresso), Lembrete
  - forms.py       → LoginForm
  - views.py       → autenticação, transações, metas, lembretes
"""

import json
from decimal import Decimal
from datetime import date

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.test.utils import override_settings

from .validators import CustomPasswordValidator
from .models import CustomUser, Transacao, MetaFinanceira, Lembrete
from .forms import LoginForm

User = get_user_model()


# ===========================================================================
# 1. TESTES DO VALIDADOR DE SENHA
# ===========================================================================

class CustomPasswordValidatorTests(TestCase):
    """Testa todas as regras do CustomPasswordValidator."""

    def setUp(self):
        self.validator = CustomPasswordValidator()

    # ---- cenários válidos --------------------------------------------------

    def test_senha_valida_passa_sem_excecao(self):
        """Senha com 8+ chars, maiúscula e símbolo deve passar sem exceção."""
        try:
            self.validator.validate("Segura@1")
        except ValidationError:
            self.fail("ValidationError levantada para senha válida.")

    def test_senha_longa_e_valida(self):
        """Senha bem mais longa também deve ser aceita."""
        try:
            self.validator.validate("MinhaSenh@Forte2025!")
        except ValidationError:
            self.fail("ValidationError levantada para senha válida e longa.")

    # ---- comprimento -------------------------------------------------------

    def test_senha_muito_curta_levanta_erro(self):
        """Senha com menos de 8 caracteres deve levantar ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("Ab@1")
        mensagens = [str(m) for m in ctx.exception.messages]
        self.assertTrue(
            any("8 caracteres" in m for m in mensagens),
            "Mensagem de comprimento ausente nos erros."
        )

    def test_senha_exatamente_8_chars_valida(self):
        """Senha com exatamente 8 caracteres (e demais regras) deve passar."""
        try:
            self.validator.validate("Abc@1234")
        except ValidationError:
            self.fail("Senha de 8 chars válida deveria passar.")

    def test_senha_7_chars_levanta_erro(self):
        """Senha com 7 caracteres deve falhar na regra de comprimento."""
        with self.assertRaises(ValidationError):
            self.validator.validate("Abc@123")

    # ---- letra maiúscula ---------------------------------------------------

    def test_senha_sem_maiuscula_levanta_erro(self):
        """Senha sem letra maiúscula deve levantar ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("segura@1")
        mensagens = [str(m) for m in ctx.exception.messages]
        self.assertTrue(
            any("maiúscula" in m for m in mensagens),
            "Mensagem de maiúscula ausente nos erros."
        )

    def test_senha_apenas_maiusculas_sem_simbolo_levanta_erro(self):
        """Senha com letras maiúsculas mas sem símbolo deve falhar."""
        with self.assertRaises(ValidationError):
            self.validator.validate("SENHASEMBOL")

    # ---- símbolo -----------------------------------------------------------

    def test_senha_sem_simbolo_levanta_erro(self):
        """Senha sem símbolo (!@#$%&?*) deve levantar ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("SenhaForte1")
        mensagens = [str(m) for m in ctx.exception.messages]
        self.assertTrue(
            any("símbolo" in m for m in mensagens),
            "Mensagem de símbolo ausente nos erros."
        )

    def test_cada_simbolo_permitido_e_aceito(self):
        """Cada símbolo do conjunto permitido deve satisfazer a regra."""
        simbolos = "!@#$%&?*"
        for s in simbolos:
            senha = f"AbcDef{s}1"
            try:
                self.validator.validate(senha)
            except ValidationError as e:
                self.fail(f"Símbolo '{s}' deveria ser aceito, mas levantou: {e}")

    # ---- múltiplos erros ---------------------------------------------------

    def test_senha_completamente_invalida_retorna_multiplos_erros(self):
        """Senha que viola todas as regras deve retornar 3 mensagens de erro."""
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("abc")
        self.assertGreaterEqual(
            len(ctx.exception.messages), 2,
            "Deveriam existir ao menos 2 mensagens de erro."
        )

    # ---- help_text ---------------------------------------------------------

    def test_get_help_text_retorna_string_nao_vazia(self):
        """get_help_text deve retornar uma string informativa."""
        texto = self.validator.get_help_text()
        self.assertIsInstance(texto, str)
        self.assertGreater(len(texto), 0)


# ===========================================================================
# 2. TESTES DO MANAGER E MODELO DE USUÁRIO
# ===========================================================================

class CustomUserManagerTests(TestCase):
    """Testa o CustomUserManager."""

    # ---- create_user -------------------------------------------------------

    def test_criar_usuario_com_dados_validos(self):
        """Deve criar e retornar um CustomUser com os dados corretos."""
        user = User.objects.create_user(
            email="joao@example.com",
            password="Segura@123",
            first_name="João"
        )
        self.assertEqual(user.email, "joao@example.com")
        self.assertEqual(user.first_name, "João")
        self.assertTrue(user.check_password("Segura@123"))

    def test_criar_usuario_sem_email_levanta_value_error(self):
        """Criar usuário sem email deve levantar ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="Segura@123", first_name="João")

    def test_criar_usuario_sem_senha_levanta_value_error(self):
        """Criar usuário sem senha deve levantar ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_user(email="joao@example.com", password=None, first_name="João")

    def test_criar_usuario_sem_first_name_levanta_value_error(self):
        """Criar usuário sem primeiro nome deve levantar ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_user(email="joao@example.com", password="Segura@123", first_name=None)

    def test_email_e_normalizado_ao_criar_usuario(self):
        """Django normalize_email converte apenas o domínio para minúsculo."""
        user = User.objects.create_user(
            email="TESTE@EXAMPLE.COM",
            password="Segura@123",
            first_name="Teste"
        )
        # normalize_email reduz apenas a parte do domínio (@xxx.com → @xxx.com)
        self.assertEqual(user.email, "TESTE@example.com")

    # ---- create_superuser --------------------------------------------------

    def test_criar_superusuario_tem_flags_corretas(self):
        """Superusuário deve ter is_staff e is_superuser True."""
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="Admin@123"
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_criar_superusuario_sem_first_name_usa_default_admin(self):
        """Superusuário criado sem first_name deve usar 'Admin' como padrão."""
        admin = User.objects.create_superuser(
            email="admin2@example.com",
            password="Admin@123"
        )
        self.assertEqual(admin.first_name, "Admin")


class CustomUserModelTests(TestCase):
    """Testa o modelo CustomUser."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="maria@example.com",
            password="Senha@123",
            first_name="Maria"
        )

    def test_str_retorna_email(self):
        """__str__ de CustomUser deve retornar o email."""
        self.assertEqual(str(self.user), "maria@example.com")

    def test_usuario_ativo_por_padrao(self):
        """Usuário recém-criado deve ter is_active=True."""
        self.assertTrue(self.user.is_active)

    def test_usuario_nao_e_staff_por_padrao(self):
        """Usuário comum não deve ser staff."""
        self.assertFalse(self.user.is_staff)

    def test_email_unico_impede_duplicata(self):
        """Não deve ser possível criar dois usuários com o mesmo email."""
        from django.db import IntegrityError
        with self.assertRaises(Exception):
            User.objects.create_user(
                email="maria@example.com",
                password="Outra@123",
                first_name="Maria2"
            )


# ===========================================================================
# 3. TESTES DO MODELO TRANSACAO
# ===========================================================================

class TransacaoModelTests(TestCase):
    """Testa o modelo Transacao."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="Senha@123",
            first_name="User"
        )

    def _criar_transacao(self, descricao="Salário", valor="5000.00", tipo="income"):
        return Transacao.objects.create(
            usuario=self.user,
            data=date(2025, 1, 15),
            descricao=descricao,
            valor=Decimal(valor),
            tipo=tipo,
        )

    def test_str_retorna_descricao_e_valor(self):
        """__str__ deve retornar 'descrição - valor'."""
        t = self._criar_transacao()
        self.assertIn("Salário", str(t))
        self.assertIn("5000", str(t))

    def test_criar_transacao_income(self):
        t = self._criar_transacao(tipo="income")
        self.assertEqual(t.tipo, "income")

    def test_criar_transacao_expense(self):
        t = self._criar_transacao(descricao="Aluguel", valor="1200.00", tipo="expense")
        self.assertEqual(t.tipo, "expense")

    def test_criar_transacao_investment(self):
        t = self._criar_transacao(tipo="investment")
        self.assertEqual(t.tipo, "investment")

    def test_criar_transacao_extra(self):
        t = self._criar_transacao(tipo="extra")
        self.assertEqual(t.tipo, "extra")

    def test_criar_transacao_other(self):
        t = self._criar_transacao(tipo="other")
        self.assertEqual(t.tipo, "other")

    def test_transacao_pertence_ao_usuario(self):
        """A transação criada deve pertencer ao usuário correto."""
        t = self._criar_transacao()
        self.assertEqual(t.usuario, self.user)

    def test_valor_decimal_armazenado_corretamente(self):
        """O valor deve ser armazenado como Decimal com duas casas."""
        t = self._criar_transacao(valor="1234.56")
        self.assertEqual(t.valor, Decimal("1234.56"))


# ===========================================================================
# 4. TESTES DO MODELO META FINANCEIRA — LÓGICA DE NEGÓCIO PRINCIPAL
# ===========================================================================

class MetaFinanceiraAdicionarProgressoTests(TestCase):
    """
    Testa o método adicionar_progresso da MetaFinanceira.
    Este é o núcleo da lógica de negócio do projeto.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="meta@example.com",
            password="Senha@123",
            first_name="Meta"
        )
        self.meta = MetaFinanceira.objects.create(
            usuario=self.user,
            nome="Viagem",
            valor=Decimal("1000.00"),
            valor_atual=Decimal("0.00"),
            data_inicial=date(2025, 1, 1),
            data_final=date(2025, 12, 31),
        )

    # ---- status: pendente → em andamento -----------------------------------

    def test_adicionar_progresso_parcial_muda_status_para_em_andamento(self):
        """Progresso parcial deve mudar status para 'Em andamento'."""
        self.meta.adicionar_progresso(Decimal("300.00"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.status, "Em andamento")
        self.assertEqual(self.meta.valor_atual, Decimal("300.00"))

    def test_adicionar_progresso_acumula_valores(self):
        """Chamadas consecutivas devem acumular o valor_atual."""
        self.meta.adicionar_progresso(Decimal("200.00"))
        self.meta.adicionar_progresso(Decimal("300.00"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.valor_atual, Decimal("500.00"))

    # ---- status: em andamento → concluída ----------------------------------

    def test_progresso_que_atinge_meta_muda_status_para_concluida(self):
        """Atingir o valor alvo deve mudar status para 'Concluída'."""
        self.meta.adicionar_progresso(Decimal("1000.00"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.status, "Concluída")
        self.assertEqual(self.meta.valor_atual, Decimal("1000.00"))

    def test_progresso_que_ultrapassa_meta_e_capped_no_valor_alvo(self):
        """Valor acima do alvo deve ser limitado ao valor da meta (cap)."""
        self.meta.adicionar_progresso(Decimal("1500.00"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.valor_atual, Decimal("1000.00"))
        self.assertEqual(self.meta.status, "Concluída")

    def test_progresso_parcial_seguido_de_finalizacao(self):
        """Progresso parcial + progresso final deve resultar em 'Concluída'."""
        self.meta.adicionar_progresso(Decimal("600.00"))
        self.meta.adicionar_progresso(Decimal("500.00"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.status, "Concluída")
        self.assertEqual(self.meta.valor_atual, Decimal("1000.00"))

    # ---- valor negativo / zero ---------------------------------------------

    def test_valor_negativo_nao_deixa_valor_atual_negativo(self):
        """Subtração que resultaria em negativo deve ser zerada."""
        self.meta.adicionar_progresso(Decimal("-500.00"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.valor_atual, Decimal("0.00"))

    def test_valor_negativo_mantém_status_pendente_quando_valor_atual_zero(self):
        """Com valor_atual zerado por subtração, status deve ser 'Pendente'."""
        self.meta.adicionar_progresso(Decimal("-100.00"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.status, "Pendente")

    def test_subtracao_de_progresso_existente(self):
        """Subtração deve reduzir valor_atual sem ir abaixo de zero."""
        self.meta.adicionar_progresso(Decimal("400.00"))
        self.meta.adicionar_progresso(Decimal("-200.00"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.valor_atual, Decimal("200.00"))
        self.assertEqual(self.meta.status, "Em andamento")

    def test_subtracao_que_zera_muda_status_para_pendente(self):
        """Subtração que zera valor_atual deve retornar status para 'Pendente'."""
        self.meta.adicionar_progresso(Decimal("400.00"))
        self.meta.adicionar_progresso(Decimal("-400.00"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.valor_atual, Decimal("0.00"))
        self.assertEqual(self.meta.status, "Pendente")

    # ---- casos limite (edge cases) -----------------------------------------

    def test_progresso_zero_nao_altera_estado(self):
        """Adicionar zero não deve alterar valor_atual nem status."""
        self.meta.adicionar_progresso(Decimal("0"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.valor_atual, Decimal("0.00"))
        self.assertEqual(self.meta.status, "Pendente")

    def test_progresso_exatamente_no_limite_superior(self):
        """Valor_atual exatamente igual ao valor alvo = 'Concluída'."""
        self.meta.adicionar_progresso(Decimal("1000.00"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.status, "Concluída")

    def test_str_retorna_nome_da_meta(self):
        """__str__ de MetaFinanceira deve retornar o nome."""
        self.assertEqual(str(self.meta), "Viagem")


class MetaFinanceiraModelTests(TestCase):
    """Testa campos e defaults do modelo MetaFinanceira."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="campo@example.com",
            password="Senha@123",
            first_name="Campo"
        )

    def test_status_padrao_e_pendente(self):
        """Status padrão ao criar uma MetaFinanceira deve ser 'Pendente'."""
        meta = MetaFinanceira.objects.create(
            usuario=self.user,
            nome="Reserva",
            valor=Decimal("500.00"),
            data_inicial=date(2025, 1, 1),
            data_final=date(2025, 6, 30),
        )
        self.assertEqual(meta.status, "Pendente")

    def test_valor_atual_padrao_e_zero(self):
        """valor_atual padrão deve ser 0."""
        meta = MetaFinanceira.objects.create(
            usuario=self.user,
            nome="Fundo",
            valor=Decimal("200.00"),
            data_inicial=date(2025, 1, 1),
            data_final=date(2025, 3, 31),
        )
        self.assertEqual(meta.valor_atual, Decimal("0.00"))


# ===========================================================================
# 5. TESTES DO MODELO LEMBRETE
# ===========================================================================

class LembreteModelTests(TestCase):
    """Testa o modelo Lembrete."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="lemb@example.com",
            password="Senha@123",
            first_name="Lemb"
        )
        self.lembrete = Lembrete.objects.create(
            usuario=self.user,
            nome="Pagar fatura",
            descricao="Fatura do cartão",
            data=date(2025, 5, 10),
        )

    def test_str_retorna_nome(self):
        """__str__ deve retornar o nome do lembrete."""
        self.assertEqual(str(self.lembrete), "Pagar fatura")

    def test_descricao_pode_ser_vazia(self):
        """Campo descricao é opcional (blank=True)."""
        l = Lembrete.objects.create(
            usuario=self.user,
            nome="Lembrete sem descrição",
            descricao="",
            data=date(2025, 6, 1),
        )
        self.assertEqual(l.descricao, "")

    def test_lembrete_pertence_ao_usuario(self):
        self.assertEqual(self.lembrete.usuario, self.user)


# ===========================================================================
# 6. TESTES DO FORM DE LOGIN
# ===========================================================================

class LoginFormTests(TestCase):
    """Testa o LoginForm."""

    def test_form_valido_com_dados_corretos(self):
        """Form com email e senha válidos deve ser válido."""
        form = LoginForm(data={"email": "teste@example.com", "password": "Abc@1234"})
        self.assertTrue(form.is_valid())

    def test_form_invalido_sem_email(self):
        """Form sem email deve ser inválido."""
        form = LoginForm(data={"email": "", "password": "Abc@1234"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_form_invalido_sem_senha(self):
        """Form sem senha deve ser inválido."""
        form = LoginForm(data={"email": "teste@example.com", "password": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_form_invalido_com_email_malformado(self):
        """Email sem '@' deve tornar o form inválido."""
        form = LoginForm(data={"email": "nao-e-um-email", "password": "Abc@1234"})
        self.assertFalse(form.is_valid())

    def test_form_invalido_sem_nenhum_dado(self):
        """Form completamente vazio deve ser inválido."""
        form = LoginForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("password", form.errors)

    def test_cleaned_data_disponivel_apos_validacao(self):
        """Após is_valid(), cleaned_data deve conter email e password."""
        form = LoginForm(data={"email": "user@site.com", "password": "Abc@1234"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email"], "user@site.com")


# ===========================================================================
# 7. TESTES DAS VIEWS — AUTENTICAÇÃO
# ===========================================================================

@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class LoginViewTests(TestCase):
    """Testa a view de login."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="login@example.com",
            password="Senha@123",
            first_name="Login"
        )

    def test_get_login_retorna_200(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_post_login_credenciais_validas_redireciona_para_perfil(self):
        response = self.client.post(reverse("login"), {
            "email": "login@example.com",
            "password": "Senha@123"
        })
        self.assertRedirects(response, reverse("perfil"))

    def test_post_login_credenciais_invalidas_nao_redireciona(self):
        response = self.client.post(reverse("login"), {
            "email": "login@example.com",
            "password": "SenhaErrada@99"
        })
        self.assertEqual(response.status_code, 200)

    def test_post_login_senha_errada_exibe_mensagem_de_erro(self):
        response = self.client.post(reverse("login"), {
            "email": "login@example.com",
            "password": "Errada@1"
        })
        messages = list(response.context["messages"])
        self.assertTrue(any("inválidos" in str(m) for m in messages))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CadastroViewTests(TestCase):
    """Testa a view de cadastro."""

    def setUp(self):
        self.client = Client()

    def test_get_cadastro_retorna_200(self):
        response = self.client.get(reverse("cadastro"))
        self.assertEqual(response.status_code, 200)

    def test_post_cadastro_valido_cria_usuario_e_redireciona(self):
        response = self.client.post(reverse("cadastro"), {
            "first_name": "Novo",
            "email": "novo@example.com",
            "password": "Senha@123",
        })
        self.assertRedirects(response, reverse("perfil"))
        self.assertTrue(User.objects.filter(email="novo@example.com").exists())

    def test_post_cadastro_email_duplicado_retorna_erro(self):
        User.objects.create_user(
            email="existente@example.com",
            password="Senha@123",
            first_name="Existente"
        )
        response = self.client.post(reverse("cadastro"), {
            "first_name": "Outro",
            "email": "existente@example.com",
            "password": "Senha@123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("errors", response.context)
        self.assertTrue(len(response.context["errors"]) > 0)

    def test_post_cadastro_senha_invalida_retorna_erro(self):
        """Senha sem símbolo deve ser rejeitada pelo CustomPasswordValidator."""
        response = self.client.post(reverse("cadastro"), {
            "first_name": "Teste",
            "email": "teste@valida.com",
            "password": "semaiscula",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["errors"]) > 0)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SairViewTests(TestCase):
    """Testa a view de logout."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="sair@example.com",
            password="Senha@123",
            first_name="Sair"
        )

    def test_sair_redireciona_para_login(self):
        self.client.login(username="sair@example.com", password="Senha@123")
        response = self.client.get(reverse("sair"))
        self.assertRedirects(response, reverse("login"))


# ===========================================================================
# 8. TESTES DAS VIEWS — PERFIL E DASHBOARD
# ===========================================================================

class PerfilViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="perfil@example.com",
            password="Senha@123",
            first_name="Perfil"
        )

    def test_perfil_sem_login_redireciona_para_login(self):
        response = self.client.get(reverse("perfil"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('perfil')}")

    def test_perfil_com_login_retorna_200(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("perfil"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_com_login_retorna_200(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_retorna_saldo_calculado(self):
        """Dashboard deve somar ganhos/gastos e calcular saldo."""
        self.client.force_login(self.user)
        Transacao.objects.create(
            usuario=self.user, data=date(2025, 1, 1),
            descricao="Salário", valor=Decimal("3000"), tipo="income"
        )
        Transacao.objects.create(
            usuario=self.user, data=date(2025, 1, 5),
            descricao="Aluguel", valor=Decimal("800"), tipo="expense"
        )
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["ganhos"], Decimal("3000"))
        self.assertEqual(response.context["gastos"], Decimal("800"))
        self.assertEqual(response.context["saldo"], Decimal("2200"))


# ===========================================================================
# 9. TESTES DAS VIEWS — TRANSAÇÕES
# ===========================================================================

class TransacoesViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="trans@example.com",
            password="Senha@123",
            first_name="Trans"
        )
        self.client.force_login(self.user)

    def test_listar_transacoes_retorna_json(self):
        response = self.client.get(reverse("listar_transacoes"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("transacoes", data)

    def test_listar_transacoes_sem_login_redireciona(self):
        self.client.logout()
        response = self.client.get(reverse("listar_transacoes"))
        self.assertEqual(response.status_code, 302)

    def test_adicionar_transacao_post_valido(self):
        payload = {
            "data": "2025-03-10",
            "descricao": "Freelance",
            "valor": 500,
            "tipo": "income"
        }
        response = self.client.post(
            reverse("adicionar_transacao"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertTrue(
            Transacao.objects.filter(descricao="Freelance", usuario=self.user).exists()
        )

    def test_adicionar_transacao_metodo_invalido_retorna_405(self):
        response = self.client.get(reverse("adicionar_transacao"))
        self.assertEqual(response.status_code, 405)

    def test_excluir_transacao_existente(self):
        t = Transacao.objects.create(
            usuario=self.user, data=date(2025, 1, 1),
            descricao="A remover", valor=Decimal("100"), tipo="expense"
        )
        response = self.client.delete(
            reverse("excluir_transacao", kwargs={"transacao_id": t.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transacao.objects.filter(id=t.id).exists())

    def test_excluir_transacao_inexistente_retorna_404(self):
        response = self.client.delete(
            reverse("excluir_transacao", kwargs={"transacao_id": 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_transacoes_de_outro_usuario_nao_aparecem_na_listagem(self):
        """Usuário não deve ver transações de outros usuários."""
        outro = User.objects.create_user(
            email="outro@example.com",
            password="Senha@123",
            first_name="Outro"
        )
        Transacao.objects.create(
            usuario=outro, data=date(2025, 1, 1),
            descricao="Transação alheia", valor=Decimal("999"), tipo="income"
        )
        response = self.client.get(reverse("listar_transacoes"))
        descricoes = [t["descricao"] for t in response.json()["transacoes"]]
        self.assertNotIn("Transação alheia", descricoes)


# ===========================================================================
# 10. TESTES DAS VIEWS — METAS FINANCEIRAS
# ===========================================================================

class MetasViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="metas@example.com",
            password="Senha@123",
            first_name="Metas"
        )
        self.client.force_login(self.user)

    def _criar_meta(self, nome="Viagem", valor="1000"):
        return MetaFinanceira.objects.create(
            usuario=self.user,
            nome=nome,
            valor=Decimal(valor),
            data_inicial=date(2025, 1, 1),
            data_final=date(2025, 12, 31),
        )

    def test_listar_metas_json_retorna_lista(self):
        self._criar_meta()
        response = self.client.get(reverse("listar_metas_json"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("metas", data)
        self.assertEqual(len(data["metas"]), 1)

    def test_adicionar_meta_post_valido(self):
        payload = {
            "nome": "Carro",
            "valor": 20000,
            "data_inicial": "2025-01-01",
            "data_final": "2025-12-31"
        }
        response = self.client.post(
            reverse("adicionar_meta"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertTrue(MetaFinanceira.objects.filter(nome="Carro").exists())

    def test_adicionar_meta_dados_incompletos_retorna_400(self):
        payload = {"nome": "Sem valor"}
        response = self.client.post(
            reverse("adicionar_meta"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_adicionar_meta_valor_invalido_retorna_400(self):
        payload = {
            "nome": "Inválida",
            "valor": "abc",
            "data_inicial": "2025-01-01",
            "data_final": "2025-12-31"
        }
        response = self.client.post(
            reverse("adicionar_meta"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_adicionar_progresso_meta_aumenta_valor_atual(self):
        meta = self._criar_meta(valor="500")
        payload = {"valor": 200}
        response = self.client.post(
            reverse("adicionar_progresso_meta", kwargs={"meta_id": meta.id}),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        meta.refresh_from_db()
        self.assertEqual(meta.valor_atual, Decimal("200"))

    def test_adicionar_progresso_valor_zero_retorna_400(self):
        meta = self._criar_meta()
        payload = {"valor": 0}
        response = self.client.post(
            reverse("adicionar_progresso_meta", kwargs={"meta_id": meta.id}),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_adicionar_progresso_valor_negativo_retorna_400(self):
        meta = self._criar_meta()
        payload = {"valor": -50}
        response = self.client.post(
            reverse("adicionar_progresso_meta", kwargs={"meta_id": meta.id}),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_excluir_meta_existente(self):
        meta = self._criar_meta()
        response = self.client.delete(
            reverse("excluir_meta", kwargs={"meta_id": meta.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MetaFinanceira.objects.filter(id=meta.id).exists())

    def test_excluir_meta_de_outro_usuario_retorna_404(self):
        outro = User.objects.create_user(
            email="outro_meta@example.com",
            password="Senha@123",
            first_name="Outro"
        )
        meta = MetaFinanceira.objects.create(
            usuario=outro,
            nome="Meta alheia",
            valor=Decimal("300"),
            data_inicial=date(2025, 1, 1),
            data_final=date(2025, 6, 30),
        )
        response = self.client.delete(
            reverse("excluir_meta", kwargs={"meta_id": meta.id})
        )
        self.assertEqual(response.status_code, 404)

    def test_porcentagem_calculada_na_listagem(self):
        """JSON de metas deve incluir porcentagem calculada corretamente.
        Django serializa Decimal como string via DjangoJSONEncoder."""
        meta = self._criar_meta(valor="200")
        meta.adicionar_progresso(Decimal("50"))
        response = self.client.get(reverse("listar_metas_json"))
        metas = response.json()["metas"]
        # DjangoJSONEncoder serializa Decimal como string; cast para comparação
        self.assertAlmostEqual(float(metas[0]["porcentagem"]), 25.0, places=1)


# ===========================================================================
# 11. TESTES DAS VIEWS — LEMBRETES
# ===========================================================================

class LembretesViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="lemb2@example.com",
            password="Senha@123",
            first_name="Lemb2"
        )
        self.client.force_login(self.user)

    def test_listar_lembretes_retorna_json(self):
        response = self.client.get(reverse("listar_lembretes"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("lembretes", response.json())

    def test_adicionar_lembrete_post_valido(self):
        payload = {
            "nome": "Consulta médica",
            "descricao": "Dr. Silva",
            "data": "2025-07-15"
        }
        response = self.client.post(
            reverse("adicionar_lembrete"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertTrue(
            Lembrete.objects.filter(nome="Consulta médica", usuario=self.user).exists()
        )

    def test_adicionar_lembrete_sem_descricao(self):
        """Descrição é opcional — deve ser aceito sem ela."""
        payload = {"nome": "Reunião", "data": "2025-08-01"}
        response = self.client.post(
            reverse("adicionar_lembrete"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

    def test_adicionar_lembrete_metodo_get_retorna_405(self):
        response = self.client.get(reverse("adicionar_lembrete"))
        self.assertEqual(response.status_code, 405)

    def test_excluir_lembrete_existente(self):
        l = Lembrete.objects.create(
            usuario=self.user,
            nome="Expirado",
            data=date(2025, 1, 1)
        )
        response = self.client.delete(
            reverse("excluir_lembrete", kwargs={"lembrete_id": l.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Lembrete.objects.filter(id=l.id).exists())

    def test_excluir_lembrete_de_outro_usuario_retorna_404(self):
        outro = User.objects.create_user(
            email="outro_lemb@example.com",
            password="Senha@123",
            first_name="Outro"
        )
        l = Lembrete.objects.create(
            usuario=outro,
            nome="Lembrete alheio",
            data=date(2025, 3, 1)
        )
        response = self.client.delete(
            reverse("excluir_lembrete", kwargs={"lembrete_id": l.id})
        )
        self.assertEqual(response.status_code, 404)

    def test_lembretes_de_outro_usuario_nao_aparecem(self):
        outro = User.objects.create_user(
            email="outro_lemb2@example.com",
            password="Senha@123",
            first_name="Outro2"
        )
        Lembrete.objects.create(
            usuario=outro,
            nome="Lembrete sigiloso",
            data=date(2025, 4, 1)
        )
        response = self.client.get(reverse("listar_lembretes"))
        nomes = [l["nome"] for l in response.json()["lembretes"]]
        self.assertNotIn("Lembrete sigiloso", nomes)
