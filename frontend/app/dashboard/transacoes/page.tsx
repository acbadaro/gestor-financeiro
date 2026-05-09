'use client'
import { useEffect, useState, useRef } from 'react'
import { supabase } from '@/lib/supabase'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const fmt = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

const clsBadge: Record<string, string> = {
  essential:    'bg-red-100 text-red-700',
  controllable: 'bg-yellow-100 text-yellow-700',
  avoidable:    'bg-green-100 text-green-700',
}
const clsLabel: Record<string, string> = {
  essential: 'Essencial', controllable: 'Controlável', avoidable: 'Evitável',
}

type Cat = { id: string; name: string; parent_id: string | null; type: string }
type Tx  = {
  id: string; description: string; amount: number; type: string
  classification: string | null; transaction_date: string; category_id: string | null
}

export default function TransacoesPage() {
  const [transactions, setTransactions] = useState<Tx[]>([])
  const [cats, setCats] = useState<Cat[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ type: 'all', month: '' })
  const [editingCat, setEditingCat] = useState<string | null>(null) // tx.id being edited

  const currentMonth = (() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  })()

  useEffect(() => { setFilter(f => ({ ...f, month: currentMonth })) }, [])

  useEffect(() => {
    supabase.from('categories').select('id, name, parent_id, type').then(({ data }) => {
      setCats((data as Cat[]) ?? [])
    })
  }, [])

  useEffect(() => {
    if (!filter.month) return
    async function load() {
      setLoading(true)
      const [y, mo] = filter.month.split('-').map(Number)
      const start = `${filter.month}-01`
      const lastDay = new Date(y, mo, 0).getDate()
      const end = `${filter.month}-${String(lastDay).padStart(2, '0')}`

      let q = supabase.from('transactions').select('*')
        .gte('transaction_date', start).lte('transaction_date', end)
        .order('transaction_date', { ascending: false })
      if (filter.type !== 'all') q = q.eq('type', filter.type)

      const { data } = await q
      setTransactions((data as Tx[]) ?? [])
      setLoading(false)
    }
    load()
  }, [filter])

  const months = Array.from({ length: 12 }, (_, i) => {
    const d = new Date(); d.setMonth(d.getMonth() - i)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  })

  // category helpers
  const catById = Object.fromEntries(cats.map(c => [c.id, c]))
  const roots  = cats.filter(c => !c.parent_id)
  const groups = cats.filter(c => c.parent_id && roots.some(r => r.id === c.parent_id))
  const leaves = cats.filter(c => c.parent_id && groups.some(g => g.id === c.parent_id))

  function getGroup(categoryId: string | null): Cat | null {
    if (!categoryId) return null
    const leaf = catById[categoryId]
    if (!leaf) return null
    if (leaf.parent_id && groups.some(g => g.id === leaf.parent_id)) return catById[leaf.parent_id] ?? null
    if (groups.some(g => g.id === leaf.id)) return leaf
    return null
  }

  function getLeaf(categoryId: string | null): Cat | null {
    if (!categoryId) return null
    const cat = catById[categoryId]
    if (!cat) return null
    return leaves.some(l => l.id === cat.id) ? cat : null
  }

  async function updateCategory(txId: string, categoryId: string | null) {
    await supabase.from('transactions').update({ category_id: categoryId }).eq('id', txId)
    setTransactions(prev => prev.map(t => t.id === txId ? { ...t, category_id: categoryId } : t))
    setEditingCat(null)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Transações</h1>

      <div className="flex gap-3">
        <select value={filter.month} onChange={e => setFilter(f => ({ ...f, month: e.target.value }))}
          className="border rounded-lg px-3 py-1.5 text-sm bg-white">
          {months.map(m => (
            <option key={m} value={m}>
              {new Date(m + '-01T12:00:00').toLocaleString('pt-BR', { month: 'long', year: 'numeric' })}
            </option>
          ))}
        </select>
        <select value={filter.type} onChange={e => setFilter(f => ({ ...f, type: e.target.value }))}
          className="border rounded-lg px-3 py-1.5 text-sm bg-white">
          <option value="all">Todos</option>
          <option value="expense">Despesas</option>
          <option value="income">Receitas</option>
        </select>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">{transactions.length} transação(ões)</CardTitle></CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="text-sm text-gray-500 p-6">Carregando...</p>
          ) : transactions.length === 0 ? (
            <p className="text-sm text-gray-500 p-6 text-center">Nenhuma transação no período.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-3 font-medium">Data</th>
                    <th className="px-4 py-3 font-medium">Descrição</th>
                    <th className="px-4 py-3 font-medium">Categoria</th>
                    <th className="px-4 py-3 font-medium">Subcategoria</th>
                    <th className="px-4 py-3 font-medium">Classif.</th>
                    <th className="px-4 py-3 font-medium text-right">Valor</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {transactions.map(tx => {
                    const group = getGroup(tx.category_id)
                    const leaf  = getLeaf(tx.category_id)
                    const txGroups = groups.filter(g => g.type === tx.type)
                    const txLeaves = (groupId: string) => leaves.filter(l => l.parent_id === groupId)
                    const isEditing = editingCat === tx.id

                    return (
                      <tr key={tx.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                          {new Date(tx.transaction_date + 'T12:00:00').toLocaleDateString('pt-BR')}
                        </td>
                        <td className="px-4 py-3 text-gray-900 max-w-xs truncate">{tx.description}</td>

                        {/* Categoria (grupo) */}
                        <td className="px-4 py-3">
                          {isEditing ? (
                            <select
                              autoFocus
                              className="border rounded px-2 py-1 text-xs bg-white w-36"
                              defaultValue={group?.id ?? ''}
                              onChange={e => {
                                const firstLeaf = txLeaves(e.target.value)[0]
                                if (firstLeaf) updateCategory(tx.id, firstLeaf.id)
                              }}
                            >
                              <option value="">— Geral —</option>
                              {txGroups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                            </select>
                          ) : (
                            <button
                              onClick={() => setEditingCat(tx.id)}
                              className="text-left text-gray-700 hover:text-blue-600 hover:underline"
                            >
                              {group?.name ?? <span className="text-gray-400 italic">Geral</span>}
                            </button>
                          )}
                        </td>

                        {/* Subcategoria (folha) */}
                        <td className="px-4 py-3">
                          {isEditing ? (
                            <div className="flex items-center gap-1">
                              <select
                                className="border rounded px-2 py-1 text-xs bg-white w-36"
                                defaultValue={leaf?.id ?? ''}
                                onChange={e => updateCategory(tx.id, e.target.value || null)}
                              >
                                <option value="">— Geral —</option>
                                {group && txLeaves(group.id).map(l => (
                                  <option key={l.id} value={l.id}>{l.name}</option>
                                ))}
                              </select>
                              <button onClick={() => setEditingCat(null)} className="text-gray-400 hover:text-gray-600 text-xs">✕</button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setEditingCat(tx.id)}
                              className="text-left text-gray-600 hover:text-blue-600 hover:underline"
                            >
                              {leaf?.name ?? <span className="text-gray-400 italic">—</span>}
                            </button>
                          )}
                        </td>

                        <td className="px-4 py-3">
                          {tx.classification && (
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${clsBadge[tx.classification]}`}>
                              {clsLabel[tx.classification]}
                            </span>
                          )}
                        </td>
                        <td className={`px-4 py-3 text-right font-semibold whitespace-nowrap ${tx.type === 'income' ? 'text-green-600' : 'text-red-600'}`}>
                          {tx.type === 'income' ? '+' : '-'}{fmt(Number(tx.amount))}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
