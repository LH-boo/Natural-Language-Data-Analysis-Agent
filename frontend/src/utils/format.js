export function formatDateTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

export function formatLocalNow() {
  const date = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

export function formatDuration(seconds) {
  const value = Number(seconds || 0)
  if (!value) return '0 秒'
  if (value < 1) return `${Math.round(value * 1000)} 毫秒`
  return `${value.toFixed(2)} 秒`
}

export function formatUptime(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0))
  const days = Math.floor(total / 86400)
  const hours = Math.floor((total % 86400) / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const rest = total % 60
  if (days) return `${days}天 ${hours}小时 ${minutes}分钟`
  if (hours) return `${hours}小时 ${minutes}分钟`
  if (minutes) return `${minutes}分钟 ${rest}秒`
  return `${rest}秒`
}

export function formatNumber(value) {
  const number = Number(value || 0)
  if (!Number.isFinite(number)) return '0'
  return number.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}
