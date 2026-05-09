'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, TrendingDown, Wallet, Receipt } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'

const fmt = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

const COLORS = ['#16a34a','#dc2626','#ca8a04','#2563eb','#9333ea','#0891b2','#ea580c','#be185d']

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState({ income: 0, expense: 0, balance: 0, count: 0 })
  const [monthly, setMonthly] = useState<{ month: string; receitas: number; despesas: number }[]>([])
  const [byCategory, setByCategory] = useState<{ name: string; value: number }[]>([])
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  })

  useEffect(() => {
    async function load() {
      setLoading(true)
      const [y, m] = selectedMonth.split('-').map(Number)
      const start = `${selectedMonth}-01`
      const lastDay = new Date(y, m, 0).getDate()
      const end = `${selectedMonth}-${String(lastDay).padStart(2, '0')}`

      const [txRes, catRes] = await Promise.all([
        supabase.from('transactions').select('amount, type, category_id')
          .gte('transaction_date', start).lte('transaction_date', end),
        supabase.from('categories').select('id, name'),
      ])
      console.log('transactions:', txRes)
      console.log('categories:', catRes)

      const data = txRes.data
      const cats = catRes.data
      if (!data) { setLoading(false); return }

      const catById: Record<string, string> = {}
      cats?.forEach(c => { catById[c.id] = c.name })

      const income  = data.filter(t => t.type === 'income').reduce((s, t) => s + Number(t.amount), 0)
      const expense = data.filter(t => t.type === 'expense').reduce((s, t) => s + Number(t.amount), 0)
      setSummary({ income, expense, balance: income - expense, count: data.length })

      // by category (expenses only)
      const catMap: Record<string, number> = {}
      data.filter(t => t.type === 'expense').forEach(t => {
        const name = (t.category_id && catById[t.category_id]) ?? 'Sem categoria'
        catMap[name] = (catMap[name] ?? 0) + Number(t.amount)
      })
      setByCategory(
        Object.entries(catMap)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 8)
          .map(([name, value]) => ({ name, value }))
      )

      // last 6 months
      const { data: all } = await supabase
        .from('transactions')
        .select('amount, type, transaction_date')
        .gte('transaction_date', (() => {
          const d = new Date(); d.setMonth(d.getMonth() - 5); d.setDate(1); return d.toISOString().split('T')[0]
        })())

      if (all) {
        const map: Record<string, { receitas: number; despesas: number }> = {}
        all.forEach(t => {
          const m = t.transaction_date.slice(0, 7)
          if (!map[m]) map[m] = { receitas: 0, despesas: 0 }
          if (t.type === 'income') map[m].receitas += Number(t.amount)
          else map[m].despesas += Number(t.amount)
        })
        setMonthly(
          Object.entries(map)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([month, v]) => ({ month: month.slice(5) + '/' + month.slice(2, 4), ...v }))
        )
      }
      setLoading(false)
    }
    load()
  }, [selectedMonth])

  const months = Array.from({ length: 6 }, (_, i) => {
    const d = new Date(); d.setMonth(d.getMonth() - i)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Visão Geral</h1>
        <select
          value={selectedMonth}
          onChange={e => setSelectedMonth(e.target.value)}
          className="border rounded-lg px-3 py-1.5 text-sm bg-white"
        >
          {months.map(m => (
            <option key={m} value={m}>
              {new Date(m + '-01').toLocaleString('pt-BR', { month: 'long', year: 'numeric' })}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-gray-500 text-sm">Carregando...</div>
      ) : (
        <>
          <div className="grid grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-500 font-normal flex items-center gap-2"><TrendingUp size={14} className="text-green-500"/>Receitas</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold text-green-600">{fmt(summary.income)}</p></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-500 font-normal flex items-center gap-2"><TrendingDown size={14} className="text-red-500"/>Despesas</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold text-red-600">{fmt(summary.expense)}</p></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-500 font-normal flex items-center gap-2"><Wallet size={14} className="text-blue-500"/>Saldo</CardTitle></CardHeader>
              <CardContent><p className={`text-2xl font-bold ${summary.balance >= 0 ? 'text-blue-600' : 'text-red-600'}`}>{fmt(summary.balance)}</p></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-500 font-normal flex items-center gap-2"><Receipt size={14} className="text-gray-500"/>Transações</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold text-gray-700">{summary.count}</p></CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <Card>
              <CardHeader><CardTitle className="text-base">Evolução Mensal</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={monthly}>
                    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `R$${(v/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(v) => fmt(Number(v))} />
                    <Legend />
                    <Bar dataKey="receitas" fill="#16a34a" radius={[4,4,0,0]} />
                    <Bar dataKey="despesas" fill="#dc2626" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-base">Despesas por Categoria</CardTitle></CardHeader>
              <CardContent>
                {byCategory.length === 0 ? (
                  <p className="text-sm text-gray-500 py-8 text-center">Sem despesas no período</p>
                ) : (
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie data={byCategory} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${((percent ?? 0)*100).toFixed(0)}%`} labelLine={false} fontSize={11}>
                        {byCategory.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip formatter={(v) => fmt(Number(v))} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
