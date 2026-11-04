# encoding: UTF-8
# SketchUp Pro 2022 (Ruby 2.7) – Genera il contesto urbano da contesto.json (coordinate locali in metri:
# x = Est, y = Nord, z = quota relativa all'origine). Strategia e codice di base: agente sketchup-expert;
# integrazione (edifici, arredo, vegetazione, texture relative, fasce verticali): sessione di rilievo.
#
# Uso (Window › Ruby Console, modello georeferenziato con File › Geo-location › Add Location):
#   load 'C:/…/costruisci_contesto.rb'
#   RilievoUrbano::Contesto.costruisci('C:/…/modello/contesto.json')
# Rilanciabile: sostituisce il gruppo "CONTESTO – generato da dati" precedente. Un solo Ctrl+Z annulla tutto.
# Prima di scene_da_manifest.rb: nascondi il terreno di Add Location (l'entità, non il tag), la Location
# Snapshot e il tag 00_Riferimenti, altrimenti la quota delle camere viene presa sulla superficie sbagliata.
require 'json'
require 'set'

module RilievoUrbano
  module Contesto
    DICT  = 'rilievo_urbano'.freeze
    ZV    = Geom::Vector3d.new(0, 0, 1)
    MIN2A = 0.002.m * 0.002.m # 2×area minima di un triangolo, in pollici² (scarti contati in @scarti)

    def self.pt(a)
      Geom::Point3d.new(a[0].to_f.m, a[1].to_f.m, a[2].to_f.m)
    end

    def self.chiave(p)
      [p.x, p.y, p.z].map { |c| (c.to_m * 1000).round }
    end

    def self.tag(model, nome)
      return model.layers[0] if nome.nil? || nome.empty?
      model.layers[nome] || model.layers.add(nome)
    end

    def self.materiale(model, nome, m, base_dir)
      mat = model.materials[nome] || model.materials.add(nome)
      if m['texture']
        tp = File.expand_path(m['texture'], base_dir)
        raise "Texture mancante: #{tp} (copia la cartella texture/ accanto al json)" unless File.exist?(tp)
        mat.texture = tp
        mat.texture.size = [m['modulo_mm'][0].mm, m['modulo_mm'][1].mm]
      else
        mat.color = Sketchup::Color.new(*m['hex'].delete('#').scan(/../).map { |c| c.to_i(16) })
      end
      mat.alpha = m['alpha'].to_f if m['alpha']
      mat
    end

    def self.mat!(model, nome)
      model.materials[nome] or raise "Materiale mancante: #{nome}"
    end

    # --- georiferimento (stessa logica di importa_catasto.rb e scene_da_manifest.rb)
    def self.ll_of(model, p)
      r = model.point_to_latlong(p)
      r.respond_to?(:latitude) ? [r.latitude.to_f, r.longitude.to_f] : [r.y.to_f, r.x.to_f]
    end

    def self.to_point(model, lat, lng)
      [[lng, lat], [lat, lng]].each do |arg|
        p = model.latlong_to_point(arg)
        la, lo = ll_of(model, p)
        return p if (la - lat).abs < 1e-6 && (lo - lng).abs < 1e-6
      end
      raise "latlong_to_point non verificabile per #{lat}, #{lng}"
    end

    def self.trasf_geo(model, lat0, lng0)
      o = to_point(model, lat0, lng0)
      e = to_point(model, lat0, lng0 + 1e-4) - o
      e.z = 0
      e.normalize!
      Geom::Transformation.axes(Geom::Point3d.new(o.x, o.y, 0), e, ZV.cross(e), ZV)
    end

    # Rototraslazione applicata a mano al gruppo CATASTO (solo dx, dy, rotazione attorno a Z)
    def self.delta_catasto(model)
      g = model.entities.grep(Sketchup::Group).find { |x| x.name.start_with?('CATASTO') }
      o = g && g.get_attribute(DICT, 'origine')
      return nil unless o
      d = g.transformation * Geom::Transformation.new(o).inverse
      Geom::Transformation.translation(Geom::Vector3d.new(d.origin.x, d.origin.y, 0)) *
        Geom::Transformation.rotation(ORIGIN, Z_AXIS, Math.atan2(d.xaxis.y, d.xaxis.x))
    end

    # --- texture e spigoli
    def self.uv_auto(n, p)
      return [p.x.to_m, p.y.to_m] if n.z.abs >= 0.5 # dall'alto: continua tra triangoli e gruppi
      h = ZV.cross(n)
      h.normalize!
      [(p.x * h.x + p.y * h.y).to_m, p.z.to_m]      # pareti: u orizzontale nel piano, v = quota
    end

    def self.posiziona(face, mat, uvf = nil)
      return unless mat.texture
      tw = mat.texture.width.to_m
      th = mat.texture.height.to_m
      vs = face.outer_loop.vertices.first(3).map(&:position)
      uv = vs.map { |p| uvf ? uvf.call(p) : uv_auto(face.normal, p) }
      return if uv.any?(&:nil?)
      c  = Geom::Point3d.new((vs[0].x + vs[1].x + vs[2].x) / 3.0,
                             (vs[0].y + vs[1].y + vs[2].y) / 3.0,
                             (vs[0].z + vs[1].z + vs[2].z) / 3.0)
      uc = [(uv[0][0] + uv[1][0] + uv[2][0]) / 3.0, (uv[0][1] + uv[1][1] + uv[2][1]) / 3.0]
      pts = []
      (vs + [c]).zip(uv + [uc]).each { |p, (u, v)| pts << p << Geom::Point3d.new(u / tw, v / th, 0) }
      face.position_material(mat, pts, true) # 4 coppie: mappatura affine esatta
    rescue StandardError
      nil # mappatura degenere: resta quella di default
    end

    def self.ammorbidisci(ents, max_deg)
      lim = max_deg.to_f.degrees
      ents.grep(Sketchup::Edge).each do |e|
        f = e.faces
        next unless f.size == 2 && f[0].material == f[1].material # bordi e cambi di materiale restano duri
        next if f[0].normal.angle_between(f[1].normal) > lim
        e.soft = true
        e.smooth = true
      end
    end

    # (a) Superficie 2.5D da TIN già triangolata (CDT fatta fuori, triangoli antiorari visti dall'alto).
    # Le facce verticali (fasce: cordoli, salti) ricevono il materiale anche sul retro.
    def self.superficie(model, parent, s)
      g = parent.add_group
      g.name = s['nome']
      ents = g.entities
      vtx = s['vertici'].map { |a| pt(a) }
      uvf = nil
      if s['uv']
        lut = {}
        vtx.each_with_index { |p, i| lut[chiave(p)] = s['uv'][i] }
        uvf = ->(p) { lut[chiave(p)] }
      end
      s['triangoli'].group_by { |t| t[3] || 0 }.each do |_mi, tris|
        mesh = Geom::PolygonMesh.new(tris.size * 3, tris.size)
        tris.each do |t|
          a, b, c = vtx.values_at(t[0], t[1], t[2])
          if (b - a).cross(c - a).length > MIN2A
            mesh.add_polygon(a, b, c)
          else
            @scarti += 1
          end
        end
        ents.add_faces_from_mesh(mesh, Geom::PolygonMesh::NO_SMOOTH_OR_HIDE)
      end
      # materiali assegnati dopo, per normale: [0] superfici 2.5D, [1] fasce verticali (cordoli, salti)
      m0 = mat!(model, s['materiali'][0])
      m1 = mat!(model, s['materiali'][1] || s['materiali'][0])
      ents.grep(Sketchup::Face).each do |f|
        f.reverse! if f.normal.z < -0.3 # prima di assegnare il materiale
        vert = f.normal.z.abs < 0.3
        f.material = vert ? m1 : m0
        f.back_material = vert ? m1 : nil
        posiziona(f, f.material, uvf)
      end
      ammorbidisci(ents, s['smooth_deg'] || 30)
      g
    end

    # (b) Muro a sezione variabile (sweep di sezioni a 4 punti: piede esterno, testa esterna, testa interna,
    # piede interno). Materiale su entrambe le facce: l'orientamento dipende dal verso della polilinea.
    def self.sweep(model, parent, w)
      mat = mat!(model, w['materiale'])
      g = parent.add_group
      g.name = w['nome']
      ents = g.entities
      sez = w['stazioni'].map { |s| s.map { |a| pt(a) } }
      # il lato lotto (piede interno, indice 3) deve stare a SINISTRA del verso di avanzamento
      i1 = (1...sez.size).find { |i| sez[i][0].distance(sez[0][0]) > 0.01.m }
      if i1
        d = sez[i1][0] - sez[0][0]
        o = sez[0][3] - sez[0][0]
        sez.map!(&:reverse) if d.x * o.y - d.y * o.x < 0
      end
      k = sez.first.size
      mesh = Geom::PolygonMesh.new(sez.size * k, sez.size * k * 2 + 2 * k)
      tri = lambda do |a, b, c|
        if (b - a).cross(c - a).length > MIN2A then mesh.add_polygon(a, b, c) else @scarti += 1 end
      end
      sez.each_cons(2) do |s0, s1|
        k.times do |j|
          a0 = s0[j]; b0 = s0[(j + 1) % k]; a1 = s1[j]; b1 = s1[(j + 1) % k]
          tri.call(a0, a1, b1)
          tri.call(a0, b1, b0)
        end
      end
      tappo = ->(s) { (1...k - 1).each { |j| tri.call(s[0], s[j], s[j + 1]) } }
      tappo.call(sez.first)
      tappo.call(sez.last.reverse)
      ents.add_faces_from_mesh(mesh, Geom::PolygonMesh::NO_SMOOTH_OR_HIDE)
      ents.grep(Sketchup::Face).each do |f|
        f.material = mat
        f.back_material = nil
        posiziona(f, mat)
      end
      ammorbidisci(ents, w['smooth_deg'] || 20)
      g
    end

    # (c) Recinzione su paletti lungo una polilinea (base = testa del muro).
    def self.def_palo(model, r, mat)
      @fatte ||= Set.new
      nome = format('%s_h%03d', r['def_palo'] || 'REC_paletto', (r['h'] * 100).round)
      d = model.definitions[nome] || model.definitions.add(nome)
      return d if @fatte.include?(nome)
      d.entities.clear!
      s = (r['lato_palo'] || 0.04) / 2.0
      z0 = -0.10 # immorsato nella testa del muro
      f = d.entities.add_face([[-s, -s], [s, -s], [s, s], [-s, s]].map { |x, y| Geom::Point3d.new(x.m, y.m, z0.m) })
      f.reverse! if f.normal.z < 0
      f.pushpull((r['h'] + (r['gap'] || 0.05) + 0.05 - z0).m)
      d.entities.grep(Sketchup::Face).each { |x| x.material = mat }
      @fatte << nome
      d
    end

    def self.recinzione(model, parent, r)
      m_palo = mat!(model, r['materiale_palo'])
      m_rete = mat!(model, r['materiale_rete'])
      d = def_palo(model, r, m_palo)
      g = parent.add_group
      g.name = r['nome']
      ents = g.entities
      passo = r['passo'] || 2.5
      h = r['h']
      gap = r['gap'] || 0.05
      pa = r['asse'].map { |a| pt(a) }
      pali = []
      pa.each_cons(2) do |p0, p1|
        v = Geom::Vector3d.new(p1.x - p0.x, p1.y - p0.y, 0)
        next if v.length < 0.01.m
        n = [(v.length.to_m / passo).ceil, 1].max
        dir = v.normalize
        (0..n).each do |j|
          next if j.zero? && !pali.empty?
          t = j.to_f / n
          pali << [Geom::Point3d.linear_combination(1 - t, p0, t, p1), dir]
        end
      end
      pali.each { |p, dir| ents.add_instance(d, Geom::Transformation.axes(p, dir, ZV.cross(dir), ZV)) }
      tw = m_rete.texture ? m_rete.texture.width.to_m : 1.0
      th = m_rete.texture ? m_rete.texture.height.to_m : 1.0
      s_acc = 0.0
      pali.each_cons(2) do |(p0, _), (p1, _)|
        l = Math.hypot((p1.x - p0.x).to_m, (p1.y - p0.y).to_m)
        b0 = p0.offset(ZV, gap.m); b1 = p1.offset(ZV, gap.m)
        t0 = b0.offset(ZV, h.m);   t1 = b1.offset(ZV, h.m)
        begin
          f = ents.add_face(b0, b1, t1, t0)
        rescue ArgumentError
          next
        end
        f.material = m_rete
        f.back_material = m_rete
        if m_rete.texture
          uv = [[s_acc, 0], [s_acc + l, 0], [s_acc + l, h], [s_acc, h]]
          pts = []
          [b0, b1, t1, t0].each_with_index { |p, i| pts << p << Geom::Point3d.new(uv[i][0] / tw, uv[i][1] / th, 0) }
          f.position_material(m_rete, pts, true)
          f.position_material(m_rete, pts, false)
        end
        s_acc += l
      end
      g
    end

    # (d) Edificio LOD1: estrusione dell'impronta da z_base per 'altezza'; copertura col suo materiale.
    def self.edificio(model, parent, e)
      m_fac = mat!(model, e['materiale'])
      m_cop = mat!(model, e['materiale_copertura'])
      g = parent.add_group
      g.name = e['nome']
      zb = e['z_base'].to_f
      pts = e['impronta'].map { |x, y| Geom::Point3d.new(x.to_f.m, y.to_f.m, zb.m) }
      f = g.entities.add_face(pts)
      f.reverse! if f.normal.z < 0
      f.pushpull(e['altezza'].to_f.m)
      g.entities.grep(Sketchup::Face).each do |x|
        x.material = x.normal.z > 0.9 ? m_cop : m_fac
        x.back_material = nil
      end
      g
    rescue ArgumentError => err
      puts "Edificio #{e['nome']} saltato: #{err.message}"
      @saltati << e['nome']
      g.erase! if g && g.valid?
      nil
    end

    # (e) Arredo: parallelepipedo (con testa per lampioni e disco per cartelli), ruotato di rot_deg attorno a Z.
    def self.box(ents, cx, cy, z, w, d, h, mat)
      sub = ents.add_group.entities # sotto-gruppo senza nome: niente geometria fusa tra i pezzi
      pts = [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]].map { |x, y| Geom::Point3d.new((cx + x).m, (cy + y).m, z.m) }
      f = sub.add_face(pts)
      f.reverse! if f.normal.z < 0
      f.pushpull(h.m)
      sub.grep(Sketchup::Face).each { |x| x.material = mat }
    end

    def self.oggetto(model, parent, o)
      mat = mat!(model, o['materiale'])
      g = parent.add_group
      g.name = o['nome']
      w, d, h = o['dim']
      box(g.entities, 0, 0, 0, w, d, h, mat)
      box(g.entities, -0.25, 0, h - 0.15, 0.6, 0.3, 0.15, mat) if o['testa'] == 'lampione'
      if o['testa'] == 'disco'
        sub = g.entities.add_group.entities
        c = sub.add_circle(Geom::Point3d.new(0.06.m, 0, (h - 0.3).m), Geom::Vector3d.new(1, 0, 0), 0.3.m, 16)
        disco = sub.add_face(c)
        disco.pushpull(0.02.m) if disco
        sub.grep(Sketchup::Face).each { |x| x.material = mat }
      end
      rot = Geom::Transformation.rotation(ORIGIN, Z_AXIS, (o['rot_deg'] || 0).to_f.degrees)
      g.transformation = Geom::Transformation.translation(Geom::Vector3d.new(o['xy'][0].to_f.m, o['xy'][1].to_f.m, o['z'].to_f.m)) * rot
      g
    end

    # (f) Palma giovane senza fusto: ciuffo di fronde (triangoli) – sostituibile con un modello Lumion.
    def self.palma(model, parent, v)
      mat = mat!(model, v['materiale'])
      g = parent.add_group
      g.name = v['nome']
      r = v['chioma'].to_f / 2.0
      h = v['h'].to_f
      9.times do |k|
        a = k * 2 * Math::PI / 9
        base = Geom::Point3d.new(0, 0, 0.3.m)
        tip = Geom::Point3d.new((r * Math.cos(a)).m, (r * Math.sin(a)).m, (h * 0.55).m)
        mid = Geom::Point3d.new((r * 0.5 * Math.cos(a)).m, (r * 0.5 * Math.sin(a)).m, h.m)
        side = Geom::Vector3d.new(-Math.sin(a), Math.cos(a), 0)
        side.length = 0.25.m
        [[base, mid.offset(side), mid.offset(side.reverse)], [mid.offset(side), tip, mid.offset(side.reverse)]].each do |tri|
          f = g.entities.add_face(tri)
          f.material = mat
          f.back_material = mat
        end
      end
      g.transformation = Geom::Transformation.translation(Geom::Vector3d.new(v['xy'][0].to_f.m, v['xy'][1].to_f.m, v['z'].to_f.m))
      g
    end

    def self.costruisci(path)
      model = Sketchup.active_model
      raise 'Modello non georeferenziato: File › Geo-location › Add Location' unless model.georeferenced?
      base_dir = File.dirname(File.expand_path(path))
      dati = JSON.parse(File.read(path, encoding: 'UTF-8'))
      tg = trasf_geo(model, dati['origine']['lat'], dati['origine']['lng'])
      (dati['controllo'] || []).each do |c| # coerenza tra la proiezione dei dati e quella di SketchUp
        err = (tg * pt([c['x'], c['y'], 0])).distance(to_point(model, c['lat'], c['lng'])).to_m
        msg = format('Controllo %s: scarto %.3f m', c['nome'], err)
        raise "#{msg}: proiezione incoerente" if err > 0.5
        puts(err > 0.05 ? "ATTENZIONE #{msg}" : msg)
      end
      tr = tg
      if dati['applica_allineamento_catasto']
        dc = delta_catasto(model) or raise 'Gruppo CATASTO allineato non trovato'
        tr = dc * tg
      end
      prec = model.active_layer
      @fatte = Set.new
      @scarti = 0
      @saltati = []
      t0 = Time.now
      model.start_operation('Contesto da dati', true)
      begin
        model.active_layer = model.layers[0] # le entità nuove prendono il tag attivo
        old = model.entities.grep(Sketchup::Group).find { |x| x.get_attribute(DICT, 'contesto') }
        old.erase! if old
        dati['materiali'].each { |n, m| materiale(model, n, m, base_dir) }
        root = model.entities.add_group
        root.name = 'CONTESTO – generato da dati'
        root.set_attribute(DICT, 'contesto', path)
        root.transformation = tr
        (dati['superfici'] || []).each { |s| superficie(model, root.entities, s).layer = tag(model, s['tag']) }
        (dati['muri'] || []).each { |w| sweep(model, root.entities, w).layer = tag(model, w['tag']) }
        (dati['recinzioni'] || []).each { |r| recinzione(model, root.entities, r).layer = tag(model, r['tag']) }
        (dati['edifici'] || []).each { |e| (g = edificio(model, root.entities, e)) && g.layer = tag(model, e['tag']) }
        (dati['oggetti'] || []).each { |o| oggetto(model, root.entities, o).layer = tag(model, o['tag']) }
        (dati['vegetazione'] || []).each { |v| palma(model, root.entities, v).layer = tag(model, v['tag']) }
        model.definitions.purge_unused # definizioni dei gruppi di un'esecuzione precedente
        model.commit_operation
        puts format('Contesto generato da %s in %.1f s', path, Time.now - t0)
        puts "Triangoli scartati perché degeneri: #{@scarti}" if @scarti > 0
        puts "Edifici saltati (#{@saltati.size}): #{@saltati.join(', ')}" unless @saltati.empty?
        puts 'Prima di scene_da_manifest.rb: nascondi terreno di Add Location, Location Snapshot e tag 00_Riferimenti.'
      rescue StandardError
        model.abort_operation
        raise
      ensure
        model.active_layer = prec
      end
    end
  end
end

puts 'RilievoUrbano::Contesto caricato: .costruisci(percorso_contesto_json)'
