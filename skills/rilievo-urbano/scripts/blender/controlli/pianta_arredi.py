import bpy, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import MultiPoint, Polygon
from shapely.ops import unary_union
arg = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]   # blender -b -P ... -- oppure python
blend, villa, out = arg[0], int(arg[1]), arg[2]
bpy.ops.wm.open_mainfile(filepath=blend)
COL={'armadio':'#b98a55','letto':'#d9cfc0','comodino':'#c8a47a','madia_tv':'#a07a4a','scrivania':'#c8a47a','parete_tv':'#8a6a45','cucina':'#e8e2d6','divano':'#b9ad9a','tavolino':'#cfc4b2','tavolo':'#c8a47a'}
fig,ax=plt.subplots(figsize=(13,13))
for o in bpy.data.objects:
    if o.get('villa')!=villa or o.type!='MESH': continue
    W=[o.matrix_world@v.co for v in o.data.vertices]
    if 'vano' in o:
        if o['vano'].startswith('Cortile'): continue
        z0=min(w.z for w in W)
        pol=unary_union([Polygon([W[i].xy[:] for i in p.vertices]) for p in o.data.polygons if all(W[i].z<z0+.05 for i in p.vertices)]).buffer(0.01)
        g=pol if pol.geom_type=='Polygon' else max(pol.geoms,key=lambda q:q.area)
        ax.fill(*g.exterior.xy, color='#faf8f2', ec='#555', lw=1.5, zorder=1); c=g.representative_point(); ax.text(c.x,c.y,o['vano'],ha='center',fontsize=7,color='#999',zorder=2)
    elif o.get('ifc_classe') in ('IfcWindow','IfcDoor'):
        r=MultiPoint([w.xy[:] for w in W]).minimum_rotated_rectangle
        if r.geom_type=='Polygon' and r.length<14: ax.fill(*r.exterior.xy, color='#2a7fd4' if o['ifc_classe']=='IfcWindow' else '#e0541e', zorder=5)
    elif 'arredo' in o and 'tessili' not in o.name:
        ing=list(o['ingombro'])
        if len(ing)>=6:
            xs=ing[0::2]; ys=ing[1::2]; ax.fill(xs,ys,color=COL.get(o['arredo'],'#ccc'),ec='#333',lw=0.8,zorder=3)
            ax.text(sum(xs)/len(xs),sum(ys)/len(ys),o['arredo'].replace('_',' '),ha='center',va='center',fontsize=7,zorder=6)
for o in bpy.data.objects:
    if o.get('villa')==villa and 'battuta' in o:
        b=list(o['battuta']); ax.fill(b[0::2],b[1::2],color='#e0541e',alpha=.25,ec='#e0541e',lw=1,zorder=7)
ax.set_aspect('equal'); ax.axis('off'); ax.set_title('Arredi in pianta (blu: finestre; rosso: porte)',fontsize=10)
fig.savefig(out,dpi=100,bbox_inches='tight')
