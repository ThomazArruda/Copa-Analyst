import clsx from 'clsx'

interface Props {
  label: string
}

function tagStyle(label: string) {
  const l = label.toLowerCase()
  if (l.includes('favorito')) return 'bg-[#388bfd1a] text-[#58a6ff] border-[#388bfd30]'
  if (l.includes('goleada')) return 'bg-[#f851491a] text-[#f85149] border-[#f8514930]'
  if (l.includes('fechado') || l.includes('pouco')) return 'bg-[#3fb9501a] text-[#3fb950] border-[#3fb95030]'
  if (l.includes('equilibrado') || l.includes('empate')) return 'bg-[#d299221a] text-[#d29922] border-[#d2992230]'
  return 'bg-[#21262d] text-[#8b949e] border-[#30363d]'
}

export default function Tag({ label }: Props) {
  return (
    <span className={clsx(
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border',
      tagStyle(label)
    )}>
      {label}
    </span>
  )
}
