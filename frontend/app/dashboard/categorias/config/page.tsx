'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Plus, Pencil, Trash2, ChevronRight, ChevronDown, X, Check } from 'lucide-react'

type Category = {
  id: string
  name: string
  type: 'income' | 'expense'
  classification: 'essential' | 'controllable' | 'avoidable' | null
  parent_id: string | null
  is_active: boolean
  sort_order: number
}

const CLS_OPTS = [
  { value: 'essential',    label: 'Essencial' },
  { value: 'controllable', label: 'Controlável' },
  { value: 'avoidable',    label: 'Evitável' },
]
const CLS_COLOR: Record<string, string> = {
  essential: 'bg-red-100 text-red-700',
  controllable: 'bg-yellow-100 text-yellow-700',
  avoidable: 'bg-green-100 text-green-700',
}

const emptyForm = { name: '', type: 'expense' as 'expense'|'income', classification: 'controllable' as string, parent_id: '' }

export default function CategoriasConfigPage() {
  const [cats, setCats] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [modal, setModal] = useState<{ open: boolean; editing: Category | null }>({ open: false, editing: null })
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    const { data } = await supabase.from('categories').select('*').order('sort_order').order('name')
    setCats((data as Category[]) ?? [])
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const roots = cats.filter(c => !c.parent_id)
  const childrenOf = (id: string) => cats.filter(c => c.parent_id === id)

  function openAdd(parentId?: string) {
    setForm({ ...emptyForm, parent_id: parentId ?? '' })
    setModal({ open: true, editing: null })
  }

  function openEdit(cat: Category) {
    setForm({ name: cat.name, type: cat.type, classification: cat.classification ?? 'controllable', parent_id: cat.parent_id ?? '' })
    setModal({ open: true, editing: cat })
  }

  async function save() {
    if (!form.name.trim()) return
    setSaving(true)
    const payload = {
      name: form.name.trim(),
      type: form.type,
      classification: form.classification,
      parent_id: form.parent_id || null,
      is_active: true,
    }
    if (modal.editing) {
      await supabase.from('categories').update(payload).eq('id', modal.editing.id)
    } else {
      await supabase.from('categories').insert(payload)
    }
    setSaving(false)
    setModal({ open: false, editing: null })
    load()
  }

  async function del(id: string) {
    await supabase.from('categories').delete().eq('id', id)
    setDeleteId(null)
    load()
  }

  function toggle(id: string) {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function renderCat(cat: Category, depth = 0) {
    const children = childrenOf(cat.id)
    const hasChildren = children.length > 0
    const isExpanded = expanded.has(cat.id)

    return (
      <div key={cat.id}>
        <div className={`flex items-center gap-2 py-2 px-3 rounded-lg hover:bg-gray-50 group ${depth > 0 ? 'ml-6' : ''}`}>
          <button onClick={() => hasChildren && toggle(cat.id)} className="w-4 flex-shrink-0 text-gray-400">
            {hasChildren ? (isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : <span className="w-3.5 inline-block" />}
          </button>
          <span className="flex-1 text-sm text-gray-800">{cat.name}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${cat.type === 'income' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
            {cat.type === 'income' ? 'Receita' : 'Despesa'}
          </span>
          {cat.classification && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${CLS_COLOR[cat.classification]}`}>
              {CLS_OPTS.find(o => o.value === cat.classification)?.label}
            </span>
          )}
          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button onClick={() => openAdd(cat.id)} className="p-1 text-gray-400 hover:text-green-600" title="Adicionar subcategoria">
              <Plus size={14} />
            </button>
            <button onClick={() => openEdit(cat)} className="p-1 text-gray-400 hover:text-blue-600" title="Editar">
              <Pencil size={14} />
            </button>
            <button onClick={() => setDeleteId(cat.id)} className="p-1 text-gray-400 hover:text-red-600" title="Excluir">
              <Trash2 size={14} />
            </button>
          </div>
        </div>
        {hasChildren && isExpanded && children.map(c => renderCat(c, depth + 1))}
      </div>
    )
  }

  const parentOptions = cats.filter(c => !c.parent_id)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Categorias</h1>
        <Button onClick={() => openAdd()} className="bg-green-600 hover:bg-green-700 text-white gap-2">
          <Plus size={16} /> Nova Categoria
        </Button>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Árvore de Categorias</CardTitle></CardHeader>
        <CardContent>
          {loading ? <p className="text-sm text-gray-500">Carregando...</p> : (
            <div className="divide-y">
              {roots.map(cat => renderCat(cat))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal Cadastro/Edição */}
      {modal.open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">{modal.editing ? 'Editar Categoria' : 'Nova Categoria'}</h2>
              <button onClick={() => setModal({ open: false, editing: null })}><X size={18} className="text-gray-400" /></button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Nome</label>
                <input
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Ex: Alimentação"
                  autoFocus
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Subcategoria de</label>
                <select
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                  value={form.parent_id}
                  onChange={e => setForm(f => ({ ...f, parent_id: e.target.value }))}
                >
                  <option value="">— Categoria raiz —</option>
                  {parentOptions.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Tipo</label>
                  <select
                    className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                    value={form.type}
                    onChange={e => setForm(f => ({ ...f, type: e.target.value as 'income'|'expense' }))}
                  >
                    <option value="expense">Despesa</option>
                    <option value="income">Receita</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Classificação</label>
                  <select
                    className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                    value={form.classification}
                    onChange={e => setForm(f => ({ ...f, classification: e.target.value }))}
                  >
                    {CLS_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button variant="outline" className="flex-1" onClick={() => setModal({ open: false, editing: null })}>Cancelar</Button>
              <Button className="flex-1 bg-green-600 hover:bg-green-700 text-white gap-2" onClick={save} disabled={saving}>
                <Check size={16} />{saving ? 'Salvando...' : 'Salvar'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Confirmação Delete */}
      {deleteId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
            <h2 className="font-semibold text-gray-900">Excluir categoria?</h2>
            <p className="text-sm text-gray-500">
              Subcategorias e transações vinculadas podem ser afetadas.
            </p>
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setDeleteId(null)}>Cancelar</Button>
              <Button className="flex-1 bg-red-600 hover:bg-red-700 text-white" onClick={() => del(deleteId)}>Excluir</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
