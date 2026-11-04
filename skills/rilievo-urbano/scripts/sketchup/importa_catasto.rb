# encoding: UTF-8
# SketchUp Pro 2022 (Ruby 2.7) – Importa sagome catastali (GeoJSON da vettorializzazione WMS AdE)
# come riferimento da ALLINEARE: il catasto è spesso sfasato di metri rispetto alla realtà.
#
# Uso (Window › Ruby Console, modello georeferenziato con Add Location):
#   load '…/importa_catasto.rb'
#   RilievoUrbano::Catasto.importa      # sceglie uno o più .geojson → gruppo "CATASTO – da allineare"
#   …allinea il gruppo INTERO con Move/Rotate su ≥3 spigoli riconoscibili sull'imagery di Add Location
#   RilievoUrbano::Catasto.report       # stampa dx, dy, rotazione applicati (da riportare nella scheda)
#
# Regola: muovere/ruotare solo il gruppo intero (rototraslazione rigida), mai i singoli edifici.
# Se un edificio non coincide dopo l'allineamento, la sagoma è obsoleta: segnalarlo, non deformarla.
require 'json'

module RilievoUrbano
  module Catasto
    DICT = 'rilievo_urbano'
    TAG  = '00_Riferimenti'

    def self.ll_of(model, pt)
      r = model.point_to_latlong(pt)
      r.respond_to?(:latitude) ? [r.latitude.to_f, r.longitude.to_f] : [r.y.to_f, r.x.to_f]
    end

    def self.to_point(model, lng, lat)
      [[lng, lat], [lat, lng]].each do |arg|
        pt = model.latlong_to_point(arg)
        la, lo = ll_of(model, pt)
        return Geom::Point3d.new(pt.x, pt.y, 0) if (la - lat).abs < 1e-5 && (lo - lng).abs < 1e-5
      end
      raise "Conversione lat/lng non verificabile per #{lat}, #{lng}"
    end

    def self.colore(model, nome, rgb, alpha)
      m = model.materials[nome] || model.materials.add(nome)
      m.color = Sketchup::Color.new(*rgb)
      m.alpha = alpha
      m
    end

    def self.importa
      model = Sketchup.active_model
      unless model.georeferenced?
        UI.messagebox('Modello non georeferenziato: esegui prima File › Geo-location › Add Location.')
        return
      end
      paths = UI.openpanel('GeoJSON catasto', '', 'GeoJSON|*.geojson;*.json||')
      return unless paths
      paths = [paths] unless paths.is_a?(Array)
      tag = model.layers[TAG] || model.layers.add(TAG)
      mat = {
        'fabbricato' => colore(model, 'REF_catasto_fabbricati', [236, 128, 19], 0.6),
        'particella' => colore(model, 'REF_catasto_particelle', [255, 245, 210], 0.25),
        'strada'     => colore(model, 'REF_catasto_strade', [150, 150, 150], 0.5)
      }
      model.start_operation('Importa catasto', true)
      begin
        root = model.entities.add_group
        root.name = 'CATASTO – da allineare'
        root.layer = tag
        root.set_attribute(DICT, 'origine', root.transformation.to_a)
        conta = Hash.new(0)
        paths.each do |path|
          gj = JSON.parse(File.read(path, encoding: 'UTF-8'))
          gj['features'].each do |f|
            next unless f['geometry'] && f['geometry']['type'] == 'Polygon'
            tipo = f.dig('properties', 'tipo') || 'fabbricato'
            z = { 'particella' => 0.02, 'strada' => 0.04, 'fabbricato' => 0.06 }[tipo] || 0.06
            ring = f['geometry']['coordinates'][0][0..-2]
            pts = ring.map { |lng, lat| p = to_point(model, lng, lat); Geom::Point3d.new(p.x, p.y, z.m) }
            pts = pts.each_with_index.reject { |p, i| i > 0 && p == pts[i - 1] }.map(&:first)
            next if pts.size < 3
            g = root.entities.add_group
            begin
              face = g.entities.add_face(pts)
            rescue ArgumentError
              g.erase!
              next
            end
            face.reverse! if face.normal.z < 0
            face.material = mat[tipo]
            g.name = "CAT #{tipo} #{(f['properties'] || {})['area_m2']} m2"
            conta[tipo] += 1
          end
        end
        model.commit_operation
        puts "Importati: #{conta.map { |k, v| "#{v} #{k}" }.join(', ')} nel gruppo 'CATASTO – da allineare' (tag #{TAG})."
        puts 'Ora allinea il gruppo intero su ≥3 spigoli visibili nell\'imagery di Add Location, poi RilievoUrbano::Catasto.report'
      rescue StandardError => e
        model.abort_operation
        UI.messagebox("Errore: #{e.message}")
        raise
      end
    end

    def self.report
      model = Sketchup.active_model
      g = model.entities.grep(Sketchup::Group).find { |x| x.name.start_with?('CATASTO') }
      return puts('Gruppo CATASTO non trovato') unless g
      t = g.transformation
      o = Geom::Transformation.new(g.get_attribute(DICT, 'origine'))
      delta = t * o.inverse
      v = delta.origin
      ax = delta.xaxis
      rot = Math.atan2(ax.y, ax.x).radians
      puts format('Allineamento catasto: dx = %.2f m (E+), dy = %.2f m (N+, se Nord = +Y), rotazione = %.2f° (antioraria)',
                  v.x.to_m, v.y.to_m, rot)
      puts 'Riporta questi valori nella scheda (zona.allineamento_catasto) e indica i punti di controllo usati.'
    end
  end
end

puts 'RilievoUrbano::Catasto caricato: .importa  poi  .report'
