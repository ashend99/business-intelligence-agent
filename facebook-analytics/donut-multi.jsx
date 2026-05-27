// Multi-segment donut for engagement breakdown and demographics gender split.

function DonutMulti({ size = 160, strokeWidth = 22, gap = 2, segments, centerLabel, centerSub }) {
  // segments: [{ value, color, name }]
  const r = (size - strokeWidth) / 2;
  const cx = size / 2, cy = size / 2;
  const c = 2 * Math.PI * r;
  const total = segments.reduce((s, x) => s + x.value, 0);
  let offset = 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--panel-3)" strokeWidth={strokeWidth} />
      {segments.map((s, i) => {
        const len = (s.value / total) * c - gap;
        const dasharray = `${Math.max(0, len)} ${c - len}`;
        const node = (
          <circle key={i} cx={cx} cy={cy} r={r} fill="none"
            stroke={s.color} strokeWidth={strokeWidth} strokeLinecap="butt"
            strokeDasharray={dasharray} strokeDashoffset={-offset + c * 0.25}
            transform={`rotate(-90 ${cx} ${cy}) rotate(${(offset / c) * 360} ${cx} ${cy})`} />
        );
        offset += (s.value / total) * c;
        return node;
      })}
      {centerLabel && <text x={cx} y={cy + 2} textAnchor="middle" fill="var(--text)" fontSize="22" fontWeight="600">{centerLabel}</text>}
      {centerSub && <text x={cx} y={cy + 22} textAnchor="middle" fill="var(--text-3)" fontSize="11" fontFamily="var(--mono)">{centerSub}</text>}
    </svg>
  );
}

window.DonutMulti = DonutMulti;
