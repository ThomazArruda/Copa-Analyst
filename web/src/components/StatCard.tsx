interface Props {
  label: string
  value: string | number
  sub?: string
  color?: 'blue' | 'green' | 'red' | 'yellow' | 'default'
}

const colors = {
  blue: 'text-[#58a6ff]',
  green: 'text-[#3fb950]',
  red: 'text-[#f85149]',
  yellow: 'text-[#d29922]',
  default: 'text-[#e6edf3]',
}

export default function StatCard({ label, value, sub, color = 'default' }: Props) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-lg px-4 py-3">
      <div className="text-[#8b949e] text-xs mb-1">{label}</div>
      <div className={`text-2xl font-bold ${colors[color]}`}>{value}</div>
      {sub && <div className="text-[#8b949e] text-xs mt-0.5">{sub}</div>}
    </div>
  )
}
