-- Execute este script no SQL Editor do Supabase após o schema.sql principal

CREATE TABLE IF NOT EXISTS drive_processed_files (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id             TEXT        NOT NULL UNIQUE,
    file_name           TEXT        NOT NULL,
    file_type           TEXT        NOT NULL,   -- 'pdf_extrato' | 'xlsx_fatura'
    processed_at        TIMESTAMPTZ DEFAULT NOW(),
    transactions_count  INTEGER     DEFAULT 0,
    status              TEXT        DEFAULT 'success',  -- 'success' | 'error'
    error_message       TEXT
);

CREATE INDEX IF NOT EXISTS idx_drive_processed_files_file_id ON drive_processed_files(file_id);
