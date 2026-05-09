'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, Legend, CartesianGrid } from 'recharts'

const fmt = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

export default function RelatorioPage() {
  const [monthly, setMonthly] = useState<{ month: string; receitas: number; despesas: number; saldo: number }[]>([])
  const [loading, setLoading] = useState(true)
  const [months, setMonths] = useState(6)

  useEffect(() => {
    async function load() {
      setLoading(true)
      const d = new Date(); d.setMonth(d.getMonth() - (months - 1)); d.setDate(1)
      const start = d.toISOString().split('T')[0]

      const { data } = await supabase
        .from('transactions')
        .select('amount, type, transaction_date')
        .gte('transaction_date', start)
        .order('transaction_date')

      if (!data) { setLoading(false); return }

      const map: Record<string, { receitas: number; despesas: number }> = {}
      data.forEach(t => {
        const m = t.transaction_date.slice(0, 7)
        if (!map[m]) map[m] = { receitas: 0, despesas: 0 }
        if (t.type === 'income') map[m].receitas += Number(t.amount)
        else map[m].despesas += Number(t.amount)
      })

      setMonthly(
        Object.entries(map)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([m, v]) => ({
            month: new Date(m + '-01').toLocaleString('pt-BR', { month: 'short', year: '2-digit' }),
            receitas: v.receitas,
            despesas: v.despesas,
            saldo: v.receitas - v.despesas,
          }))
      )
      setLoading(false)
    }
    load()
  }, [months])

  const totalReceitas = monthly.reduce((s, m) => s + m.receitas, 0)
  const totalDespesas = monthly.reduce((s, m) => s + m.despesas, 0)
  const mediaReceitas = monthly.length ? totalReceitas / monthly.length : 0
  const mediaDespesas = monthly.length ? totalDespesas / monthly.length : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Relatório</h1>
        <select
          value={months}
          onChange={e => setMonths(Number(e.target.value))}
          className="border rounded-lg px-3 py-1.5 text-sm bg-white"
        >
          <option value={3}>Últimos 3 meses</option>
          <option value={6}>Últimos 6 meses</option>
          <option value={12}>Últimos 12 meses</option>
        </select>
      </div>

      {loading ? <p className="text-sm text-gray-500">Carregando...</p> : (
        <>
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Total Receitas', value: totalReceitas, color: 'text-green-600' },
              { label: 'Total Despesas', value: totalDespesas, color: 'text-red-600' },
              { label: 'Média Receitas/mês', value: mediaReceitas, color: 'text-green-600' },
              { label: 'Média Despesas/mês', value: mediaDespesas, color: 'text-red-600' },
            ].map(({ label, value, color }) => (
              <Card key={label}>
                <CardHeader className="pb-2"><CardTitle className="text-xs text-gray-500 font-normal">{label}</CardTitle></CardHeader>
                <CardContent><p className={`text-xl font-bold ${color}`}>{fmt(value)}</p></CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader><CardTitle className="text-base">Receitas vs Despesas</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={monthly}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
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
            <CardHeader><CardTitle className="text-base">Evolução do Saldo</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={monthly}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `R$${(v/1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v) => fmt(Number(v))} />
                  <Line type="monotone" dataKey="saldo" stroke="#2563eb" strokeWidth={2} dot={{ r: 4 }} name="Saldo" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
