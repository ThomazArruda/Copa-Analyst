// Maps team names to flag emojis
const FLAGS: Record<string, string> = {
  'Argentina': '🇦🇷', 'Brazil': '🇧🇷', 'France': '🇫🇷', 'England': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'Germany': '🇩🇪', 'Spain': '🇪🇸', 'Portugal': '🇵🇹', 'Netherlands': '🇳🇱',
  'Belgium': '🇧🇪', 'Italy': '🇮🇹', 'Uruguay': '🇺🇾', 'Croatia': '🇭🇷',
  'Mexico': '🇲🇽', 'United States': '🇺🇸', 'Canada': '🇨🇦', 'Japan': '🇯🇵',
  'South Korea': '🇰🇷', 'Australia': '🇦🇺', 'Morocco': '🇲🇦', 'Senegal': '🇸🇳',
  'Ghana': '🇬🇭', 'Nigeria': '🇳🇬', 'Cameroon': '🇨🇲', 'South Africa': '🇿🇦',
  'Ecuador': '🇪🇨', 'Colombia': '🇨🇴', 'Chile': '🇨🇱', 'Peru': '🇵🇪',
  'Venezuela': '🇻🇪', 'Bolivia': '🇧🇴', 'Paraguay': '🇵🇾', 'Costa Rica': '🇨🇷',
  'Panama': '🇵🇦', 'Honduras': '🇭🇳', 'El Salvador': '🇸🇻', 'Jamaica': '🇯🇲',
  'Saudi Arabia': '🇸🇦', 'Iran': '🇮🇷', 'Iraq': '🇮🇶', 'Jordan': '🇯🇴',
  'Qatar': '🇶🇦', 'United Arab Emirates': '🇦🇪', 'China PR': '🇨🇳', 'India': '🇮🇳',
  'Indonesia': '🇮🇩', 'Vietnam': '🇻🇳', 'Thailand': '🇹🇭', 'Uzbekistan': '🇺🇿',
  'Switzerland': '🇨🇭', 'Austria': '🇦🇹', 'Denmark': '🇩🇰', 'Sweden': '🇸🇪',
  'Norway': '🇳🇴', 'Poland': '🇵🇱', 'Ukraine': '🇺🇦', 'Serbia': '🇷🇸',
  'Turkey': '🇹🇷', 'Hungary': '🇭🇺', 'Czech Republic': '🇨🇿', 'Slovakia': '🇸🇰',
  'Romania': '🇷🇴', 'Greece': '🇬🇷', 'Scotland': '🏴󠁧󠁢󠁳󠁣󠁴󠁿', 'Wales': '🏴󠁧󠁢󠁷󠁬󠁳󠁿',
  'Ireland': '🇮🇪', 'Albania': '🇦🇱', 'Slovenia': '🇸🇮', 'Israel': '🇮🇱',
  'Algeria': '🇩🇿', 'Tunisia': '🇹🇳', 'Egypt': '🇪🇬', 'Mali': '🇲🇱',
  'Ivory Coast': "🇨🇮", "Côte d'Ivoire": "🇨🇮",
  'New Zealand': '🇳🇿', 'Cuba': '🇨🇺', 'Trinidad and Tobago': '🇹🇹',
}

export function flag(team: string): string {
  return FLAGS[team] ?? '🏳️'
}
