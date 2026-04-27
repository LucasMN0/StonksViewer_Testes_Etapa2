from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
from decimal import Decimal
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import json

from .models import CustomUser, Transacao, MetaFinanceira, Lembrete


class IntegracaoCadastroLoginTests(TestCase):
    """
    Fluxo 1: Cadastro com validação multicamada + Login
    Camadas: CustomPasswordValidator → CustomUserManager → login_view → sessão Django
    """

    def setUp(self):
        self.client = Client()

    def test_cadastro_valido_cria_usuario_e_autentica(self):
        """Cadastro com dados válidos cria usuário no banco e autentica automaticamente."""
        response = self.client.post(reverse('cadastro'), {
            'first_name': 'Lucas',
            'email': 'lucas@teste.com',
            'password': 'Senha@123',
        })
        self.assertRedirects(response, reverse('perfil'))
        self.assertTrue(CustomUser.objects.filter(email='lucas@teste.com').exists())

    def test_cadastro_senha_curta_nao_cria_usuario(self):
        """Senha com menos de 8 chars falha no CustomPasswordValidator e não cria usuário."""
        response = self.client.post(reverse('cadastro'), {
            'first_name': 'Lucas',
            'email': 'lucas@teste.com',
            'password': 'Ab@1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(email='lucas@teste.com').exists())

    def test_cadastro_senha_sem_maiuscula_nao_cria_usuario(self):
        """Senha sem letra maiúscula falha no CustomPasswordValidator."""
        response = self.client.post(reverse('cadastro'), {
            'first_name': 'Lucas',
            'email': 'lucas@teste.com',
            'password': 'senha@123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(email='lucas@teste.com').exists())

    def test_cadastro_senha_sem_simbolo_nao_cria_usuario(self):
        """Senha sem símbolo falha no CustomPasswordValidator."""
        response = self.client.post(reverse('cadastro'), {
            'first_name': 'Lucas',
            'email': 'lucas@teste.com',
            'password': 'SenhaSemSimbolo1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(email='lucas@teste.com').exists())

    def test_cadastro_email_duplicado_nao_cria_segundo_usuario(self):
        """Email já cadastrado retorna erro e mantém apenas um usuário."""
        CustomUser.objects.create_user(
            email='lucas@teste.com', password='Senha@123', first_name='Lucas'
        )
        response = self.client.post(reverse('cadastro'), {
            'first_name': 'Outro',
            'email': 'lucas@teste.com',
            'password': 'Senha@123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CustomUser.objects.filter(email='lucas@teste.com').count(), 1)

    def test_login_apos_cadastro_funciona(self):
        """Após cadastro, login com as mesmas credenciais deve autenticar com sucesso."""
        self.client.post(reverse('cadastro'), {
            'first_name': 'Lucas',
            'email': 'lucas@teste.com',
            'password': 'Senha@123',
        })
        self.client.logout()
        response = self.client.post(reverse('login'), {
            'email': 'lucas@teste.com',
            'password': 'Senha@123',
        })
        self.assertRedirects(response, reverse('perfil'))

    def test_login_com_senha_errada_nao_autentica(self):
        """Login com senha incorreta não cria sessão autenticada."""
        CustomUser.objects.create_user(
            email='lucas@teste.com', password='Senha@123', first_name='Lucas'
        )
        response = self.client.post(reverse('login'), {
            'email': 'lucas@teste.com',
            'password': 'SenhaErrada@1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class IntegracaoRecuperacaoSenhaTests(TestCase):
    """
    Fluxo 2: Recuperação e redefinição de senha
    Camadas: recuperar_senha view → CustomUser query → default_token_generator →
             send_mail (mock) → redefinir_senha view → CustomPasswordValidator → user.set_password()
    """

    def setUp(self):
        self.client = Client()
        self.usuario = CustomUser.objects.create_user(
            email='usuario@teste.com',
            password='SenhaAntiga@1',
            first_name='Usuario'
        )

    def _get_reset_url(self):
        uid = urlsafe_base64_encode(force_bytes(self.usuario.pk))
        token = default_token_generator.make_token(self.usuario)
        return reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})

    @patch('usuarios.views.send_mail')
    def test_recuperar_senha_email_existente_envia_email(self, mock_send_mail):
        """POST com email cadastrado deve chamar send_mail e redirecionar para login."""
        response = self.client.post(reverse('recuperar'), {'email': 'usuario@teste.com'})
        mock_send_mail.assert_called_once()
        self.assertRedirects(response, reverse('login'))

    @patch('usuarios.views.send_mail')
    def test_recuperar_senha_email_inexistente_nao_envia_email(self, mock_send_mail):
        """POST com email não cadastrado não deve chamar send_mail."""
        response = self.client.post(reverse('recuperar'), {'email': 'inexistente@teste.com'})
        mock_send_mail.assert_not_called()
        self.assertRedirects(response, reverse('recuperar'))

    def test_reset_token_valido_renderiza_formulario(self):
        """GET na URL de reset com token válido deve renderizar o formulário."""
        url = self._get_reset_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_reset_token_invalido_redireciona_para_recuperar(self):
        """GET com token inválido deve redirecionar para a página de recuperação."""
        uid = urlsafe_base64_encode(force_bytes(self.usuario.pk))
        url = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': 'token-invalido'})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('recuperar'))

    def test_reset_senha_valida_altera_senha_e_redireciona(self):
        """POST com nova senha válida deve alterar a senha e redirecionar para login."""
        url = self._get_reset_url()
        response = self.client.post(url, {
            'novaSenha': 'NovaSenha@456',
            'confirmarSenha': 'NovaSenha@456',
        })
        self.assertRedirects(response, reverse('login'))
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('NovaSenha@456'))

    def test_reset_senha_invalida_nao_altera_senha(self):
        """POST com senha que viola CustomPasswordValidator não deve alterar a senha."""
        url = self._get_reset_url()
        self.client.post(url, {
            'novaSenha': 'semaiuscula1@',
            'confirmarSenha': 'semaiuscula1@',
        })
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('SenhaAntiga@1'))

    def test_login_com_nova_senha_apos_reset(self):
        """Após reset bem-sucedido, login com a nova senha deve autenticar o usuário."""
        url = self._get_reset_url()
        self.client.post(url, {
            'novaSenha': 'NovaSenha@456',
            'confirmarSenha': 'NovaSenha@456',
        })
        self.client.logout()
        response = self.client.post(reverse('login'), {
            'email': 'usuario@teste.com',
            'password': 'NovaSenha@456',
        })
        self.assertRedirects(response, reverse('perfil'))


class IntegracaoTransacoesDashboardTests(TestCase):
    """
    Fluxo 3: Transações e cálculo do dashboard
    Camadas: adicionar_transacao view → Transacao.objects.create →
             dashboard view → lógica de agregação Python
    """

    def setUp(self):
        self.client = Client()
        self.usuario = CustomUser.objects.create_user(
            email='usuario@teste.com',
            password='Senha@123',
            first_name='Usuario'
        )
        self.client.force_login(self.usuario)

    def _adicionar_transacao(self, descricao, valor, tipo, data='2024-01-01'):
        return self.client.post(
            reverse('adicionar_transacao'),
            data=json.dumps({'descricao': descricao, 'valor': valor, 'tipo': tipo, 'data': data}),
            content_type='application/json'
        )

    def test_dashboard_soma_apenas_income_nos_ganhos(self):
        """Dashboard deve contabilizar apenas tipo 'income' nos ganhos."""
        self._adicionar_transacao('Salario', 3000, 'income')
        self._adicionar_transacao('Investimento', 500, 'investment')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['ganhos'], Decimal('3000'))

    def test_dashboard_soma_apenas_expense_nos_gastos(self):
        """Dashboard deve contabilizar apenas tipo 'expense' nos gastos."""
        self._adicionar_transacao('Aluguel', 1200, 'expense')
        self._adicionar_transacao('Lazer', 200, 'extra')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['gastos'], Decimal('1200'))

    def test_dashboard_calcula_saldo_correto(self):
        """Saldo deve ser igual a soma de income menos soma de expense."""
        self._adicionar_transacao('Salario', 3000, 'income')
        self._adicionar_transacao('Aluguel', 1200, 'expense')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['saldo'], Decimal('1800'))

    def test_dashboard_tipos_extras_nao_afetam_saldo(self):
        """Tipos 'investment', 'extra' e 'other' não devem alterar ganhos nem gastos."""
        self._adicionar_transacao('Aplicacao', 1000, 'investment')
        self._adicionar_transacao('Jantar', 100, 'extra')
        self._adicionar_transacao('Outro', 50, 'other')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['ganhos'], Decimal('0'))
        self.assertEqual(response.context['gastos'], Decimal('0'))
        self.assertEqual(response.context['saldo'], Decimal('0'))

    def test_dashboard_ignora_transacoes_de_outro_usuario(self):
        """Transações de outro usuário não devem aparecer no dashboard do usuário atual."""
        outro = CustomUser.objects.create_user(
            email='outro@teste.com', password='Senha@123', first_name='Outro'
        )
        Transacao.objects.create(
            usuario=outro, data='2024-01-01', descricao='Salario', valor=5000, tipo='income'
        )
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['ganhos'], Decimal('0'))

    def test_excluir_transacao_reflete_no_dashboard(self):
        """Excluir uma transação deve remover seu valor do dashboard."""
        resp = self._adicionar_transacao('Salario', 3000, 'income')
        transacao_id = json.loads(resp.content)['transacao']['id']
        self.client.delete(reverse('excluir_transacao', args=[transacao_id]))
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['ganhos'], Decimal('0'))


class IntegracaoMetaFinanceiraTests(TestCase):
    """
    Fluxo 4: Ciclo de vida completo de meta financeira
    Camadas: adicionar_meta view → MetaFinanceira.objects.create →
             adicionar_progresso_meta view → MetaFinanceira.adicionar_progresso() →
             listar_metas_json view
    """

    def setUp(self):
        self.client = Client()
        self.usuario = CustomUser.objects.create_user(
            email='usuario@teste.com',
            password='Senha@123',
            first_name='Usuario'
        )
        self.client.force_login(self.usuario)

    def _criar_meta(self, nome='Viagem', valor=1000):
        resp = self.client.post(
            reverse('adicionar_meta'),
            data=json.dumps({
                'nome': nome,
                'valor': valor,
                'data_inicial': '2024-01-01',
                'data_final': '2024-12-31',
            }),
            content_type='application/json'
        )
        return json.loads(resp.content)['meta']['id']

    def _adicionar_progresso(self, meta_id, valor):
        return self.client.post(
            reverse('adicionar_progresso_meta', args=[meta_id]),
            data=json.dumps({'valor': valor}),
            content_type='application/json'
        )

    def test_meta_criada_com_status_pendente(self):
        """Meta recém-criada deve ter status 'Pendente' e valor_atual igual a zero."""
        meta_id = self._criar_meta()
        meta = MetaFinanceira.objects.get(id=meta_id)
        self.assertEqual(meta.status, 'Pendente')
        self.assertEqual(meta.valor_atual, Decimal('0'))

    def test_progresso_parcial_muda_status_para_em_andamento(self):
        """Adicionar progresso parcial deve mudar o status para 'Em andamento'."""
        meta_id = self._criar_meta(valor=1000)
        self._adicionar_progresso(meta_id, 500)
        meta = MetaFinanceira.objects.get(id=meta_id)
        self.assertEqual(meta.status, 'Em andamento')
        self.assertEqual(meta.valor_atual, Decimal('500'))

    def test_progresso_completo_muda_status_para_concluida(self):
        """Ao atingir 100% do valor alvo, status deve mudar para 'Concluída'."""
        meta_id = self._criar_meta(valor=1000)
        self._adicionar_progresso(meta_id, 1000)
        meta = MetaFinanceira.objects.get(id=meta_id)
        self.assertEqual(meta.status, 'Concluída')

    def test_multiplos_progressos_acumulam_ate_concluir(self):
        """Múltiplos progressos parciais devem acumular até concluir a meta."""
        meta_id = self._criar_meta(valor=1000)
        self._adicionar_progresso(meta_id, 300)
        self._adicionar_progresso(meta_id, 400)
        self._adicionar_progresso(meta_id, 300)
        meta = MetaFinanceira.objects.get(id=meta_id)
        self.assertEqual(meta.status, 'Concluída')
        self.assertEqual(meta.valor_atual, Decimal('1000'))

    def test_listar_metas_retorna_porcentagem_calculada(self):
        """Endpoint de listagem deve retornar a porcentagem corretamente calculada."""
        meta_id = self._criar_meta(valor=1000)
        self._adicionar_progresso(meta_id, 250)
        response = self.client.get(reverse('listar_metas_json'))
        data = json.loads(response.content)
        meta_data = next(m for m in data['metas'] if m['id'] == meta_id)
        self.assertEqual(meta_data['porcentagem'], 25.0)

    def test_progresso_negativo_retorna_400_e_nao_altera_meta(self):
        """Valor negativo no progresso deve retornar 400 e não alterar a meta."""
        meta_id = self._criar_meta()
        response = self._adicionar_progresso(meta_id, -100)
        self.assertEqual(response.status_code, 400)
        meta = MetaFinanceira.objects.get(id=meta_id)
        self.assertEqual(meta.valor_atual, Decimal('0'))

    def test_excluir_meta_remove_da_listagem(self):
        """Após excluir meta, ela não deve mais aparecer na listagem JSON."""
        meta_id = self._criar_meta()
        self.client.delete(reverse('excluir_meta', args=[meta_id]))
        response = self.client.get(reverse('listar_metas_json'))
        data = json.loads(response.content)
        ids = [m['id'] for m in data['metas']]
        self.assertNotIn(meta_id, ids)


class IntegracaoIsolacaoDadosTests(TestCase):
    """
    Fluxo 5: Isolação de dados entre usuários
    Camadas: autenticação Django → filtros usuario=request.user em todas as views
    """

    def setUp(self):
        self.client_a = Client()
        self.client_b = Client()
        self.usuario_a = CustomUser.objects.create_user(
            email='a@teste.com', password='Senha@123', first_name='A'
        )
        self.usuario_b = CustomUser.objects.create_user(
            email='b@teste.com', password='Senha@123', first_name='B'
        )
        self.client_a.force_login(self.usuario_a)
        self.client_b.force_login(self.usuario_b)

    # --- Transações ---

    def test_transacao_de_a_nao_aparece_para_b(self):
        """Transação criada pelo usuário A não deve aparecer na listagem do usuário B."""
        Transacao.objects.create(
            usuario=self.usuario_a, data='2024-01-01',
            descricao='Salario A', valor=3000, tipo='income'
        )
        response = self.client_b.get(reverse('listar_transacoes'))
        data = json.loads(response.content)
        self.assertEqual(len(data['transacoes']), 0)

    def test_b_nao_pode_excluir_transacao_de_a(self):
        """Usuário B não deve conseguir excluir transação que pertence ao usuário A."""
        transacao = Transacao.objects.create(
            usuario=self.usuario_a, data='2024-01-01',
            descricao='Salario A', valor=3000, tipo='income'
        )
        response = self.client_b.delete(reverse('excluir_transacao', args=[transacao.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Transacao.objects.filter(id=transacao.id).exists())

    # --- Metas ---

    def test_meta_de_a_nao_aparece_para_b(self):
        """Meta criada pelo usuário A não deve aparecer na listagem do usuário B."""
        MetaFinanceira.objects.create(
            usuario=self.usuario_a, nome='Viagem', valor=1000,
            data_inicial='2024-01-01', data_final='2024-12-31'
        )
        response = self.client_b.get(reverse('listar_metas_json'))
        data = json.loads(response.content)
        self.assertEqual(len(data['metas']), 0)

    def test_b_nao_pode_excluir_meta_de_a(self):
        """Usuário B não deve conseguir excluir meta que pertence ao usuário A."""
        meta = MetaFinanceira.objects.create(
            usuario=self.usuario_a, nome='Viagem', valor=1000,
            data_inicial='2024-01-01', data_final='2024-12-31'
        )
        response = self.client_b.delete(reverse('excluir_meta', args=[meta.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(MetaFinanceira.objects.filter(id=meta.id).exists())

    def test_b_nao_pode_adicionar_progresso_em_meta_de_a(self):
        """Usuário B não deve conseguir adicionar progresso em meta do usuário A."""
        meta = MetaFinanceira.objects.create(
            usuario=self.usuario_a, nome='Viagem', valor=1000,
            data_inicial='2024-01-01', data_final='2024-12-31'
        )
        response = self.client_b.post(
            reverse('adicionar_progresso_meta', args=[meta.id]),
            data=json.dumps({'valor': 500}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
        meta.refresh_from_db()
        self.assertEqual(meta.valor_atual, Decimal('0'))

    # --- Lembretes ---

    def test_lembrete_de_a_nao_aparece_para_b(self):
        """Lembrete criado pelo usuário A não deve aparecer na listagem do usuário B."""
        Lembrete.objects.create(
            usuario=self.usuario_a, nome='Reuniao', data='2024-06-01'
        )
        response = self.client_b.get(reverse('listar_lembretes'))
        data = json.loads(response.content)
        self.assertEqual(len(data['lembretes']), 0)

    def test_b_nao_pode_excluir_lembrete_de_a(self):
        """Usuário B não deve conseguir excluir lembrete que pertence ao usuário A."""
        lembrete = Lembrete.objects.create(
            usuario=self.usuario_a, nome='Reuniao', data='2024-06-01'
        )
        response = self.client_b.delete(reverse('excluir_lembrete', args=[lembrete.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Lembrete.objects.filter(id=lembrete.id).exists())
