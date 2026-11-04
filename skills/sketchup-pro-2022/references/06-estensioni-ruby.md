# Estensioni e Ruby

## Installazione
- **Extension Warehouse** (*Extensions › Extension Warehouse*) oppure **SketchUcation**
  ExtensionStore. Per i file `.rbz`: *Extensions › Extension Manager › Install Extension*.
- Cartella Plugins (Windows): `%AppData%\SketchUp\SketchUp 2022\SketchUp\Plugins`.
  macOS: `~/Library/Application Support/SketchUp 2022/SketchUp/Plugins`.
- Verificare la compatibilità con la **2022** (Ruby 2.7). Le estensioni scritte solo per la 2024+
  (Ruby 3.2) possono non funzionare.
- Molte estensioni richiedono librerie: **TT_Lib²** (ThomThom), **LibFredo6** (Fredo6).

## Estensioni consigliate (gratuite o a pagamento: verificare la licenza)
| Estensione | Autore | A cosa serve |
|---|---|---|
| CleanUp³ | ThomThom | Pulizia: purge, spigoli coplanari, facce duplicate, materiali |
| Solid Inspector² | ThomThom | Trova e corregge ciò che impedisce il "Solid" |
| Selection Toys | ThomThom | Selezione per tipo (spigoli, facce, istanze…) |
| Joint Push Pull | Fredo6 | Push/Pull su superfici curve, spessori di gusci |
| Curviloft | Fredo6 | Loft/sweep tra curve |
| FredoScale | Fredo6 | Taper, bend, twist, rotazione scalata |
| RoundCorner | Fredo6 | Raccordi e smussi |
| Profile Builder | Mind.Sight.Studios | Profili parametrici (muri, cornici, ringhiere) con quantità |
| 1001bit Tools | 1001bit | Scale, coperture, finestre, strumenti architettonici |
| Eneroth (varie) | Eneroth3 | Face Creator, Solid Tools migliorati, utility |
| Skatter | Lindale | Scatter di vegetazione/oggetti con proxy (render) |
| Skimp | Mind.Sight.Studios | Riduzione poligoni di modelli pesanti |
| Make Faces | TIG | Chiude le facce da linee importate |
| Lumion LiveSync | Lumion | Sincronizzazione live con Lumion |

Regola: installare solo ciò che si usa davvero. Troppe estensioni rallentano l'avvio e sono la causa
più comune di crash (vedi troubleshooting).

## Ruby Console (*Window › Ruby Console*)
Gli script si possono incollare nella console. Avvolgerli sempre in un'operazione annullabile.

### Assegna un tag a tutti i componenti con un certo nome
```ruby
model = Sketchup.active_model
tag   = model.layers['40_Serramenti'] || model.layers.add('40_Serramenti')
model.start_operation('Tagga serramenti', true)
model.definitions.each do |d|
  next unless d.name =~ /^FIN_|^PRT_/
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

### Report dei componenti (nome, istanze) in console
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
(Il modello deve essere già salvato perché `model.path` non sia vuoto.)

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
- La documentazione è su ruby.sketchup.com (scegliere l'API della versione 2022).
- Per un'estensione vera: struttura `nome_ext.rb` + cartella, `SketchupExtension`, namespace in un
  modulo proprio. Distribuire come `.rbz` (zip rinominato).
