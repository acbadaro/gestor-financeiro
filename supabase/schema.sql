-- ============================================================
-- GESTOR FINANCEIRO PESSOAL — Schema completo
-- Execute este arquivo no SQL Editor do Supabase
-- ============================================================

-- Usuários (estende o auth do Supabase)
CREATE TABLE public.users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE,
    email       TEXT,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'contributor' CHECK (role IN ('admin', 'contributor')),
    is_active   BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Contas (cartão, corrente, outra)
CREATE TABLE public.accounts (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT NOT NULL,
    type       TEXT NOT NULL CHECK (type IN ('checking', 'credit_card', 'other')),
    balance    DECIMAL(12,2) DEFAULT 0,
    is_active  BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Categorias em árvore (pai → filho)
CREATE TABLE public.categories (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id      UUID REFERENCES public.categories(id) ON DELETE RESTRICT,
    name           TEXT NOT NULL,
    type           TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    classification TEXT CHECK (classification IN ('essential', 'controllable', 'avoidable')),
    is_active      BOOLEAN DEFAULT true,
    sort_order     INTEGER DEFAULT 0,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Transações
CREATE TABLE public.transactions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES public.users(id),
    account_id       UUID REFERENCES public.accounts(id),
    category_id      UUID REFERENCES public.categories(id),
    description      TEXT NOT NULL,
    amount           DECIMAL(12,2) NOT NULL CHECK (amount > 0),
    type             TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    classification   TEXT CHECK (classification IN ('essential', 'controllable', 'avoidable')),
    transaction_date DATE NOT NULL,
    is_recurring     BOOLEAN DEFAULT false,
    source           TEXT DEFAULT 'telegram' CHECK (source IN ('telegram', 'drive', 'manual')),
    is_confirmed     BOOLEAN DEFAULT false,
    notes            TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Bens (ativos)
CREATE TABLE public.assets (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT NOT NULL,
    value      DECIMAL(12,2) NOT NULL CHECK (value >= 0),
    asset_date DATE NOT NULL,
    notes      TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dívidas (passivos)
CREATE TABLE public.liabilities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    total_value     DECIMAL(12,2) NOT NULL CHECK (total_value >= 0),
    remaining_value DECIMAL(12,2) NOT NULL CHECK (remaining_value >= 0),
    monthly_payment DECIMAL(12,2),
    due_date        DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Metas de economia
CREATE TABLE public.goals (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,
    target_amount DECIMAL(12,2) NOT NULL CHECK (target_amount > 0),
    period        TEXT NOT NULL CHECK (period IN ('monthly', 'yearly')),
    category_id   UUID REFERENCES public.categories(id),
    is_active     BOOLEAN DEFAULT true,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Projeções mensais (IA sugere, usuário confirma)
CREATE TABLE public.projections (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id         UUID NOT NULL REFERENCES public.categories(id),
    month               DATE NOT NULL,
    ai_suggested_amount DECIMAL(12,2),
    user_adjusted_amount DECIMAL(12,2),
    is_confirmed        BOOLEAN DEFAULT false,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(category_id, month)
);

-- Estado das conversas do Telegram
CREATE TABLE public.conversation_states (
    telegram_id BIGINT PRIMARY KEY,
    state       TEXT,
    context     JSONB,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ÍNDICES
-- ============================================================
CREATE INDEX idx_transactions_date       ON public.transactions(transaction_date);
CREATE INDEX idx_transactions_user       ON public.transactions(user_id);
CREATE INDEX idx_transactions_category   ON public.transactions(category_id);
CREATE INDEX idx_transactions_type       ON public.transactions(type);
CREATE INDEX idx_categories_parent       ON public.categories(parent_id);

-- ============================================================
-- PLANO DE CONTAS INICIAL
-- ============================================================

-- ---- RECEITAS ----
INSERT INTO public.categories (id, name, type, classification, sort_order) VALUES
('ee000000-0000-0000-0000-000000000001', 'Receitas', 'income', 'essential', 1);

INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('ee000000-0000-0000-0000-000000000011', 'ee000000-0000-0000-0000-000000000001', 'Salário / Pró-labore',         'income', 'essential',    1),
('ee000000-0000-0000-0000-000000000012', 'ee000000-0000-0000-0000-000000000001', 'Freelance / Renda Extra',      'income', 'controllable', 2),
('ee000000-0000-0000-0000-000000000013', 'ee000000-0000-0000-0000-000000000001', 'Rendimentos / Investimentos',  'income', 'essential',    3),
('ee000000-0000-0000-0000-000000000014', 'ee000000-0000-0000-0000-000000000001', 'Aluguel Recebido',             'income', 'essential',    4),
('ee000000-0000-0000-0000-000000000015', 'ee000000-0000-0000-0000-000000000001', 'Outros Recebimentos',          'income', 'controllable', 5);

-- ---- DESPESAS ----
INSERT INTO public.categories (id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0000-000000000001', 'Despesas', 'expense', 'essential', 2);

-- Moradia
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0001-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Moradia', 'expense', 'essential', 1);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0001-000000000011', 'd0000000-0000-0000-0001-000000000001', 'Aluguel / Financiamento', 'expense', 'essential', 1),
('d0000000-0000-0000-0001-000000000012', 'd0000000-0000-0000-0001-000000000001', 'Condomínio',              'expense', 'essential', 2),
('d0000000-0000-0000-0001-000000000013', 'd0000000-0000-0000-0001-000000000001', 'IPTU / Taxas',            'expense', 'essential', 3),
('d0000000-0000-0000-0001-000000000014', 'd0000000-0000-0000-0001-000000000001', 'Água e Esgoto',           'expense', 'essential', 4),
('d0000000-0000-0000-0001-000000000015', 'd0000000-0000-0000-0001-000000000001', 'Energia Elétrica',        'expense', 'essential', 5),
('d0000000-0000-0000-0001-000000000016', 'd0000000-0000-0000-0001-000000000001', 'Gás',                     'expense', 'essential', 6),
('d0000000-0000-0000-0001-000000000017', 'd0000000-0000-0000-0001-000000000001', 'Internet / Telefone',     'expense', 'essential', 7),
('d0000000-0000-0000-0001-000000000018', 'd0000000-0000-0000-0001-000000000001', 'Manutenção / Reformas',   'expense', 'controllable', 8);

-- Alimentação
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0002-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Alimentação', 'expense', 'essential', 2);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0002-000000000011', 'd0000000-0000-0000-0002-000000000001', 'Supermercado',             'expense', 'essential', 1),
('d0000000-0000-0000-0002-000000000012', 'd0000000-0000-0000-0002-000000000001', 'Feira / Hortifruti',       'expense', 'essential', 2),
('d0000000-0000-0000-0002-000000000013', 'd0000000-0000-0000-0002-000000000001', 'Padaria / Açougue',        'expense', 'essential', 3),
('d0000000-0000-0000-0002-000000000014', 'd0000000-0000-0000-0002-000000000001', 'Refeições no Trabalho',    'expense', 'essential', 4);

-- Saúde
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0003-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Saúde', 'expense', 'essential', 3);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0003-000000000011', 'd0000000-0000-0000-0003-000000000001', 'Plano de Saúde',     'expense', 'essential', 1),
('d0000000-0000-0000-0003-000000000012', 'd0000000-0000-0000-0003-000000000001', 'Medicamentos',       'expense', 'essential', 2),
('d0000000-0000-0000-0003-000000000013', 'd0000000-0000-0000-0003-000000000001', 'Consultas / Exames', 'expense', 'essential', 3),
('d0000000-0000-0000-0003-000000000014', 'd0000000-0000-0000-0003-000000000001', 'Academia',           'expense', 'controllable', 4);

-- Transporte
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0004-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Transporte', 'expense', 'essential', 4);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0004-000000000011', 'd0000000-0000-0000-0004-000000000001', 'Combustível',             'expense', 'essential',    1),
('d0000000-0000-0000-0004-000000000012', 'd0000000-0000-0000-0004-000000000001', 'IPVA / Seguro Veículo',   'expense', 'essential',    2),
('d0000000-0000-0000-0004-000000000013', 'd0000000-0000-0000-0004-000000000001', 'Manutenção Veículo',      'expense', 'essential',    3),
('d0000000-0000-0000-0004-000000000014', 'd0000000-0000-0000-0004-000000000001', 'Transporte Público / App','expense', 'essential',    4),
('d0000000-0000-0000-0004-000000000015', 'd0000000-0000-0000-0004-000000000001', 'Estacionamento / Pedágio','expense', 'controllable', 5);

-- Educação
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0005-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Educação', 'expense', 'essential', 5);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0005-000000000011', 'd0000000-0000-0000-0005-000000000001', 'Mensalidade',          'expense', 'essential',    1),
('d0000000-0000-0000-0005-000000000012', 'd0000000-0000-0000-0005-000000000001', 'Cursos / Capacitação', 'expense', 'controllable', 2),
('d0000000-0000-0000-0005-000000000013', 'd0000000-0000-0000-0005-000000000001', 'Material / Livros',    'expense', 'controllable', 3);

-- Serviços Financeiros
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0006-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Serviços Financeiros', 'expense', 'essential', 6);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0006-000000000011', 'd0000000-0000-0000-0006-000000000001', 'Parcelas / Empréstimos', 'expense', 'essential', 1),
('d0000000-0000-0000-0006-000000000012', 'd0000000-0000-0000-0006-000000000001', 'Seguros',                'expense', 'essential', 2),
('d0000000-0000-0000-0006-000000000013', 'd0000000-0000-0000-0006-000000000001', 'Tarifas Bancárias',      'expense', 'essential', 3);

-- Vestuário
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0007-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Vestuário', 'expense', 'controllable', 7);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0007-000000000011', 'd0000000-0000-0000-0007-000000000001', 'Roupas',              'expense', 'controllable', 1),
('d0000000-0000-0000-0007-000000000012', 'd0000000-0000-0000-0007-000000000001', 'Calçados / Acessórios','expense', 'controllable', 2);

-- Lazer e Entretenimento
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0008-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Lazer e Entretenimento', 'expense', 'controllable', 8);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0008-000000000011', 'd0000000-0000-0000-0008-000000000001', 'Streaming / Assinaturas', 'expense', 'controllable', 1),
('d0000000-0000-0000-0008-000000000012', 'd0000000-0000-0000-0008-000000000001', 'Restaurantes / Bares',    'expense', 'controllable', 2),
('d0000000-0000-0000-0008-000000000013', 'd0000000-0000-0000-0008-000000000001', 'Viagens / Hospedagem',    'expense', 'controllable', 3),
('d0000000-0000-0000-0008-000000000014', 'd0000000-0000-0000-0008-000000000001', 'Hobbies / Eventos',       'expense', 'controllable', 4);

-- Tecnologia
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0009-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Tecnologia', 'expense', 'controllable', 9);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0009-000000000011', 'd0000000-0000-0000-0009-000000000001', 'Equipamentos / Eletrônicos', 'expense', 'controllable', 1),
('d0000000-0000-0000-0009-000000000012', 'd0000000-0000-0000-0009-000000000001', 'Apps / Software',            'expense', 'controllable', 2);

-- Presentes e Doações
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0010-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Presentes e Doações', 'expense', 'controllable', 10);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0010-000000000011', 'd0000000-0000-0000-0010-000000000001', 'Presentes', 'expense', 'controllable', 1),
('d0000000-0000-0000-0010-000000000012', 'd0000000-0000-0000-0010-000000000001', 'Doações',   'expense', 'controllable', 2);

-- Cuidados Pessoais
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0011-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Cuidados Pessoais', 'expense', 'controllable', 11);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0011-000000000011', 'd0000000-0000-0000-0011-000000000001', 'Beleza / Estética', 'expense', 'controllable', 1),
('d0000000-0000-0000-0011-000000000012', 'd0000000-0000-0000-0011-000000000001', 'Higiene Pessoal',   'expense', 'controllable', 2);

-- Despesas Diversas
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0012-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Despesas Diversas', 'expense', 'avoidable', 12);
INSERT INTO public.categories (id, parent_id, name, type, classification, sort_order) VALUES
('d0000000-0000-0000-0012-000000000011', 'd0000000-0000-0000-0012-000000000001', 'Multas / Juros',       'expense', 'avoidable', 1),
('d0000000-0000-0000-0012-000000000012', 'd0000000-0000-0000-0012-000000000001', 'Compras por Impulso',  'expense', 'avoidable', 2),
('d0000000-0000-0000-0012-000000000013', 'd0000000-0000-0000-0012-000000000001', 'Outros',               'expense', 'avoidable', 3);

-- ============================================================
-- CONTAS PADRÃO
-- ============================================================
INSERT INTO public.accounts (name, type) VALUES
('Conta Corrente', 'checking'),
('Cartão de Crédito', 'credit_card');
