/** A labelled number tile, as used in the bet slip and the Scout panel. */
export default function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ flex: '1 1 120px', background: 'var(--bg)', borderRadius: 8, padding: '10px 12px' }}>
      <div className="dim" style={{ fontSize: 12 }}>{label}</div>
      <div className="mono" style={{ fontSize: 20, fontWeight: 500 }}>{value}</div>
    </div>
  );
}
