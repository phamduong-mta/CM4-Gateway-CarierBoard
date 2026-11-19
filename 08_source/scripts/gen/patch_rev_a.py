"""Sửa tay cuối cùng (rev A) sau route.py (biến thể S) + finish.py 5, chạy trên hardware/cm4-gateway.kicad_pcb.
1) nối via chân 8 U401 vào lưới +3V3_SW trên B; 2) thu hẹp vết +3V3_SW cạnh C541 (thiếu 0.001 mm);
3) thêm gờ bù độ dài WAN_MDI1_N trên In2 (lệch 4.9 → 2.1 mm)."""
import pcbnew,math
M=lambda v:int(round(v*1e6))
b=pcbnew.LoadBoard(__import__('sys').argv[1])
def seg(net,lay,pts,w):
  n=b.FindNet(net)
  for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
    t=pcbnew.PCB_TRACK(b);t.SetStart(pcbnew.VECTOR2I(M(x1),M(y1)));t.SetEnd(pcbnew.VECTOR2I(M(x2),M(y2)))
    t.SetWidth(M(w));t.SetLayer(b.GetLayerID(lay));t.SetNet(n);b.Add(t)
# 1) noi via chan 8 U401 vao luoi +3V3_SW tren B
seg('+3V3_SW','B.Cu',[(103.05,73.5),(102.35,72.8),(102.35,72.75)],0.12)
for t in list(b.GetTracks()):
  if t.Type()==pcbnew.PCB_VIA_T: continue
  s,e=t.GetStart(),t.GetEnd()
  # 2) khe ho 0.0009 mm voi C541
  if t.GetNetname()=='+3V3_SW' and t.GetLayerName()=='B.Cu' and abs(t.GetLength()/1e6-1.7678)<1e-3 and abs((s.x+e.x)/2e6-66.15)<1.5:
    t.SetWidth(t.GetWidth()-M(0.006)); print('w',t.GetWidth())
  # 3) bu do dai WAN_MDI1_N
  if t.GetNetname()=='WAN_MDI1_N' and t.GetLayerName()=='In2.Cu' and s.x==M(174) and s.y==M(111.2) and e.y==M(116.2):
    w=t.GetWidth()/1e6; b.Remove(t)
    seg('WAN_MDI1_N','In2.Cu',[(174,111.2),(174,112.4),(174.3,112.7),(175.5,112.7),(175.7,112.9),(175.7,113.3),(175.5,113.5),(174.3,113.5),(174,113.8),(174,116.2)],w); print('tuned')
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(__import__('sys').argv[1])
