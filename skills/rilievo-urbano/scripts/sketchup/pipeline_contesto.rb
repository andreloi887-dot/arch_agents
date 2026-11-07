# encoding: UTF-8
# SketchUp Pro 2022 (Ruby 2.7) – Esecuzione automatica, senza finestre di dialogo:
#   apre il modello base georeferenziato → costruisce il contesto da contesto.json → nasconde il terreno di
#   Add Location → crea le scene camera-matched ed esporta i PNG → esporta inventario.json → viste aeree →
#   salva una copia → scrive esito_pipeline.json (e, se richiesto, chiude SketchUp).
#
# Avvio da riga di comando (Windows):
#   set RILIEVO_CONFIG=C:\...\modello\pipeline.json
#   "C:\Program Files\SketchUp\SketchUp 2022\SketchUp.exe" -RubyStartup "C:\...\pipeline_contesto.rb"
# oppure da Window › Ruby Console:  $RILIEVO_CONFIG = 'C:/.../pipeline.json'; load 'C:/.../pipeline_contesto.rb'
#
# pipeline.json (percorsi assoluti o relativi alla cartella del file):
#   { "skp_base": "base_georef.skp", "contesto": "contesto.json", "manifest": "manifest_riprese.json",
#     "uscita": "uscita_sketchup", "chiudi": false }
# Il modello base deve essere già georeferenziato (File › Geo-location › Add Location sull'incrocio).
require 'json'
$RILIEVO_PIPELINE = true

module RilievoUrbano
  module Pipeline
    DIR = File.dirname(File.expand_path(__FILE__))

    def self.log(msg)
      line = "[#{Time.now.strftime('%H:%M:%S')}] #{msg}"
      puts line
      File.open(@log_path, 'a:UTF-8') { |f| f.puts(line) } if @log_path
    end

    def self.cfg_path
      $RILIEVO_CONFIG || ENV['RILIEVO_CONFIG'] || File.join(DIR, 'pipeline.json')
    end

    def self.risolvi(base, p)
      p.nil? ? nil : File.expand_path(p, base)
    end

    def self.nascondi_location(model)
      nascosti = []
      model.entities.each do |e|
        next unless e.respond_to?(:name) && (e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance) || e.is_a?(Sketchup::Image))
        nome = e.is_a?(Sketchup::ComponentInstance) ? "#{e.name} #{e.definition.name}" : e.name.to_s
        next if nome =~ /CONTESTO|CATASTO/
        next unless nome =~ /Location|Terrain|Terreno|Snapshot|Posizione|Geo/i
        e.hidden = true
        nascosti << nome.strip
      end
      rif = model.layers['00_Riferimenti']
      rif.visible = false if rif
      nascosti
    end

    def self.vista(model, nome, eye, target, fov, file)
      cam = Sketchup::Camera.new(eye, target, Z_AXIS, true, fov)
      model.active_view.camera = cam
      pg = model.pages[nome]
      model.pages.erase(pg) if pg
      model.pages.add(nome)
      model.active_view.write_image(filename: file, width: 1600, height: 1000, antialias: true, transparent: false)
    end

    def self.esegui
      esito = { 'ok' => false, 'passi' => {}, 'errori' => [] }
      cfg_file = cfg_path
      base = File.dirname(File.expand_path(cfg_file))
      cfg = JSON.parse(File.read(cfg_file, encoding: 'UTF-8'))
      out = risolvi(base, cfg['uscita'] || 'uscita_sketchup')
      Dir.mkdir(out) unless Dir.exist?(out)
      @log_path = File.join(out, 'pipeline.log')
      File.write(@log_path, '')
      log "Configurazione: #{cfg_file}"
      t0 = Time.now
      begin
        skp = risolvi(base, cfg['skp_base'])
        if skp && File.expand_path(Sketchup.active_model.path.to_s) != skp
          raise "Modello base non trovato: #{skp}" unless File.exist?(skp)
          Sketchup.open_file(skp)
        end
        model = Sketchup.active_model
        log "Modello: #{model.path} – SketchUp #{Sketchup.version}"
        raise 'Modello non georeferenziato: fare Add Location sull\'incrocio e salvare il modello base' unless model.georeferenced?

        load File.join(DIR, 'costruisci_contesto.rb')
        t = Time.now
        RilievoUrbano::Contesto.costruisci(risolvi(base, cfg['contesto'] || 'contesto.json'))
        esito['passi']['contesto_s'] = (Time.now - t).round(1)
        log "Contesto costruito in #{esito['passi']['contesto_s']} s"

        esito['passi']['nascosti'] = nascondi_location(model)
        log "Nascosti (terreno/snapshot di Add Location, 00_Riferimenti): #{esito['passi']['nascosti'].join(', ')}"

        man = risolvi(base, cfg['manifest'])
        if man && File.exist?(man)
          load File.join(DIR, 'scene_da_manifest.rb')
          fatte = RilievoUrbano::SceneDaManifest.run(man, File.join(out, 'export_verifica'), false)
          esito['passi']['scene'] = fatte
          log "Scene camera-matched esportate: #{fatte.size}"
        else
          log "Manifest assente: scene di verifica saltate (#{man})"
        end

        load File.join(DIR, 'inventario_modello.rb')
        inv = RilievoUrbano::Inventario.run(File.join(out, 'inventario.json'))
        esito['passi']['inventario'] = inv
        log "Inventario: #{inv}"

        tg = RilievoUrbano::Contesto.trasf_geo(model, cfg['lat'] || 39.25240, cfg['lng'] || 9.11527)
        p = ->(x, y, z) { tg * Geom::Point3d.new(x.m, y.m, z.m) }
        vista(model, 'VISTA_aerea_SO', p.call(-60, -45, 40), p.call(5, 20, 2), 55, File.join(out, 'vista_aerea_SO.png'))
        vista(model, 'VISTA_aerea_NE', p.call(55, 75, 38), p.call(0, 15, 2), 55, File.join(out, 'vista_aerea_NE.png'))
        vista(model, 'VISTA_angolo', p.call(-12, 4, 2.6), p.call(2, 16, 2.0), 75, File.join(out, 'vista_angolo.png'))
        log 'Viste aeree esportate'

        dest = File.join(out, 'contesto_generato.skp')
        # file vuoti lasciati da un'esecuzione interrotta (.skp o backup .skb a 0 byte) bloccano model.save
        [dest, dest.sub(/\.skp\z/, '.skb')].each { |f| File.delete(f) if File.exist?(f) && File.size(f) == 0 }
        model.save(dest)
        esito['passi']['skp'] = dest
        log "Salvato: #{dest}"
        esito['ok'] = true
      rescue StandardError => e
        esito['errori'] << "#{e.class}: #{e.message}"
        esito['errori'] += e.backtrace.first(8)
        log "ERRORE: #{e.class}: #{e.message}"
        e.backtrace.first(8).each { |l| log "  #{l}" }
      ensure
        esito['durata_s'] = (Time.now - t0).round(1)
        File.write(File.join(out, 'esito_pipeline.json'), JSON.pretty_generate(esito), encoding: 'UTF-8')
        log "Fine (ok=#{esito['ok']}) in #{esito['durata_s']} s – #{File.join(out, 'esito_pipeline.json')}"
        Sketchup.quit if cfg && cfg['chiudi']
      end
    end
  end
end

# Avvio differito: con -RubyStartup il modello e l'interfaccia devono finire di caricarsi.
UI.start_timer(4, false) { RilievoUrbano::Pipeline.esegui }
