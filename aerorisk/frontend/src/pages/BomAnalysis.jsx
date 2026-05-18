import { useEffect, useRef, useState } from 'react'
import {
  Upload, Cpu, Bug, ShieldAlert, Plane, Package, Trash2, FileCode2,
  AlertOctagon, ChevronRight, Search,
} from 'lucide-react'
import { bomAPI } from '../api/client'
import { RiskBadge } from '../components/RiskBadge'

const SEV = {
  CRITICAL: 'bg-red-500/20 text-red-300 border-red-500/40',
  HIGH:     'bg-orange-500/20 text-orange-300 border-orange-500/40',
  MEDIUM:   'bg-yellow-500/15 text-yellow-300 border-yellow-500/40',
  LOW:      'bg-sky-500/15 text-sky-300 border-sky-500/40',
}
function sevForCvss(c) {
  if (c >= 9.0) return 'CRITICAL'
  if (c >= 7.0) return 'HIGH'
  if (c >= 4.0) return 'MEDIUM'
  return 'LOW'
}
function Tag({ sev, children }) {
  return <span className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold tracking-wider ${SEV[sev] || SEV.LOW}`}>{children || sev}</span>
}

function StatCardSmall({ icon: Icon, value, label, color = 'sky' }) {
  const accents = {
    sky: 'text-sky-300', red: 'text-red-300', orange: 'text-orange-300',
    yellow: 'text-yellow-300', emerald: 'text-emerald-300', slate: 'text-slate-300',
  }
  return (
    <div className="bg-gray-900/70 border border-gray-800 rounded-lg p-3">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-400">
        <Icon size={11} className={accents[color]} />
        {label}
      </div>
      <div className={`text-xl font-bold ${accents[color]} mt-0.5`}>{value}</div>
    </div>
  )
}

export default function BomAnalysis() {
  const [uploads, setUploads] = useState([])
  const [selected, setSelected] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const fileRef = useRef()

  const refresh = () => bomAPI.list().then(r => setUploads(r.data)).catch(console.error)
  useEffect(() => { refresh() }, [])

  const handleUpload = async (file, opts = {}) => {
    if (!file) return
    setUploading(true); setError(null)
    try {
      const { data } = await bomAPI.upload(file, opts)
      await refresh()
      setSelected(data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (e) => {
    e.preventDefault(); setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleUpload(file)
  }

  const onSelect = (id) => bomAPI.get(id).then(r => setSelected(r.data)).catch(console.error)

  const remove = async (id) => {
    if (!confirm('Delete this SBOM analysis?')) return
    await bomAPI.remove(id)
    if (selected?.id === id) setSelected(null)
    refresh()
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
          <FileCode2 size={22} className="text-sky-400" />
          BOM → CVE → Fleet Impact
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Upload a CycloneDX or CSV SBOM. Components are matched to the part catalog, enriched against NVD + KEV + CISA ICS advisories, then rolled up to affected tail numbers.
        </p>
      </div>

      {/* Upload area */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition ${
          dragOver
            ? 'border-sky-500 bg-sky-500/5'
            : 'border-gray-700 bg-gray-900/40 hover:border-gray-600'
        }`}
      >
        <Upload size={28} className="text-slate-500 mx-auto mb-2" />
        <div className="text-sm text-slate-300 font-medium mb-1">
          Drop a CycloneDX JSON or CSV file here
        </div>
        <div className="text-xs text-slate-500 mb-3">
          Accepts .json, .cdx.json, .csv · CSV columns: name, vendor, version, part_number
        </div>
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="text-xs px-4 py-1.5 bg-sky-500/15 hover:bg-sky-500/25 border border-sky-500/30 text-sky-300 rounded transition disabled:opacity-50"
        >
          {uploading ? 'Analyzing…' : 'Choose file'}
        </button>
        <input
          ref={fileRef} type="file" className="hidden"
          accept=".json,.cdx.json,.csv"
          onChange={(e) => handleUpload(e.target.files?.[0])}
        />
        {error && <div className="mt-2 text-xs text-red-400">{error}</div>}
      </div>

      {/* Recent uploads */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-800">
          <h2 className="font-semibold text-slate-100 text-sm">Recent SBOM analyses</h2>
        </div>
        <div className="divide-y divide-gray-800">
          {uploads.length === 0 && (
            <div className="p-6 text-center text-xs text-slate-500 italic">
              No uploads yet. Drop an SBOM above to run analysis.
            </div>
          )}
          {uploads.map(u => {
            const isSel = selected?.id === u.id
            return (
              <button
                key={u.id}
                onClick={() => onSelect(u.id)}
                className={`w-full text-left p-3 hover:bg-gray-800/40 transition flex items-center gap-3 ${isSel ? 'bg-gray-800/30' : ''}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                    <span className="text-sm font-medium text-slate-100 truncate">{u.name}</span>
                    <span className="text-[10px] mono text-slate-500 px-1 py-0.5 bg-gray-800 rounded">{u.source_format}</span>
                    {u.target_platform && (
                      <span className="text-[10px] text-sky-300">{u.target_platform}</span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {u.component_count} components · {u.matched_part_count} matched to catalog · {u.cve_count} CVEs · {u.affected_aircraft_count} aircraft
                  </div>
                </div>
                <RiskBadge score={u.risk_score} />
                <button
                  onClick={(e) => { e.stopPropagation(); remove(u.id) }}
                  className="text-slate-600 hover:text-red-400 p-1"
                  title="Delete"
                ><Trash2 size={12} /></button>
                <ChevronRight size={14} className="text-slate-600 shrink-0" />
              </button>
            )
          })}
        </div>
      </div>

      {/* Detail */}
      {selected && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-5">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-lg font-bold text-slate-100">{selected.name}</h2>
            <span className="text-xs text-slate-500">·</span>
            <span className="text-xs text-slate-400">{new Date(selected.created_at + 'Z').toLocaleString()}</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            <StatCardSmall icon={Package} value={selected.component_count} label="Components" color="slate" />
            <StatCardSmall icon={Cpu} value={selected.matched_part_count} label="Catalog matches" color="sky" />
            <StatCardSmall icon={Bug} value={selected.cve_count} label="CVEs" color="orange" />
            <StatCardSmall icon={ShieldAlert} value={selected.critical_cve_count} label="Critical CVEs" color="red" />
            <StatCardSmall icon={AlertOctagon} value={selected.max_cvss?.toFixed(1) ?? '—'} label="Max CVSS" color="red" />
            <StatCardSmall icon={Plane} value={selected.affected_aircraft_count} label="Aircraft hit" color="orange" />
          </div>

          {selected.affected_tails?.length > 0 && (
            <div className="bg-red-950/30 border border-red-500/30 rounded-lg p-3">
              <div className="text-[10px] uppercase tracking-wider text-red-300 mb-1">Cyber-physical impact</div>
              <div className="text-xs text-slate-200">
                <span className="font-semibold">{selected.affected_tails.length} aircraft</span> in maintenance schedule depend on parts whose firmware/software is named in this SBOM:
                <span className="ml-2 mono text-red-300">{selected.affected_tails.join(', ')}</span>
              </div>
            </div>
          )}

          {/* Components table */}
          <div className="bg-gray-950/50 border border-gray-800 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-gray-800 flex items-center gap-2">
              <Search size={12} className="text-slate-500" />
              <span className="text-xs font-semibold text-slate-200">Component breakdown</span>
              <span className="text-[11px] text-slate-500 ml-auto">{selected.components?.length || 0} rows</span>
            </div>
            <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="bg-gray-900/80 sticky top-0">
                  <tr className="text-left text-slate-400">
                    <th className="px-3 py-2 font-medium">Component</th>
                    <th className="px-3 py-2 font-medium">Vendor</th>
                    <th className="px-3 py-2 font-medium">Catalog match</th>
                    <th className="px-3 py-2 font-medium text-right">CVEs</th>
                    <th className="px-3 py-2 font-medium text-right">Max CVSS</th>
                    <th className="px-3 py-2 font-medium">Top CVE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {selected.components?.map(c => {
                    const top = c.cves?.slice().sort((a, b) => b.cvss - a.cvss)[0]
                    return (
                      <tr key={c.id} className={c.cve_count > 0 ? 'bg-red-950/10' : ''}>
                        <td className="px-3 py-2">
                          <div className="font-medium text-slate-100 truncate max-w-[200px]" title={c.name}>{c.name}</div>
                          {c.version && <div className="text-[10px] text-slate-500 mono">v{c.version}</div>}
                        </td>
                        <td className="px-3 py-2 text-slate-300">{c.vendor || '—'}</td>
                        <td className="px-3 py-2">
                          {c.matched_part_number ? (
                            <div>
                              <span className="mono text-sky-300">{c.matched_part_number}</span>
                              <div className="text-[10px] text-slate-500">{c.matched_supplier_name} · {Math.round(c.match_confidence)}% via {c.matched_on}</div>
                            </div>
                          ) : c.matched_supplier_name ? (
                            <div>
                              <span className="text-slate-300">{c.matched_supplier_name}</span>
                              <div className="text-[10px] text-slate-500">supplier only · {Math.round(c.match_confidence)}%</div>
                            </div>
                          ) : (
                            <span className="text-slate-600 italic">no match</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-right">
                          {c.cve_count > 0 ? (
                            <div>
                              <span className="text-red-300 font-semibold">{c.cve_count}</span>
                              {c.kev_listed && <Tag sev="HIGH">KEV</Tag>}
                            </div>
                          ) : (
                            <span className="text-slate-600">0</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-right">
                          {c.max_cvss > 0 ? (
                            <Tag sev={sevForCvss(c.max_cvss)}>{c.max_cvss.toFixed(1)}</Tag>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          {top ? (
                            <div className="max-w-[280px]">
                              <span className="mono text-[10px] text-sky-300">{top.cve_id}</span>
                              <div className="text-[10px] text-slate-400 truncate" title={top.description}>{top.description}</div>
                            </div>
                          ) : (
                            <span className="text-slate-600 italic">none</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
