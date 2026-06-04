interface Props {
  mandante: string
  visitante: string
  probM: number
  probE: number
  probV: number
}

export default function ProbBar({ mandante, visitante, probM, probE, probV }: Props) {
  const pM = Math.round(probM * 100)
  const pE = Math.round(probE * 100)
  const pV = Math.round(probV * 100)

  return (
    <div className="space-y-2.5">
      <div className="flex justify-between text-xs font-medium px-0.5">
        <span className="text-[#58a6ff] tabular-nums font-bold text-sm">{pM}%</span>
        <span className="text-[#8b949e] tabular-nums">{pE}%</span>
        <span className="text-[#f47067] tabular-nums font-bold text-sm">{pV}%</span>
      </div>
      <div className="flex rounded-full overflow-hidden h-3 gap-px">
        <div
          className="bg-gradient-to-r from-[#1f6feb] to-[#58a6ff] transition-all rounded-l-full"
          style={{ width: `${pM}%` }}
          title={`${mandante} ${pM}%`}
        />
        <div
          className="bg-[#30363d] transition-all"
          style={{ width: `${pE}%` }}
          title={`Empate ${pE}%`}
        />
        <div
          className="bg-gradient-to-r from-[#da3633] to-[#f47067] transition-all rounded-r-full"
          style={{ width: `${pV}%` }}
          title={`${visitante} ${pV}%`}
        />
      </div>
      <div className="flex justify-between text-xs text-[#8b949e] font-medium px-0.5">
        <span>{mandante}</span>
        <span>Empate</span>
        <span>{visitante}</span>
      </div>
    </div>
  )
}
