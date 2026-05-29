// Facebook Analytics — dark-mode replica of SocialHub layout, plugged into Nexus design system.

const NAV = [
  { id: 'overview', icon: 'Home', label: 'Overview' },
  { id: 'analytics', icon: 'Analytics', label: 'Analytics' },
  { id: 'inbox', icon: 'Chatbot', label: 'Inbox', badge: 12 },
  { id: 'content', icon: 'Doc', label: 'Content' },
  { id: 'posts', icon: 'Send', label: 'Posts' },
  { id: 'calendar', icon: 'Calendar', label: 'Calendar' },
  { id: 'ads', icon: 'Flash', label: 'Ads' },
  { id: 'audience', icon: 'Team', label: 'Audience' },
  { id: 'reports', icon: 'Reports', label: 'Reports' },
  { id: 'competitors', icon: 'Star', label: 'Competitors' },
  { id: 'settings', icon: 'Settings', label: 'Settings' },
  { id: 'integrations', icon: 'Folder', label: 'Integrations' },
];

const PLATFORMS = [
  { id: 'fb', icon: 'Facebook', label: 'Facebook', tone: 'fb' },
  { id: 'ig', icon: 'Instagram', label: 'Instagram', tone: 'ig' },
  { id: 'li', icon: 'LinkedIn', label: 'LinkedIn', tone: 'li' },
  { id: 'yt', icon: 'Eye', label: 'YouTube', tone: 'yt' },
  { id: 'tk', icon: 'Flash', label: 'TikTok', tone: 'tk' },
];

function Sidebar() {
  return (
    <aside style={{ width: 240, flex: '0 0 240px', borderRight: '1px solid var(--border)', background: 'var(--bg-2)', display: 'flex', flexDirection: 'column' }}>
      {/* Logo */}
      <div style={{ padding: '18px 16px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div className="logo-mark">
          <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2.5 13.5 V2.5" /><path d="M2.5 13.5 H13.5" /><path d="M5 11 V7" /><path d="M8 11 V5" /><path d="M11 11 V8" />
          </svg>
        </div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.01em' }}>SocialHub</div>
          <div style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: 0.6 }}>Aurora Labs</div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: '4px 8px', display: 'flex', flexDirection: 'column', gap: 2, flex: 1, overflowY: 'auto' }}>
        {NAV.map(n => {
          const Icon = Icons[n.icon];
          const active = n.id === 'analytics';
          return (
            <div key={n.id} className={`nav-item ${active ? 'active' : ''}`}>
              <Icon size={16} />
              <span style={{ flex: 1 }}>{n.label}</span>
              {n.badge && <span className="badge">{n.badge}</span>}
            </div>
          );
        })}
      </nav>

      {/* Connected platforms */}
      <div style={{ borderTop: '1px solid var(--border)', padding: '12px 8px' }}>
        <div className="label" style={{ padding: '4px 12px', marginBottom: 4 }}>Connected platforms</div>
        {PLATFORMS.map(p => {
          const Icon = Icons[p.icon];
          return (
            <div key={p.id} className={`connected-row ${p.id === 'fb' ? 'active' : ''}`}>
              <span className={`platform-tile ${p.tone}`} style={{ width: 24, height: 24, flexBasis: 24 }}><Icon size={14} /></span>
              <span>{p.label}</span>
            </div>
          );
        })}
      </div>

      <div style={{ borderTop: '1px solid var(--border)', padding: 12, display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
        <Icons.ChevronLeft size={14} />
        <span style={{ fontSize: 12, color: 'var(--text-3)' }}>Collapse</span>
      </div>
    </aside>
  );
}

function TopBar() {
  return (
    <header style={{ padding: '20px 24px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', borderBottom: '1px solid var(--border)', background: 'var(--bg)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <button className="btn ghost" style={{ padding: 6 }}><Icons.Dots size={16} /></button>
        <div className="platform-tile fb"><Icons.Facebook size={20} /></div>
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.01em' }}>Facebook Analytics</div>
          <div style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 2 }}>Overview of your Facebook Page performance</div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button className="input"><Icons.Calendar size={13} /><span>May 12 — Jun 10, 2024</span><Icons.ChevronDown size={11} /></button>
          <button className="input"><span style={{ color: 'var(--text-3)' }}>Compare to:</span><span>Apr 12 — May 11, 2024</span><Icons.ChevronDown size={11} /></button>
          <button className="btn"><Icons.Download size={13} />Export</button>
          <button className="btn ghost" style={{ padding: 8, position: 'relative' }}>
            <Icons.Bell size={16} />
            <span style={{ position: 'absolute', top: 4, right: 4, background: 'var(--coral)', color: 'white', fontSize: 9, fontWeight: 700, borderRadius: 999, minWidth: 14, height: 14, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '0 4px' }}>8</span>
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 10px 4px 4px', border: '1px solid var(--border)', borderRadius: 999 }}>
            <div className="avatar lg" style={{ width: 30, height: 30, flexBasis: 30, background: 'var(--indigo)', borderColor: 'var(--indigo-2)', color: 'white' }}>JD</div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.2 }}>John Doe</div>
              <div style={{ fontSize: 10, color: 'var(--text-3)' }}>Admin</div>
            </div>
            <Icons.ChevronDown size={11} />
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: 'var(--text-3)' }}>Facebook Page</span>
          <button className="input">
            <span style={{ width: 18, height: 18, borderRadius: 4, background: 'var(--fb)', color: 'white', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700 }}>TN</span>
            <span>TechNova Solutions</span>
            <Icons.ChevronDown size={11} />
          </button>
        </div>
      </div>
    </header>
  );
}

function KPICard({ label, value, delta, color, spark }) {
  return (
    <div className="panel" style={{ padding: 18, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 13, color: 'var(--text-2)', fontWeight: 500 }}>{label}</span>
        <Icons.Eye size={13} />
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 8 }}>
        <span style={{ fontSize: 26, fontWeight: 700, letterSpacing: '-0.02em' }}>{value}</span>
        <span className="mono" style={{ fontSize: 11, color: delta.startsWith('−') || delta.startsWith('-') ? 'var(--coral)' : 'var(--teal)' }}>
          {delta.startsWith('−') || delta.startsWith('-') ? '↓' : '↑'} {delta.replace(/^[−-]/, '')}
        </span>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>vs Apr 12 — May 11</div>
      <div style={{ marginTop: 12, height: 56 }}>
        <LineArea width={260} height={56} points={spark} accent={color} fill showAxis={false} areaOpacity={0.22} />
      </div>
    </div>
  );
}

function Section({ title, subtitle, right, children, style }) {
  return (
    <div className="panel" style={{ padding: 22, display: 'flex', flexDirection: 'column', ...style }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 600 }}>{title}</div>
          {subtitle && <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>{subtitle}</div>}
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}

function GranularitySelect({ value }) {
  return (
    <button className="input" style={{ padding: '6px 10px', fontSize: 12 }}>
      <span>{value}</span>
      <Icons.ChevronDown size={11} />
    </button>
  );
}

function SocialPage() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <TopBar />

        <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* KPI row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 14 }}>
            <KPICard label="Reach" value="128.4K" delta="18.6%" color="#4A8CFF" spark={[60,62,58,65,72,68,76,80,72,84,88,82,92,98]} />
            <KPICard label="Impressions" value="256.7K" delta="24.5%" color="#9B7BFF" spark={[40,44,42,50,56,54,62,60,72,76,82,80,92,108]} />
            <KPICard label="Engagement" value="15.7K" delta="21.4%" color="#2EC27E" spark={[50,52,48,56,62,58,68,72,68,78,82,76,88,98]} />
            <KPICard label="Engagement Rate" value="12.24%" delta="8.7%" color="#FF8A4C" spark={[70,72,74,76,78,80,82,84,82,86,88,90,92,96]} />
            <KPICard label="Page Likes" value="2.4K" delta="15.3%" color="#4A8CFF" spark={[10,14,18,22,28,34,42,48,56,62,70,78,86,94]} />
            <KPICard label="Video Views" value="91.3K" delta="30.8%" color="#E163C9" spark={[20,26,22,32,28,42,38,52,58,68,74,82,92,108]} />
          </div>

          {/* Middle row — Performance, Demographics, Top Countries */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.6fr 1fr', gap: 14 }}>
            {/* Performance */}
            <Section
              title="Performance Overview"
              right={<GranularitySelect value="Daily" />}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginBottom: 10 }}>
                {[
                  ['Reach', '#4A8CFF'],
                  ['Impressions', '#9B7BFF'],
                  ['Engagement', '#2EC27E'],
                ].map(([n, c]) => (
                  <span key={n} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-2)' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: c }} />{n}
                  </span>
                ))}
              </div>
              <div style={{ height: 280 }}>
                <MultiLine width={680} height={280} series={[
                  { name: 'Reach', color: '#4A8CFF', points: [10,14,12,16,15,19,18,22,21,24,22,26,30,32,28,34,33,30,36,38,33,38,40,36,42,44,40,45,42,46] },
                  { name: 'Impressions', color: '#9B7BFF', points: [18,22,20,24,23,28,27,32,30,35,33,38,42,46,40,48,46,42,52,55,50,55,58,52,60,64,58,68,64,62] },
                  { name: 'Engagement', color: '#2EC27E', points: [4,6,5,6,7,8,7,9,10,11,9,11,13,14,12,15,14,12,16,17,14,17,18,16,19,21,18,22,20,21] },
                ]} />
              </div>
            </Section>

            {/* Audience Demographics */}
            <Section title="Audience Demographics" subtitle="Facebook Page followers">
              <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
                {/* Women block */}
                <div style={{ textAlign: 'center', flex: 1 }}>
                  <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--blue)' }}>54.3%</div>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--blue)' }} />Women
                  </div>
                </div>
                <DonutMulti size={150} strokeWidth={22} segments={[
                  { value: 54.3, color: 'var(--blue)' },
                  { value: 45.7, color: 'var(--purple)' },
                ]} />
                <div style={{ textAlign: 'center', flex: 1 }}>
                  <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--purple)' }}>45.7%</div>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--purple)' }} />Men
                  </div>
                </div>
              </div>

              <hr className="divider" style={{ margin: '16px 0' }} />

              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 10 }}>Age & Gender</div>
              <AgeGenderBars />
            </Section>

            {/* Top countries */}
            <Section title="Top Countries">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {[
                  ['United States', 28.3, 100],
                  ['India', 18.7, 66],
                  ['Philippines', 7.9, 28],
                  ['Brazil', 5.4, 19],
                  ['United Kingdom', 4.3, 15],
                ].map(([country, pct, bar]) => (
                  <div key={country}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                      <span style={{ fontSize: 13 }}>{country}</span>
                      <span className="mono" style={{ fontSize: 12, color: 'var(--text-2)' }}>{pct}%</span>
                    </div>
                    <div style={{ height: 4, background: 'var(--panel-3)', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ width: `${bar}%`, height: '100%', background: 'var(--blue)' }} />
                    </div>
                  </div>
                ))}
              </div>
              <button className="btn" style={{ justifyContent: 'center', marginTop: 16, background: 'var(--panel-2)' }}>See all</button>
            </Section>
          </div>

          {/* Bottom row — Top posts, breakdown, over time */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1.4fr', gap: 14 }}>
            <Section
              title="Top Performing Posts"
              right={<button className="btn sm">View all</button>}
              style={{ padding: 0 }}
            >
              <table className="dense">
                <thead>
                  <tr><th>Post</th><th>Type</th><th>Reach</th><th>Engagement</th><th>Eng. Rate</th></tr>
                </thead>
                <tbody>
                  {[
                    { title: '5 AI Tools That Will Boost...', date: 'May 30, 2024 10:30 AM', type: 'Image', reach: '34.2K', eng: '4.2K', rate: '12.3%', bar: 92, swatch: '#FFB28A' },
                    { title: 'How to Grow Your Page...', date: 'May 28, 2024 09:15 AM', type: 'Image', reach: '28.6K', eng: '3.6K', rate: '12.6%', bar: 78, swatch: '#A1C9FF' },
                    { title: 'We Hit 10K Followers! 🎉', date: 'May 26, 2024 08:00 PM', type: 'Text', reach: '22.1K', eng: '2.8K', rate: '12.7%', bar: 62, swatch: '#FFE08A' },
                    { title: 'New Blog Post: The Future...', date: 'May 24, 2024 11:45 AM', type: 'Link', reach: '18.7K', eng: '2.2K', rate: '11.8%', bar: 51, swatch: '#B8FFE5' },
                    { title: 'Behind the Scenes of Our...', date: 'May 22, 2024 07:30 PM', type: 'Image', reach: '16.3K', eng: '1.9K', rate: '11.7%', bar: 44, swatch: '#D4B8FF' },
                  ].map((r, i) => (
                    <tr key={i}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                          <div style={{ width: 36, height: 36, borderRadius: 6, background: r.swatch, opacity: 0.85, flex: '0 0 36px' }} />
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 200 }}>{r.title}</div>
                            <div style={{ fontSize: 11, color: 'var(--text-3)' }}>{r.date}</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        {r.type === 'Image' && <Icons.Instagram size={15} />}
                        {r.type === 'Text' && <span style={{ fontFamily: 'var(--mono)', fontSize: 14, color: 'var(--text-2)' }}>T</span>}
                        {r.type === 'Link' && <Icons.Doc size={15} />}
                      </td>
                      <td className="mono">{r.reach}</td>
                      <td>
                        <div className="mono" style={{ fontSize: 12 }}>{r.eng}</div>
                        <div style={{ height: 3, width: 70, background: 'var(--panel-3)', borderRadius: 2, marginTop: 4, overflow: 'hidden' }}>
                          <div style={{ width: `${r.bar}%`, height: '100%', background: 'var(--blue)' }} />
                        </div>
                      </td>
                      <td className="mono" style={{ fontWeight: 600, color: 'var(--teal)' }}>{r.rate}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Section>

            <Section title="Engagement Breakdown">
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <DonutMulti
                  size={170}
                  strokeWidth={24}
                  centerLabel="0"
                  centerSub="Total"
                  segments={[
                    { value: 53.5, color: '#4A8CFF' },
                    { value: 13.4, color: '#2EC27E' },
                    { value: 11.5, color: '#9B7BFF' },
                    { value: 21.6, color: '#FF8A4C' },
                  ]}
                />
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {[
                    ['Reactions', '8.4K (53.5%)', '#4A8CFF'],
                    ['Comments', '2.1K (13.4%)', '#2EC27E'],
                    ['Shares', '1.8K (11.5%)', '#9B7BFF'],
                    ['Clicks', '3.4K (21.6%)', '#FF8A4C'],
                  ].map(([k, v, c]) => (
                    <div key={k}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ width: 9, height: 9, borderRadius: '50%', background: c }} />
                        <span style={{ fontSize: 13, fontWeight: 500 }}>{k}</span>
                      </div>
                      <div className="mono" style={{ fontSize: 11, color: 'var(--text-3)', marginLeft: 17, marginTop: 2 }}>{v}</div>
                    </div>
                  ))}
                </div>
              </div>
            </Section>

            <Section
              title="Engagement Over Time"
              right={<GranularitySelect value="Daily" />}
            >
              <div style={{ height: 240 }}>
                <Bars width={520} height={240} accent="#4A8CFF" labels={['May 12','','','','May 17','','','','','May 22','','','','','May 27','','','','','Jun 1','','','','','Jun 6','','','','','Jun 10']}
                  values={[600,820,1040,720,920,1180,1320,1080,1260,1480,1240,1380,1620,1140,1520,1280,1680,1440,1360,1180,1620,1740,1480,1880,1620,1380,1560,1820,1480,1680]} />
              </div>
            </Section>
          </div>

          {/* Key insights */}
          <Section title="Key Insights" subtitle="Generated by Nexus agent · refreshed 2m ago">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
              {[
                { icon: 'Analytics', tone: 'rgba(46,194,126,0.16)', color: 'var(--green)',
                  title: 'Reach is up 18.6%', body: 'You reached 128.4K more people compared to the previous period.' },
                { icon: 'Star', tone: 'rgba(155,123,255,0.16)', color: 'var(--purple)',
                  title: 'Engagement Rate improved', body: 'Your engagement rate increased by 8.7% compared to last period.' },
                { icon: 'Eye', tone: 'rgba(74,140,255,0.16)', color: 'var(--blue)',
                  title: 'Video performance is great', body: 'Video views increased by 30.8% and driving more engagement.' },
                { icon: 'Clock', tone: 'rgba(255,138,76,0.16)', color: 'var(--orange)',
                  title: 'Best posting time', body: 'Posts between 6PM — 9PM get the highest engagement.' },
              ].map((k, i) => {
                const Icon = Icons[k.icon];
                return (
                  <div key={i} className="panel-2" style={{ padding: 14, display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ width: 38, height: 38, borderRadius: 8, background: k.tone, color: k.color, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 38px' }}>
                      <Icon size={18} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{k.title}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-2)', marginTop: 4, lineHeight: 1.45 }}>{k.body}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Section>
        </div>
      </main>
    </div>
  );
}

function AgeGenderBars() {
  // Each bucket: women%, men%
  const buckets = [
    ['13-17',  6,  4],
    ['18-24', 14, 10],
    ['25-34', 30, 22],
    ['35-44', 22, 18],
    ['45-54', 11,  8],
    ['55-64',  6,  5],
    ['65+',    4,  3],
  ];
  const max = 32;
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, height: 110 }}>
        {/* y-axis */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', paddingBottom: 18 }}>
          {['30%','20%','10%','0%'].map(y => (
            <span key={y} className="mono" style={{ fontSize: 10, color: 'var(--text-3)' }}>{y}</span>
          ))}
        </div>
        {buckets.map(([label, w, m]) => (
          <div key={label} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%' }}>
            <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end', gap: 3 }}>
              <div style={{ width: 10, height: `${(w/max) * 100}%`, background: 'var(--blue)', borderRadius: '3px 3px 0 0' }} />
              <div style={{ width: 10, height: `${(m/max) * 100}%`, background: 'var(--purple)', borderRadius: '3px 3px 0 0' }} />
            </div>
            <span className="mono" style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 6 }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<SocialPage />);
