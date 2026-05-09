'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Legend } from 'recharts'

const fmt = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const COLORS = ['#dc2626','#ea580c','#ca8a04','#16a34a','#2563eb','#9333ea','#0891b2','#be185d','#65a30d','#0d9488']

export default function CategoriasPage() {
  const [data, setData]     = useState<{ name: string; value: number }[]>([])
  const [loading, setLoading] = useState(true)
  const [month, setMonth] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  })

  const months = Array.from({ length: 12 }, (_, i) => {
    const d = new Date(); d.setMonth(d.getMonth() - i)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  })

  useEffect(() => {
    async function load() {
      setLoading(true)
      const [y, mo] = month.split('-').map(Number)
      const start = `${month}-01`
      const lastDay = new Date(y, mo, 0).getDate()
      const end = `${month}-${String(lastDay).padStart(2, '0')}`

      const [{ data: rows }, { data: cats }] = await Promise.all([
        supabase.from('transactions').select('amount, category_id')
          .eq('type', 'expense').gte('transaction_date', start).lte('transaction_date', end),
        supabase.from('categories').select('id, name'),
      ])

      if (!rows) { setLoading(false); return }

      const catById: Record<string, string> = {}
      cats?.forEach(c => { catById[c.id] = c.name })

      const map: Record<string, number> = {}
      rows.forEach(r => {
        const name = (r.category_id && catById[r.category_id]) ?? 'Sem categoria'
        map[name] = (map[name] ?? 0) + Number(r.amount)
      })

      setData(
        Object.entries(map)
          .sort((a, b) => b[1] - a[1])
          .map(([name, value]) => ({ name, value }))
      )
      setLoading(false)
    }
    load()
  }, [month])

  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Despesas por Categoria</h1>
        <select
          value={month}
          onChange={e => setMonth(e.target.value)}
          className="border rounded-lg px-3 py-1.5 text-sm bg-white"
        >
          {months.map(m => (
            <option key={m} value={m}>
              {new Date(m + '-01').toLocaleString('pt-BR', { month: 'long', year: 'numeric' })}
            </option>
          ))}
        </select>
      </div>

      {loading ? <p className="text-sm text-gray-500">Carregando...</p> : (
        <>
          <div className="grid grid-cols-2 gap-6">
            <Card>
              <CardHeader><CardTitle className="text-base">Distribuição</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100}>
                      {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(v) => fmt(Number(v))} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-base">Ranking</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.slice(0, 8)} layout="vertical">
                    <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={v => `R$${(v/1000).toFixed(1)}k`} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={120} />
                    <Tooltip formatter={(v) => fmt(Number(v))} />
                    <Bar dataKey="value" fill="#dc2626" radius={[0,4,4,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle className="text-base">Detalhamento</CardTitle></CardHeader>
            <CardContent>
              <div className="divide-y">
                {data.map((d, i) => (
                  <div key={d.name} className="flex items-center gap-4 py-3">
                    <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                    <span className="flex-1 text-sm text-gray-700">{d.name}</span>
                    <span className="text-sm font-medium text-gray-900">{fmt(d.value)}</span>
                    <span className="text-xs text-gray-500 w-12 text-right">{((d.value / total) * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
              <div className="flex justify-between pt-4 border-t mt-2">
                <span className="text-sm font-semibold text-gray-700">Total</span>
                <span className="text-sm font-bold text-red-600">{fmt(total)}</span>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
