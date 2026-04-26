# Guia de Configuração — Gestor Financeiro

Siga os passos na ordem. Cada passo leva entre 2 e 5 minutos.

---

## PASSO 1 — Criar o Bot no Telegram

1. Abra o Telegram e procure por **@BotFather**
2. Envie o comando: `/newbot`
3. Dê um nome para o bot (ex: `Gestor Financeiro`)
4. Dê um username (ex: `meu_gestor_bot`) — precisa terminar em `bot`
5. O BotFather vai te enviar um **Token** no formato `123456789:AABB...`
6. **Guarde esse token** — você vai usá-lo no `.env`

Para descobrir seu próprio Telegram ID:
- Procure por **@userinfobot** no Telegram
- Envie qualquer mensagem
- Ele retorna seu ID numérico (ex: `987654321`)

---

## PASSO 2 — Obter a chave do Google Gemini (gratuita)

1. Acesse: https://aistudio.google.com/app/apikey
2. Clique em **Create API Key**
3. Selecione ou crie um projeto Google
4. **Copie a chave** gerada

---

## PASSO 3 — Criar projeto no Supabase

1. Acesse: https://app.supabase.com
2. Clique em **New Project**
3. Dê um nome (ex: `gestor-financeiro`) e defina uma senha forte
4. Aguarde o projeto ser criado (~1 minuto)
5. Vá em **Settings → API**
6. Copie:
   - **Project URL** (ex: `https://xxxxxx.supabase.co`)
   - **anon public key** (chave longa)

### Criar as tabelas:
1. No painel do Supabase, vá em **SQL Editor**
2. Clique em **New Query**
3. Abra o arquivo `supabase/schema.sql` deste projeto
4. Cole todo o conteúdo no editor
5. Clique em **Run** (▶️)
6. Deve aparecer "Success" para cada comando

### Cadastrar você como usuário admin:
Execute este SQL no editor (troque pelos seus dados):
```sql
INSERT INTO public.users (telegram_id, name, role, is_active)
VALUES (SEU_TELEGRAM_ID, 'Seu Nome', 'admin', true);
```

### Cadastrar outros usuários (contribuidores):
```sql
INSERT INTO public.users (telegram_id, name, role, is_active)
VALUES (TELEGRAM_ID_USUARIO, 'Nome do Usuário', 'contributor', true);
```

---

## PASSO 4 — Configurar o arquivo .env

1. Na pasta `backend/`, copie o arquivo `.env.example` e renomeie para `.env`
2. Preencha com os valores que você coletou:

```
TELEGRAM_BOT_TOKEN=cole_aqui_o_token_do_botfather
GEMINI_API_KEY=cole_aqui_a_chave_do_gemini
SUPABASE_URL=cole_aqui_a_url_do_supabase
SUPABASE_KEY=cole_aqui_a_anon_key_do_supabase
ADMIN_TELEGRAM_IDS=cole_aqui_seu_telegram_id
```

---

## PASSO 5 — Criar conta no Render (hospedagem do bot)

1. Acesse: https://render.com
2. Clique em **Get Started for Free**
3. Faça login com sua conta GitHub

### Subir o código para o GitHub:
1. Acesse: https://github.com/new
2. Crie um repositório privado chamado `gestor-financeiro`
3. No seu computador, abra o terminal na pasta `gestor-financeiro/`
4. Execute:
```bash
git init
git add .
git commit -m "fase 1 - bot telegram"
git remote add origin https://github.com/SEU_USUARIO/gestor-financeiro.git
git push -u origin main
```

### Criar o serviço no Render:
1. No Render, clique em **New → Web Service**
2. Conecte ao repositório `gestor-financeiro`
3. Configure:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. Em **Environment Variables**, adicione as mesmas variáveis do seu `.env`
5. Clique em **Create Web Service**
6. Aguarde o deploy (~3 minutos)

---

## PASSO 6 — Testar o bot

1. Abra o Telegram
2. Procure pelo nome do bot que você criou
3. Envie `/start`
4. Deve aparecer a mensagem de boas-vindas
5. Envie: `gastei 50 reais no supermercado hoje`
6. O bot deve mostrar a transação classificada e pedir confirmação

---

## Solução de problemas

**Bot não responde:**
- Verifique se o serviço no Render está "Live" (verde)
- Confirme que o `TELEGRAM_BOT_TOKEN` está correto
- Veja os logs no Render (aba Logs)

**Erro de banco de dados:**
- Confirme que o `SUPABASE_URL` e `SUPABASE_KEY` estão corretos
- Verifique se o schema foi executado com sucesso

**Usuário não autorizado:**
- Confirme que seu `telegram_id` foi inserido na tabela `users`
- Verifique se `is_active = true`
