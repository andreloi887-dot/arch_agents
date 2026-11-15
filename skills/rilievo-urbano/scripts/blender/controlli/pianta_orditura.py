import bpy, math, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import MultiPoint, Polygon
from shapely.ops import unary_union
blend, villa, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
bpy.ops.wm.open_mainfile(filepath=blend)
fig,ax=plt.subplots(figsize=(13,13))
for o in bpy.data.objects:
    if o.get('villa')!=villa or o.type!='MESH': continue
    W=[o.matrix_world@v.co for v in o.data.vertices]
    if 'vano' in o:
        if o['vano'].startswith('Cortile'): continue
        z0=min(w.z for w in W)
        pol=unary_union([Polygon([W[i].xy[:] for i in p.vertices]) for p in o.data.polygons if all(W[i].z<z0+.05 for i in p.vertices)]).buffer(0.01)
        g=pol if pol.geom_type=='Polygon' else max(pol.geoms,key=lambda q:q.area)
        ax.fill(*g.exterior.xy, color='#f2efe6', ec='#888', lw=1.2, zorder=1); c=g.representative_point(); ax.text(c.x,c.y,o['vano'],ha='center',fontsize=8,color='#333',zorder=6)
    elif o.name.startswith('Falda'):
        low=[p for p in o.data.polygons if (o.matrix_world.to_3x3()@p.normal).z<-0.3]
        if low:
            u=unary_union([Polygon([W[i].xy[:] for i in p.vertices]) for p in low]).buffer(0.01)
            for g in ([u] if u.geom_type=='Polygon' else u.geoms): ax.plot(*g.exterior.xy,color='#d33',lw=0.8,ls='--',zorder=2)
    elif o.get('ifc_classe') in ('IfcWindow','IfcDoor'):
        r=MultiPoint([w.xy[:] for w in W]).minimum_rotated_rectangle
        if r.geom_type=='Polygon' and r.length<12: ax.fill(*r.exterior.xy, color='#2a7fd4' if o['ifc_classe']=='IfcWindow' else '#e08a1e', zorder=5)
    elif o.get('finitura')=='orditura':
        for p in o.data.polygons:
            if p.normal.z>0.5:
                xs=[W[i].x for i in p.vertices]; ys=[W[i].y for i in p.vertices]
                larg=min(math.dist((xs[k],ys[k]),(xs[(k+1)%4],ys[(k+1)%4])) for k in range(4))
                ax.fill(xs,ys,color='#5b3310' if larg>0.12 else '#b5803f',zorder=4 if larg>0.12 else 3)
ax.set_aspect('equal'); ax.axis('off')
ax.set_title("Orditura del tetto in pianta – marrone scuro: travi di colmo, displuvio, compluvio; chiaro: travetti e travi perpendicolari;\nrosso tratteggiato: contorno delle falde; blu: finestre; arancio: porte",fontsize=10)
fig.savefig(out,dpi=110,bbox_inches='tight')
