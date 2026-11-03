/** 展示层用到的中英对照与小工具 */

export const GENRE_CN = {
  Action: '动作',
  Adventure: '冒险',
  Animation: '动画',
  Children: '儿童',
  Comedy: '喜剧',
  Crime: '犯罪',
  Documentary: '纪录',
  Drama: '剧情',
  Fantasy: '奇幻',
  'Film-Noir': '黑色电影',
  Horror: '恐怖',
  IMAX: 'IMAX',
  Musical: '歌舞',
  Mystery: '悬疑',
  Romance: '爱情',
  'Sci-Fi': '科幻',
  Thriller: '惊悚',
  War: '战争',
  Western: '西部',
  '(no genres listed)': '未分类',
}

export function genreCN(g) {
  return GENRE_CN[g] || g
}

export const FEATURE_CN = {
  bpr: 'BPR 召回分',
  item_trend: '条目热度趋势',
  user_last_activity: '用户最近活跃',
  item_recency: '条目新鲜度',
  user_activity: '用户活跃度',
  item_mean: '条目平均分',
  genre_affinity: '类型亲和度',
  pop_log: '热度（对数）',
  item_bayes: '贝叶斯均分',
}

/** MovieLens 的标题形如 "Toy Story (1995)"，把年份拆出来显示 */
export function splitTitle(title) {
  if (!title) return { name: '', year: null }
  const m = title.match(/^(.*?)\s*\((\d{4})\)\s*$/)
  if (m) return { name: m[1], year: Number(m[2]) }
  return { name: title, year: null }
}

/** 0.88938 → 0.8894 */
export function fixed(v, n = 4) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—'
  return Number(v).toFixed(n)
}

/** 0.88938 相对 0.73634 → +20.8% */
export function pct(v, base) {
  if (!base) return '—'
  const d = ((v - base) / base) * 100
  return `${d >= 0 ? '+' : ''}${d.toFixed(1)}%`
}

export function ms(v) {
  if (v === null || v === undefined) return '—'
  if (v < 0.1) return '<0.1 ms'
  if (v < 10) return `${v.toFixed(2)} ms`
  if (v < 1000) return `${v.toFixed(1)} ms`
  return `${(v / 1000).toFixed(2)} s`
}

export function thousands(v) {
  if (v === null || v === undefined) return '—'
  return Number(v).toLocaleString('en-US')
}

/** 推荐理由：只用真实字段（排名 / 分数 / 类型），不编造理由 */
export function buildReason(item, { maxScore, candidates, genres }) {
  const bits = []
  if (item.score !== null && maxScore !== null) {
    const ratio = maxScore > 0 ? item.score / maxScore : 0
    if (item.rank === 1) bits.push('BPR 分数为该用户本批最高')
    else if (ratio >= 0.98) bits.push('BPR 分数与 Top1 持平')
    else if (ratio >= 0.75) bits.push('BPR 分数处于 Top10 高段')
    else if (item.score >= 0) bits.push('BPR 给出弱正向偏好')
    else bits.push('BPR 分数偏低，靠排序特征的统计信号托起')
  }
  if (item.genreAffinity !== null && item.genreAffinity !== undefined) {
    bits.push(`类型画像余弦 ${Number(item.genreAffinity).toFixed(3)}`)
  } else if (genres.length) {
    bits.push(`类型 ${genres.slice(0, 2).map(genreCN).join('/')}`)
  }
  if (candidates) bits.push(`候选集 ${candidates} 部中排第 ${item.rank}`)
  return bits.join('；')
}
