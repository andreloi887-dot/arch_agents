# Estensioni e Ruby (2025)

## Installazione
- **Extension Warehouse** (*Extensions › Extension Warehouse*) o **SketchUcation**
  ExtensionStore. File `.rbz`: *Extensions › Extension Manager › Install Extension*.
- Cartella Plugins: Windows `%AppData%\SketchUp\SketchUp 2025\SketchUp\Plugins`; macOS
  `~/Library/Application Support/SketchUp 2025/SketchUp/Plugins`.
- **Ruby 3.2 dalla 2024**: le estensioni in Ruby puro scritte per la 2022 di solito funzionano; quelle
  con parti compilate (C/C++) vanno aggiornate. Installare sempre la versione dichiarata
  compatibile con 2024/2025.
- Aggiornare prima le librerie: **TT_Lib²**, **LibFredo6**.
- Non copiare la cartella Plugins della 2022 nella 2025: reinstallare una a una.
- Dalla 2024, se un'estensione dà errore, SketchUp mostra una **finestra dedicata** che indica quale
  estensione è, con le opzioni di aggiornarla o disinstallarla.
- **Overlays** (2023): le estensioni che disegnano informazioni a schermo (quote dinamiche, analisi)
  si accendono e spengono dal pannello *Overlays*.

## Estensioni consigliate (verificare la compatibilità con la 2025 e la licenza)
| Estensione | Autore | A cosa serve |
|---|---|---|
| CleanUp³ | ThomThom | Pulizia: purge, spigoli coplanari, facce duplicate |
| Solid Inspector² | ThomThom | Trova e corregge ciò che impedisce il "Solid" |
| Selection Toys | ThomThom | Selezione per tipo |
| Joint Push Pull | Fredo6 | Push/Pull su superfici curve, gusci |
| Curviloft | Fredo6 | Loft/sweep tra curve |
| FredoScale | Fredo6 | Taper, bend, twist |
| RoundCorner | Fredo6 | Raccordi e smussi |
| Profile Builder | Mind.Sight.Studios | Profili parametrici con quantità |
| 1001bit Tools | 1001bit | Scale, coperture, strumenti architettonici |
| Eneroth (varie) | Eneroth3 | Face Creator, utility |
| Skatter | Lindale | Scatter con proxy |
| Skimp | Mind.Sight.Studios | Decimazione di modelli pesanti |
| Make Faces | TIG | Facce da linee importate |
| Lumion LiveSync | Lumion | Solo se la versione di Lumion supporta la 2025 |

Nota: alcune funzioni che prima richiedevano estensioni ora sono native (Flip, AO, PBR ed
environment per viste rapide, Search). Si può alleggerire il set.

## Ruby Console (*Extensions › Developer › Ruby Console*; in alcune versioni *Window › Ruby Console*)
Avvolgere sempre gli script in un'operazione annullabile. Gli snippet sotto sono compatibili con
Ruby 3.2.

### Assegna un tag ai componenti per prefisso del nome
```ruby
model = Sketchup.active_model
tag   = model.layers['40_Serramenti'] || model.layers.add('40_Serramenti')
model.start_operation('Tagga serramenti', true)
model.definitions.each do |d|
  next unless d.name.match?(/\A(FIN|PRT)_/)
  d.instances.each { |i| i.layer = tag }
end
model.commit_operation
```

### Sposta su Untagged tutta la geometria grezza (regola d'oro)
```ruby
model    = Sketchup.active_model
untagged = model.layers[0] # Layer0 = "Untagged"
model.start_operation('Geometria grezza su Untagged', true)
fix = lambda do |ents|
  ents.grep(Sketchup::Edge).each { |e| e.layer = untagged }
  ents.grep(Sketchup::Face).each { |e| e.layer = untagged }
end
fix.call(model.entities)
model.definitions.each { |d| fix.call(d.entities) unless d.image? }
model.commit_operation
```

### Report dei componenti (istanze, nome)
```ruby
Sketchup.active_model.definitions
  .reject { |d| d.group? || d.image? || d.instances.empty? }
  .sort_by { |d| -d.instances.size }
  .each { |d| puts "#{d.instances.size}\t#{d.name}" }
```

### Esporta ogni scena come PNG
```ruby
model  = Sketchup.active_model
folder = File.join(File.dirname(model.path), 'export_scene')
Dir.mkdir(folder) unless Dir.exist?(folder)
po = model.options['PageOptions']
old_transition = po['ShowTransition']
po['ShowTransition'] = false # evita di catturare la transizione a metà
model.pages.each do |p|
  model.pages.selected_page = p
  model.active_view.write_image(
    filename: File.join(folder, "#{p.name}.png"),
    width: 4000, height: 2500, antialias: true, transparent: false)
end
po['ShowTransition'] = old_transition
```
(Il modello deve essere già salvato. Con lo stile Photoreal l'export è più lento.)

### Report dei materiali (per preparare l'export verso Lumion)
```ruby
Sketchup.active_model.materials.sort_by(&:name).each do |m|
  tex = m.texture ? File.basename(m.texture.filename.to_s) : '-'
  puts "#{m.name}\t#{m.color.to_a[0..2].join(',')}\t#{tex}"
end
```

### Purge completo
```ruby
m = Sketchup.active_model
m.start_operation('Purge', true)
m.definitions.purge_unused
m.materials.purge_unused
m.layers.purge_unused
m.styles.purge_unused
m.commit_operation
```

## Note di sviluppo
- API su ruby.sketchup.com: scegliere la versione 2025. Dalla 2025 ci sono API per le proprietà PBR
  dei materiali e per gli environments (corrette nella 2025.0.2). Verificare i nomi esatti dei
  metodi nella documentazione prima di usarli.
- Per un'estensione: `nome_ext.rb` + cartella, `SketchupExtension`, namespace in un modulo proprio,
  distribuzione `.rbz`. Linter: `rubocop-sketchup` aggiornato per la 2024/2025.
