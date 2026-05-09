import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export type Transaction = {
  id: string
  description: string
  amount: number
  type: 'income' | 'expense'
  classification: 'essential' | 'controllable' | 'avoidable' | null
  transaction_date: string
  source: string
  is_confirmed: boolean
  category_id: string | null
  categories?: { name: string; parent_id: string | null } | null
}

export type Category = {
  id: string
  name: string
  type: 'income' | 'expense'
  parent_id: string | null
  classification: string | null
}
