// Mapeia nomes de seleções para códigos ISO 3166-1 alpha-2 (flagcdn.com)
const FLAG_CODES: Record<string, string> = {
  // América do Sul
  'Argentina': 'ar', 'Brazil': 'br', 'Uruguay': 'uy', 'Colombia': 'co',
  'Ecuador': 'ec', 'Chile': 'cl', 'Peru': 'pe', 'Venezuela': 've',
  'Bolivia': 'bo', 'Paraguay': 'py',
  // América do Norte / Central / Caribe
  'United States': 'us', 'Mexico': 'mx', 'Canada': 'ca',
  'Costa Rica': 'cr', 'Panama': 'pa', 'Honduras': 'hn',
  'El Salvador': 'sv', 'Jamaica': 'jm', 'Cuba': 'cu',
  'Trinidad and Tobago': 'tt', 'Guatemala': 'gt', 'Curacao': 'cw',
  'Haiti': 'ht',
  // Europa
  'France': 'fr', 'Germany': 'de', 'Spain': 'es', 'Portugal': 'pt',
  'Netherlands': 'nl', 'Belgium': 'be', 'Italy': 'it', 'Croatia': 'hr',
  'Switzerland': 'ch', 'Austria': 'at', 'Denmark': 'dk', 'Sweden': 'se',
  'Norway': 'no', 'Poland': 'pl', 'Ukraine': 'ua', 'Serbia': 'rs',
  'Turkey': 'tr', 'Hungary': 'hu', 'Czech Republic': 'cz', 'Slovakia': 'sk',
  'Romania': 'ro', 'Greece': 'gr', 'Ireland': 'ie', 'Albania': 'al',
  'Slovenia': 'si', 'Israel': 'il', 'England': 'gb', 'Scotland': 'gb',
  'Wales': 'gb', 'Bosnia & Herzegovina': 'ba', 'Bosnia and Herzegovina': 'ba',
  // África
  'Morocco': 'ma', 'Senegal': 'sn', 'Ghana': 'gh', 'Nigeria': 'ng',
  'Cameroon': 'cm', 'South Africa': 'za', 'Egypt': 'eg', 'Tunisia': 'tn',
  'Algeria': 'dz', 'Mali': 'ml', "Ivory Coast": 'ci', "Côte d'Ivoire": 'ci',
  'DR Congo': 'cd', 'Cape Verde': 'cv',
  // Ásia / Oriente Médio
  'Japan': 'jp', 'South Korea': 'kr', 'Australia': 'au',
  'Saudi Arabia': 'sa', 'Iran': 'ir', 'Iraq': 'iq', 'Jordan': 'jo',
  'Qatar': 'qa', 'United Arab Emirates': 'ae', 'China PR': 'cn',
  'Indonesia': 'id', 'Vietnam': 'vn', 'Uzbekistan': 'uz',
  'New Zealand': 'nz', 'India': 'in', 'Thailand': 'th',
}

/** Retorna URL de bandeira (flagcdn.com 40px) ou string vazia se não mapeado. */
export function flagUrl(team: string): string {
  const code = FLAG_CODES[team]
  if (!code) return ''
  return `https://flagcdn.com/w40/${code}.png`
}

/** Componente img inline — use em JSX onde quiser exibir a bandeira. */
export function flag(team: string): string {
  // mantido por compatibilidade; retorna o código ISO ou '?'
  return FLAG_CODES[team] ?? ''
}
