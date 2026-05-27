import { useMemo, useState } from 'react'

// Charts — pure SVG chart primitives used by analytics pages.
// LineArea, MultiLine, Bars, DonutMulti

function normalize(points, width, height, padX = 0, padY = 4) {
  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1
  const w = width - padX * 2
  const h = height - padY * 2
  return points.map((v, i) => ({
    x: padX + (i / Math.max(points.length - 1, 1)) * w,
    y: padY + h - ((v - min) / range) * h,
  }))
}

// ---------------------------------------------------------------------------
// LineArea — sparkline with optional filled area
// ---------------------------------------------------------------------------
export function LineArea({
  width = 260, height = 56, points = [],
  accent = 'var(--indigo)', fill = true,
  areaOpacity = 0.18, showAxis = false,
}) {
  if (points.length < 2) return null
  const pts = normalize(points, width, height)
  const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const areaPath = `${linePath} L${pts[pts.length - 1].x.toFixed(1)},${height} L${pts[0].x.toFixed(1)},${height} Z`
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ display: 'block' }}>
      {fill && <path d={areaPath} fill={accent} opacity={areaOpacity} />}
      <path d={linePath} fill="none" stroke={accent} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// MultiLine — multi-series line chart with gridlines
// ---------------------------------------------------------------------------
export function MultiLine({ width = 680, height = 280, series = [], xTickLabels = [], pointLabels = [] }) {
  if (!series.length) return null
  const allPts = series.flatMap(s => Array.isArray(s.points) ? s.points : [])
  if (!allPts.length) return null
  const [hoveredPoint, setHoveredPoint] = useState(null)
  const min = 0
  const maxValue = Math.max(...allPts, 0)
  const gridCount = 4
  const step = Math.max(1, Math.ceil(maxValue / gridCount))
  const yMax = step * gridCount
  const range = yMax - min || 1
  const padL = 28, padR = 12, padT = 12, padB = 34
  const w = width - padL - padR
  const h = height - padT - padB
  const len = series[0].points.length

  const resolvedPointLabels = useMemo(() => {
    if (Array.isArray(pointLabels) && pointLabels.length === len) {
      return pointLabels
    }
    return Array.from({ length: len }, (_, i) => `Point ${i + 1}`)
  }, [pointLabels, len])

  const toSvg = (v, i) => ({
    x: padL + (i / Math.max(len - 1, 1)) * w,
    y: padT + h - ((v - min) / range) * h,
  })

  const grids = Array.from({ length: gridCount + 1 }, (_, i) => {
    const v = min + (range * i) / gridCount
    const y = padT + h - ((v - min) / range) * h
    const label = v >= 1000 ? `${(v / 1000).toFixed(1)}K` : Math.round(v)
    return { y, label }
  })

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block' }}>
      {grids.map((g, i) => (
        <g key={i}>
          <line x1={padL} y1={g.y} x2={padL + w} y2={g.y} stroke="var(--border)" strokeWidth={1} />
          <text x={padL - 4} y={g.y + 4} textAnchor="end" fill="var(--text-3)" fontSize={10} fontFamily="var(--mono)">{g.label}</text>
        </g>
      ))}
      {series.map((s) => {
        const pts = s.points.map((v, i) => toSvg(v, i))
        const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
        return (
          <g key={s.name}>
            <path d={d} fill="none" stroke={s.color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
            {pts.map((p, i) => (
              <g key={`${s.name}-pt-${i}`}>
                <circle
                  cx={p.x.toFixed(1)}
                  cy={p.y.toFixed(1)}
                  r="2.8"
                  fill="white"
                  stroke={s.color}
                  strokeWidth="1.8"
                  opacity="0.95"
                />
                <circle
                  cx={p.x.toFixed(1)}
                  cy={p.y.toFixed(1)}
                  r="8"
                  fill="transparent"
                  onMouseEnter={() => setHoveredPoint({
                    x: p.x,
                    y: p.y,
                    value: s.points[i],
                    seriesName: s.name,
                    color: s.color,
                    label: resolvedPointLabels[i],
                  })}
                  onMouseMove={() => setHoveredPoint({
                    x: p.x,
                    y: p.y,
                    value: s.points[i],
                    seriesName: s.name,
                    color: s.color,
                    label: resolvedPointLabels[i],
                  })}
                  onMouseLeave={() => setHoveredPoint(null)}
                  style={{ cursor: 'pointer' }}
                />
              </g>
            ))}
          </g>
        )
      })}
      {xTickLabels.map((label, i) => {
        if (!label) return null
        const x = padL + (i / Math.max(xTickLabels.length - 1, 1)) * w
        return (
          <g key={`x-${i}`}>
            <line x1={x.toFixed(1)} y1={padT + h} x2={x.toFixed(1)} y2={padT + h + 5} stroke="var(--border)" strokeWidth={1} />
            <text
              x={x.toFixed(1)}
              y={padT + h + 18}
              textAnchor="middle"
              fill="var(--text-3)"
              fontSize={10}
              fontFamily="var(--mono)"
            >
              {label}
            </text>
          </g>
        )
      })}
      {hoveredPoint && (() => {
        const tooltipWidth = 154
        const tooltipHeight = 50
        let tooltipX = hoveredPoint.x + 10
        if (tooltipX + tooltipWidth > padL + w) {
          tooltipX = hoveredPoint.x - tooltipWidth - 10
        }
        tooltipX = Math.max(tooltipX, padL + 2)

        let tooltipY = hoveredPoint.y - tooltipHeight - 10
        if (tooltipY < padT + 2) {
          tooltipY = hoveredPoint.y + 10
        }

        return (
          <g pointerEvents="none">
            <line
              x1={hoveredPoint.x.toFixed(1)}
              y1={padT}
              x2={hoveredPoint.x.toFixed(1)}
              y2={padT + h}
              stroke={hoveredPoint.color}
              strokeOpacity="0.28"
              strokeWidth="1"
              strokeDasharray="4 4"
            />
            <circle
              cx={hoveredPoint.x.toFixed(1)}
              cy={hoveredPoint.y.toFixed(1)}
              r="4.6"
              fill={hoveredPoint.color}
              stroke="white"
              strokeWidth="2"
            />
            <rect
              x={tooltipX.toFixed(1)}
              y={tooltipY.toFixed(1)}
              width={tooltipWidth}
              height={tooltipHeight}
              rx="10"
              fill="rgba(15, 23, 42, 0.94)"
              stroke="rgba(255, 255, 255, 0.18)"
              strokeWidth="1"
            />
            <text
              x={(tooltipX + 10).toFixed(1)}
              y={(tooltipY + 17).toFixed(1)}
              fill="rgba(226, 232, 240, 0.95)"
              fontSize="10"
              fontFamily="var(--mono)"
            >
              {hoveredPoint.label}
            </text>
            <text
              x={(tooltipX + 10).toFixed(1)}
              y={(tooltipY + 34).toFixed(1)}
              fill="white"
              fontSize="12"
              fontWeight="700"
              fontFamily="var(--mono)"
            >
              {`${hoveredPoint.seriesName}: ${Number(hoveredPoint.value || 0).toLocaleString()}`}
            </text>
          </g>
        )
      })()}
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Bars — bar chart with optional x-axis labels
// ---------------------------------------------------------------------------
export function Bars({ width = 520, height = 240, accent = 'var(--blue)', labels = [], values = [] }) {
  if (!values.length) return null
  const padL = 36, padR = 8, padT = 12, padB = 28
  const w = width - padL - padR
  const h = height - padT - padB
  const max = Math.max(...values, 1)
  const n = values.length
  const slotW = w / n
  const barW = Math.max(2, slotW - 4)

  const gridCount = 4
  const grids = Array.from({ length: gridCount + 1 }, (_, i) => {
    const v = Math.round((max * i) / gridCount)
    const y = padT + h - (v / max) * h
    const label = v >= 1000 ? `${(v / 1000).toFixed(1)}K` : v
    return { y, label }
  })

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block' }}>
      {grids.map((g, i) => (
        <g key={i}>
          <line x1={padL} y1={g.y} x2={padL + w} y2={g.y} stroke="var(--border)" strokeWidth={1} />
          <text x={padL - 4} y={g.y + 4} textAnchor="end" fill="var(--text-3)" fontSize={10} fontFamily="var(--mono)">{g.label}</text>
        </g>
      ))}
      {values.map((v, i) => {
        const bh = Math.max(1, (v / max) * h)
        const x = padL + i * slotW + (slotW - barW) / 2
        const y = padT + h - bh
        return <rect key={i} x={x.toFixed(1)} y={y.toFixed(1)} width={barW.toFixed(1)} height={bh.toFixed(1)} rx={2} fill={accent} opacity={0.85} />
      })}
      {labels.map((l, i) => {
        if (!l) return null
        const x = padL + i * slotW + slotW / 2
        return <text key={i} x={x.toFixed(1)} y={padT + h + 16} textAnchor="middle" fill="var(--text-3)" fontSize={10} fontFamily="var(--mono)">{l}</text>
      })}
    </svg>
  )
}

// ---------------------------------------------------------------------------
// DonutMulti — multi-segment donut chart
// ---------------------------------------------------------------------------
export function DonutMulti({ size = 160, strokeWidth = 22, gap = 2, segments = [], centerLabel, centerSub }) {
  const r = (size - strokeWidth) / 2
  const cx = size / 2, cy = size / 2
  const c = 2 * Math.PI * r
  const total = segments.reduce((s, x) => s + x.value, 0) || 1
  let offset = 0
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ display: 'block' }}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--panel-3)" strokeWidth={strokeWidth} />
      {segments.map((s, i) => {
        const len = (s.value / total) * c - gap
        const dasharray = `${Math.max(0, len)} ${c - len}`
        const rotation = (offset / c) * 360
        const node = (
          <circle key={i} cx={cx} cy={cy} r={r} fill="none"
            stroke={s.color} strokeWidth={strokeWidth} strokeLinecap="butt"
            strokeDasharray={dasharray}
            strokeDashoffset={-offset + c * 0.25}
            transform={`rotate(-90 ${cx} ${cy}) rotate(${rotation} ${cx} ${cy})`} />
        )
        offset += (s.value / total) * c
        return node
      })}
      {centerLabel && (
        <text x={cx} y={cy + 8} textAnchor="middle" fill="var(--text)" fontSize="20" fontWeight="700" fontFamily="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif">{centerLabel}</text>
      )}
      {centerSub && (
        <text x={cx} y={cy + 24} textAnchor="middle" fill="var(--text-3)" fontSize="11" fontFamily="var(--mono)">{centerSub}</text>
      )}
    </svg>
  )
}

// ---------------------------------------------------------------------------
// GroupedBars — 2 bars per metric (Current vs Previous) with hover tooltip
// groups = [{ label, color, current, previous }, ...]
// ---------------------------------------------------------------------------
export function GroupedBars({ width = 520, height = 220, groups = [] }) {
  const [tooltip, setTooltip] = useState(null)

  const paddingTop = 16
  const paddingLeft = 36
  const paddingRight = 12
  const paddingBottom = 28   // metric label row only
  const chartH = height - paddingTop - paddingBottom
  const chartW = width - paddingLeft - paddingRight

  const barW = Math.max(8, Math.floor((chartW / groups.length) * 0.32))
  const innerGap = Math.max(3, Math.floor(barW * 0.18))
  const groupW = chartW / groups.length

  const maxVal = Math.max(...groups.flatMap(g => [g.current, g.previous]), 1)

  // Y-axis ticks (4)
  const ticks = [0.25, 0.5, 0.75, 1].map(f => ({
    y: paddingTop + chartH * (1 - f),
    label: (() => { const v = Math.round(maxVal * f); return v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : v })(),
  }))

  const fmt = v => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block', overflow: 'visible' }}
        onMouseLeave={() => setTooltip(null)}>
        {/* Y-axis baseline */}
        <line x1={paddingLeft} y1={paddingTop} x2={paddingLeft} y2={paddingTop + chartH}
          stroke="var(--panel-3)" strokeWidth={1} />
        {/* Grid lines + tick labels */}
        {ticks.map(({ y, label }, i) => (
          <g key={i}>
            <line x1={paddingLeft} y1={y} x2={paddingLeft + chartW} y2={y}
              stroke="var(--panel-3)" strokeWidth={1} strokeDasharray={i === ticks.length - 1 ? '0' : '3 3'} />
            <text x={paddingLeft - 6} y={y + 4} textAnchor="end" fontSize={10}
              fill="var(--text-3)" fontFamily="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif">
              {label}
            </text>
          </g>
        ))}
        {/* Baseline */}
        <line x1={paddingLeft} y1={paddingTop + chartH} x2={paddingLeft + chartW} y2={paddingTop + chartH}
          stroke="var(--panel-3)" strokeWidth={1} />

        {/* Groups */}
        {groups.map((g, gi) => {
          const cx = paddingLeft + gi * groupW + groupW / 2
          const curX = cx - innerGap / 2 - barW
          const prevX = cx + innerGap / 2
          const curH = Math.max(2, (g.current / maxVal) * chartH)
          const prevH = Math.max(g.previous > 0 ? 2 : 0, (g.previous / maxVal) * chartH)
          const labelY = paddingTop + chartH + 18

          return (
            <g key={gi}>
              {/* Current bar */}
              <rect
                x={curX} y={paddingTop + chartH - curH} width={barW} height={curH}
                fill={g.color} rx={3}
                style={{ cursor: 'default', transition: 'opacity 0.15s' }}
                onMouseEnter={e => setTooltip({ x: curX + barW / 2, y: paddingTop + chartH - curH - 8, text: `Current · ${g.label}`, value: fmt(g.current) })}
              />
              {/* Previous bar */}
              <rect
                x={prevX} y={paddingTop + chartH - prevH} width={barW} height={prevH}
                fill={g.color} fillOpacity={0.35} rx={3}
                style={{ cursor: 'default', transition: 'opacity 0.15s' }}
                onMouseEnter={e => setTooltip({ x: prevX + barW / 2, y: paddingTop + chartH - prevH - 8, text: `Previous · ${g.label}`, value: fmt(g.previous) })}
              />
              {/* Metric label */}
              <text x={cx} y={labelY} textAnchor="middle" fontSize={10} fontWeight={500}
                fill="var(--text-3)" fontFamily="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif">
                {g.label}
              </text>
            </g>
          )
        })}

        {/* SVG Tooltip bubble */}
        {tooltip && (() => {
          const tw = 110, th = 38, tx = Math.min(Math.max(tooltip.x - tw / 2, paddingLeft), width - tw - 4)
          const ty = tooltip.y - th - 4
          return (
            <g style={{ pointerEvents: 'none' }}>
              <rect x={tx} y={ty} width={tw} height={th} rx={6}
                fill="var(--panel)" stroke="var(--border)" strokeWidth={1}
                style={{ filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.18))' }} />
              <text x={tx + tw / 2} y={ty + 13} textAnchor="middle" fontSize={9.5} fill="var(--text-3)"
                fontFamily="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif">{tooltip.text}</text>
              <text x={tx + tw / 2} y={ty + 29} textAnchor="middle" fontSize={14} fontWeight={700} fill="var(--text)"
                fontFamily="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif">{tooltip.value}</text>
            </g>
          )
        })()}
      </svg>
    </div>
  )
}
