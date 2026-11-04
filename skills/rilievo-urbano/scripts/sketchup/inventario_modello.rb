# encoding: UTF-8
# SketchUp Pro 2022 (Ruby 2.7) – Esporta inventario.json per la VERIFICA del rilievo urbano.
#
# Riconosce come elemento ogni gruppo/componente il cui nome (istanza o, per i componenti, definizione)
# inizia con un ID della scheda: E01, E03a, R02, A01, P01, V01… Per ognuno registra quote reali
# (bounding box in coordinate del modello, metri), baricentro in lat/lng (se georeferenziato), tag e
# materiali usati al suo interno. Esporta anche tutti i materiali con colore RGB (per le texture è il
# colore medio restituito da SketchUp) e dimensione della texture in mm.
# Uso: Window › Ruby Console → load 'C:/percorso/inventario_modello.rb'. Sola lettura: non modifica il modello.
require 'json'

module RilievoUrbano
  module Inventario
    RE_ID = /\A([ERAPV]\d{2,3}[a-z]?)(?![0-9A-Za-z])/

    def self.id_of(inst)
      names = [inst.name]
      names << inst.definition.name if inst.is_a?(Sketchup::ComponentInstance)
      names.each { |n| m = RE_ID.match(n.to_s.strip); return m[1] if m }
      nil
    end

    def self.mat_name(m)
      m ? m.display_name : nil
    end

    def self.collect_materials(ents, acc)
      ents.each do |e|
        case e
        when Sketchup::Face
          acc << mat_name(e.material) if e.material
          acc << mat_name(e.back_material) if e.back_material
        when Sketchup::Group, Sketchup::ComponentInstance
          acc << mat_name(e.material) if e.material
          collect_materials(e.definition.entities, acc)
        end
      end
      acc
    end

    def self.world_bounds(inst, tr)
      t = tr * inst.transformation
      bb = Geom::BoundingBox.new
      db = inst.definition.bounds
      (0..7).each { |i| bb.add(db.corner(i).transform(t)) }
      bb
    end

    def self.latlng(model, pt)
      return nil unless model.georeferenced?
      r = model.point_to_latlong(pt)
      la, lo = r.respond_to?(:latitude) ? [r.latitude.to_f, r.longitude.to_f] : [r.y.to_f, r.x.to_f]
      { 'lat' => la.round(7), 'lng' => lo.round(7) }
    end

    # Restituisce true se nel sottoalbero c'è almeno un elemento con ID.
    def self.walk(model, ents, tr, out, stats)
      found = false
      ents.each do |e|
        next unless e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
        id = id_of(e)
        if id
          bb = world_bounds(e, tr)
          mats = collect_materials(e.definition.entities, [])
          mats << mat_name(e.material) if e.material
          out << {
            'id' => id,
            'nome' => e.name.to_s.empty? ? e.definition.name : e.name,
            'tag' => e.layer.name,
            'z_min' => bb.min.z.to_m.round(3),
            'z_max' => bb.max.z.to_m.round(3),
            'altezza' => (bb.max.z - bb.min.z).to_m.round(3),
            'ingombro_xy_m' => [bb.width.to_m.round(2), bb.height.to_m.round(2)],
            'baricentro' => latlng(model, bb.center),
            'materiali' => mats.compact.uniq.sort,
            'nascosto' => e.hidden?
          }
          found = true
        else
          sub = walk(model, e.definition.entities, tr * e.transformation, out, stats)
          stats[:senza_id] += 1 unless sub
          found ||= sub
        end
      end
      found
    end

    def self.run
      model = Sketchup.active_model
      out = []
      stats = { senza_id: 0 }
      walk(model, model.entities, Geom::Transformation.new, out, stats)
      mats = model.materials.map do |m|
        tex = m.texture
        {
          'nome' => m.display_name,
          'rgb' => [m.color.red, m.color.green, m.color.blue],
          'texture' => !tex.nil?,
          'texture_mm' => tex ? [(tex.width.to_m * 1000).round, (tex.height.to_m * 1000).round] : nil,
          'alpha' => m.alpha.round(2)
        }
      end
      data = {
        'modello' => File.basename(model.path.to_s),
        'georeferenziato' => model.georeferenced?,
        'unita' => 'm',
        'elementi' => out,
        'materiali' => mats,
        'senza_id' => stats[:senza_id],
        'materiali_senza_prefisso' => mats.map { |m| m['nome'] }.reject { |n| n =~ /\AC\d{2,3}_/ }
      }
      path = if model.path.empty?
               UI.savepanel('Salva inventario', '', 'inventario.json')
             else
               File.join(File.dirname(model.path), 'inventario.json')
             end
      return unless path
      File.write(path, JSON.pretty_generate(data), encoding: 'UTF-8')
      puts "Inventario: #{out.size} elementi con ID, #{stats[:senza_id]} contenitori senza ID -> #{path}"
      ids = out.map { |o| o['id'] }
      dup = ids.group_by { |i| i }.select { |_, v| v.size > 1 }.keys
      puts "ID ripetuti (normale per le serie A/V): #{dup.join(', ')}" unless dup.empty?
    end
  end
end

RilievoUrbano::Inventario.run
