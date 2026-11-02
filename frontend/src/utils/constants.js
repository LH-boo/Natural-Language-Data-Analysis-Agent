export const CHART_TYPE_LABELS = {
  bar: '柱状图',
  line: '折线图',
  pie: '饼图',
  scatter: '散点图',
  table: '数据表'
}

export const CHART_TYPE_OPTIONS = [
  { label: '柱状图', value: 'bar' },
  { label: '折线图', value: 'line' },
  { label: '饼图', value: 'pie' },
  { label: '散点图', value: 'scatter' }
]

export const AGG_OPTIONS = [
  { label: '求和', value: 'sum' },
  { label: '平均值', value: 'avg' },
  { label: '计数', value: 'count' },
  { label: '最大值', value: 'max' },
  { label: '最小值', value: 'min' }
]

export const AGG_LABELS = {
  sum: '求和',
  avg: '平均值',
  count: '计数',
  max: '最大值',
  min: '最小值'
}

export const DB_TYPE_OPTIONS = [
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgresql' },
  { label: 'SQLite', value: 'sqlite' }
]

export const DB_TYPE_LABELS = {
  mysql: 'MySQL',
  postgresql: 'PostgreSQL',
  postgres: 'PostgreSQL',
  sqlite: 'SQLite'
}

export const SOURCE_TYPE_LABELS = {
  csv: 'CSV 文件',
  sample: '示例数据',
  database: '数据库'
}

export const SUGGESTIONS = [
  '销售额最高的 10 个商品有哪些？',
  '各地区的销售额分布情况如何？',
  '近几个月的销售趋势如何？',
  '不同品类的利润占比是多少？',
  '哪个渠道的客单价最高？',
  '统计各类别的订单数量并排序。'
]

export function chartTypeLabel(type) {
  return CHART_TYPE_LABELS[type] || '数据表'
}

export function dbTypeLabel(type) {
  return DB_TYPE_LABELS[type] || type || '-'
}
