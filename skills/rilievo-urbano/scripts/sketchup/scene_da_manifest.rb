# encoding: UTF-8
# SketchUp Pro 2022 (Ruby 2.7) – Crea scene con la stessa camera delle riprese Street View
# (manifest_riprese.json di gmaps.py) ed esporta i PNG per la VERIFICA.
#
# Prerequisiti: modello georeferenziato (File › Geo-location › Add Location) con terreno visibile.
# Uso: Window › Ruby Console → load 'C:/percorso/scene_da_manifest.rb'  (oppure incolla il file)
#      Lavora su una copia del .skp. Tutte le scene si annullano con un solo Ctrl+Z.
#
# Camera: posizione = pano reale; quota occhio = terreno (raytest verso il basso) + eye_height_m
# (2,5 m di default, sovrascrivibile per ripresa con "z_occhio_m"); heading 0 = Nord, orario;
# pitch positivo verso l'alto; fov sul formato quadrato (aspect ratio 1:1).
require 'json'

module RilievoUrbano
  module SceneDaManifest
    EXPORT_PX = 1280

    def self.ll_of(model, pt)
      r = model.point_to_latlong(pt)
      r.respond_to?(:latitude) ? [r.latitude.to_f, r.longitude.to_f] : [r.y.to_f, r.x.to_f]
    end

    # latlong_to_point vuole [lng, lat]; si verifica con la conversione inversa.
    def self.to_point(model, lat, lng)
      [[lng, lat], [lat, lng]].each do |arg|
        pt = model.latlong_to_point(arg)
        la, lo = ll_of(model, pt)
        return pt if (la - lat).abs < 1e-5 && (lo - lng).abs < 1e-5
      end
      raise "Conversione lat/lng non verificabile per #{lat}, #{lng}"
    end

    def self.combo(*pairs) # somma di (vettore, scalare) senza usare Vector3d#* (prodotto vettoriale)
      x = y = z = 0.0
      pairs.each { |v, k| x += v.x * k; y += v.y * k; z += v.z * k }
      Geom::Vector3d.new(x, y, z)
    end

    def self.ground_z(model, pt)
      ray = [Geom::Point3d.new(pt.x, pt.y, pt.z + 1000.m), Geom::Vector3d.new(0, 0, -1)]
      hit = model.raytest(ray) # ignora la geometria nascosta
      hit ? hit[0].z : 0.0
    end

    def self.camera_for(model, s, eye_default)
      lat = s['lat'].to_f
      lng = s['lng'].to_f
      p0 = to_point(model, lat, lng)
      north = to_point(model, lat + 1e-4, lng) - p0
      east  = to_point(model, lat, lng + 1e-4) - p0
      north.z = 0; east.z = 0
      north.normalize!; east.normalize!
      h = s['heading'].to_f.degrees
      p = s['pitch'].to_f.degrees
      flat = combo([north, Math.cos(h)], [east, Math.sin(h)])
      flat.normalize!
      zaxis = Geom::Vector3d.new(0, 0, 1)
      dir = combo([flat, Math.cos(p)], [zaxis, Math.sin(p)])
      up  = combo([flat, -Math.sin(p)], [zaxis, Math.cos(p)])
      z_eye = s['z_occhio_m'] ? s['z_occhio_m'].to_f.m : ground_z(model, p0) + eye_default.m
      eye = Geom::Point3d.new(p0.x, p0.y, z_eye)
      target = eye.offset(dir, 10.m)
      cam = Sketchup::Camera.new(eye, target, up, true, s['fov'].to_f)
      cam.aspect_ratio = 1.0
      cam
    end

    # path/folder facoltativi: se assenti si chiedono con le finestre di dialogo (uso interattivo)
    def self.run(path = nil, folder = nil, interattivo = true)
      model = Sketchup.active_model
      unless model.georeferenced?
        raise 'Modello non georeferenziato' unless interattivo
        UI.messagebox('Modello non georeferenziato: esegui prima File › Geo-location › Add Location.')
        return
      end
      path ||= UI.openpanel('Seleziona manifest_riprese.json', '', 'JSON|*.json||')
      return unless path
      man = JSON.parse(File.read(path, encoding: 'UTF-8'))
      eye_default = (man['eye_height_m'] || 2.5).to_f
      base = model.path.empty? ? File.dirname(path) : File.dirname(model.path)
      folder ||= File.join(base, 'export_verifica')
      Dir.mkdir(folder) unless Dir.exist?(folder)

      po = model.options['PageOptions']
      old_transition = po['ShowTransition']
      po['ShowTransition'] = false
      view = model.active_view
      done = []
      model.start_operation('Scene da manifest Street View', true)
      begin
        man['riprese'].each do |s|
          cam = camera_for(model, s, eye_default)
          view.camera = cam
          old = model.pages[s['id']]
          model.pages.erase(old) if old
          page = model.pages.add(s['id'])
          page.description = "#{s['inquadra']} | pano #{s['pano_id']} #{s['data']} | h #{s['heading']} p #{s['pitch']} fov #{s['fov']}"
          file = File.join(folder, "#{s['id']}.png")
          view.write_image(filename: file, width: EXPORT_PX, height: EXPORT_PX, antialias: true, transparent: false)
          done << s['id']
        end
        model.commit_operation
      rescue StandardError => e
        model.abort_operation
        UI.messagebox("Errore: #{e.message}") if interattivo
        raise
      ensure
        po['ShowTransition'] = old_transition
      end
      puts "Scene create ed esportate (#{done.size}): #{done.join(', ')} -> #{folder}"
      puts 'Controlla subito la prima vista: se l\'orizzonte non coincide con la foto, correggi z_occhio_m o l\'origine.'
      done
    end
  end
end

RilievoUrbano::SceneDaManifest.run unless $RILIEVO_PIPELINE
