// Icon set — exact copy of nexus/icons.jsx ported to ES module export

const NxIcon = ({ d, size = 16, fill, strokeWidth = 1.6 }) => (
  <svg viewBox="0 0 16 16" width={size} height={size} fill={fill || 'none'} stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
    {Array.isArray(d) ? d.map((p, i) => <path key={i} d={p} />) : <path d={d} />}
  </svg>
)

export const Icons = {
  Nexus: ({ size = 18 }) => (
    <svg viewBox="0 0 20 20" width={size} height={size} fill="none">
      <path d="M3 3 L17 3 L17 11 L11 17 L3 17 Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M7 7 L13 7 M7 11 L11 11" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="10" cy="10" r="2.5" fill="currentColor" opacity="0.4" />
    </svg>
  ),
  Home:        (p) => <NxIcon {...p} d={["M2.5 7 L8 2.5 L13.5 7 V13.5 H2.5 Z","M6 13.5 V9 H10 V13.5"]} />,
  Analytics:   (p) => <NxIcon {...p} d={["M2.5 13.5 V2.5","M2.5 13.5 H13.5","M5 11 V7","M8 11 V5","M11 11 V8"]} />,
  Reports:     (p) => <NxIcon {...p} d={["M3.5 2 H10 L12.5 4.5 V14 H3.5 Z","M9.5 2 V5 H12.5","M5.5 8 H10.5","M5.5 11 H10.5"]} />,
  Chatbot:     (p) => <NxIcon {...p} d={["M2.5 4 H13.5 V11 H8 L5 13.5 V11 H2.5 Z","M5.5 7.5 H5.6","M8 7.5 H8.1","M10.5 7.5 H10.6"]} />,
  Sales:       (p) => <NxIcon {...p} d={["M2.5 13 L6 9 L9 11 L13.5 5","M10 5 H13.5 V8.5"]} />,
  Team:        (p) => <NxIcon {...p} d={["M11 13.5 V12 a2 2 0 0 0 -2 -2 H5 a2 2 0 0 0 -2 2 V13.5","M7 8 a2.5 2.5 0 1 0 0 -5 a2.5 2.5 0 0 0 0 5","M13.5 13.5 V12 a2 2 0 0 0 -1.5 -1.9","M11 8 a2 2 0 0 0 0 -4"]} />,
  Social:      (p) => <NxIcon {...p} d={["M4 4.5 a1.5 1.5 0 1 0 0 3 a1.5 1.5 0 0 0 0 -3","M12 2.5 a1.5 1.5 0 1 0 0 3 a1.5 1.5 0 0 0 0 -3","M12 10.5 a1.5 1.5 0 1 0 0 3 a1.5 1.5 0 0 0 0 -3","M5.5 5.5 L10.5 3.5","M5.5 6.5 L10.5 11.5"]} />,
  Settings:    (p) => <NxIcon {...p} d={["M8 10.5 a2.5 2.5 0 1 0 0 -5 a2.5 2.5 0 0 0 0 5","M8 1.5 V3 M8 13 V14.5 M14.5 8 H13 M3 8 H1.5 M12.6 3.4 L11.5 4.5 M4.5 11.5 L3.4 12.6 M12.6 12.6 L11.5 11.5 M4.5 4.5 L3.4 3.4"]} />,
  Search:      (p) => <NxIcon {...p} d={["M7 12 a5 5 0 1 0 0 -10 a5 5 0 0 0 0 10","M10.5 10.5 L13.5 13.5"]} />,
  Bell:        (p) => <NxIcon {...p} d={["M3.5 11.5 H12.5 L11 9.5 V7 A3 3 0 0 0 5 7 V9.5 Z","M6.5 13 a1.5 1.5 0 0 0 3 0"]} />,
  Sparkle:     (p) => <NxIcon {...p} d={["M8 2 L9.2 6.8 L14 8 L9.2 9.2 L8 14 L6.8 9.2 L2 8 L6.8 6.8 Z"]} fill="currentColor" strokeWidth={0} />,
  Robot:       (p) => <NxIcon {...p} d={["M3 6 H13 V12 H3 Z","M6 9 H6.1 M10 9 H10.1","M8 4 V6 M6 12 V14 M10 12 V14","M5 4 H11"]} />,
  Plus:        (p) => <NxIcon {...p} d={["M8 3 V13 M3 8 H13"]} />,
  Filter:      (p) => <NxIcon {...p} d={["M2 3.5 H14 L9.5 8.5 V13 L6.5 11.5 V8.5 Z"]} />,
  Download:    (p) => <NxIcon {...p} d={["M8 2.5 V10.5","M5 7.5 L8 10.5 L11 7.5","M2.5 13 H13.5"]} />,
  Eye:         (p) => <NxIcon {...p} d={["M1.5 8 C3 5 5.5 3.5 8 3.5 C10.5 3.5 13 5 14.5 8 C13 11 10.5 12.5 8 12.5 C5.5 12.5 3 11 1.5 8 Z","M8 10 a2 2 0 1 0 0 -4 a2 2 0 0 0 0 4"]} />,
  Info:        (p) => <NxIcon {...p} d={["M8 14 A6 6 0 1 0 8 2 A6 6 0 0 0 8 14","M8 7.2 V10.8","M8 5.2 H8.1"]} />,
  Calendar:    (p) => <NxIcon {...p} d={["M2.5 4 H13.5 V13.5 H2.5 Z","M2.5 7 H13.5","M5.5 2.5 V5 M10.5 2.5 V5"]} />,
  Chevron:     (p) => <NxIcon {...p} d={["M6 4 L10 8 L6 12"]} />,
  ChevronDown: (p) => <NxIcon {...p} d={["M4 6 L8 10 L12 6"]} />,
  ChevronLeft: (p) => <NxIcon {...p} d={["M10 4 L6 8 L10 12"]} />,
  ArrowUp:     (p) => <NxIcon {...p} d={["M8 13 V3 M4 7 L8 3 L12 7"]} />,
  ArrowDown:   (p) => <NxIcon {...p} d={["M8 3 V13 M4 9 L8 13 L12 9"]} />,
  ArrowRight:  (p) => <NxIcon {...p} d={["M3 8 H13 M9 4 L13 8 L9 12"]} />,
  Check:       (p) => <NxIcon {...p} d={["M3 8.5 L6.5 12 L13 4"]} />,
  X:           (p) => <NxIcon {...p} d={["M4 4 L12 12 M12 4 L4 12"]} />,
  Dots:        (p) => <NxIcon {...p} d={["M3.5 8 H3.6 M8 8 H8.1 M12.5 8 H12.6"]} strokeWidth={2.4} />,
  Send:        (p) => <NxIcon {...p} d={["M2 8 L14 2 L11 14 L8 9 Z","M2 8 L8 9"]} />,
  Doc:         (p) => <NxIcon {...p} d={["M3.5 2 H10 L12.5 4.5 V14 H3.5 Z","M9.5 2 V5 H12.5"]} />,
  Flash:       (p) => <NxIcon {...p} d={["M9 1.5 L4 9 H8 L7 14.5 L12 7 H8 Z"]} />,
  PinLeft:     (p) => <NxIcon {...p} d={["M6 3 V13 M3 6 L13 6","M9 3 L13 6 L9 9"]} />,
  Drag:        (p) => <NxIcon {...p} d={["M6 4 H6.1 M10 4 H10.1 M6 8 H6.1 M10 8 H10.1 M6 12 H6.1 M10 12 H10.1"]} strokeWidth={2.2} />,
  Clock:       (p) => <NxIcon {...p} d={["M8 14 A6 6 0 1 0 8 2 A6 6 0 0 0 8 14","M8 4.5 V8 L10.5 9.5"]} />,
  Folder:      (p) => <NxIcon {...p} d={["M2 4.5 V13 H14 V6 H8 L6.5 4.5 Z"]} />,
  Star:        (p) => <NxIcon {...p} d={["M8 2 L9.8 6 L14 6.5 L11 9.6 L11.8 14 L8 11.8 L4.2 14 L5 9.6 L2 6.5 L6.2 6 Z"]} />,
  LinkedIn:    (p) => <NxIcon {...p} d={["M3 3 H6 V13 H3 Z","M4.5 3 a1.5 1.5 0 1 0 0 -2 a1.5 1.5 0 0 0 0 2","M9 8 a2.5 2.5 0 0 1 5 0 V13 H11 V8","M9 6 V13"]} />,
  Twitter:     (p) => <NxIcon {...p} d={["M2 3 L14 13 M14 3 L2 13"]} />,
  Instagram:   (p) => <NxIcon {...p} d={["M5 2 H11 a3 3 0 0 1 3 3 V11 a3 3 0 0 1 -3 3 H5 a3 3 0 0 1 -3 -3 V5 a3 3 0 0 1 3 -3 Z","M8 10.5 a2.5 2.5 0 1 0 0 -5 a2.5 2.5 0 0 0 0 5","M11 4.5 H11.1"]} />,
  Facebook:    (p) => <NxIcon {...p} d={["M9.5 1.5 H8 A3.5 3.5 0 0 0 4.5 5 V7 H2.5 V10.5 H4.5 V14.5 H8 V10.5 H10 L10.5 7 H8 V5 A1 1 0 0 1 9 4 H9.5 Z"]} />,
  Trash:       (p) => <NxIcon {...p} d={["M3 4.5 H13","M5.5 4.5 V3 H10.5 V4.5","M5 4.5 L5.5 13 H10.5 L11 4.5","M7 7 V11 M9 7 V11"]} />,
  Pencil:      (p) => <NxIcon {...p} d={["M10.5 2.5 L13.5 5.5 L6 13 L2.5 13.5 L3 10 Z","M9 4 L12 7"]} />,
  Chat:        (p) => <NxIcon {...p} d={["M2.5 4 H13.5 V11 H8 L5 13.5 V11 H2.5 Z"]} />,
}
