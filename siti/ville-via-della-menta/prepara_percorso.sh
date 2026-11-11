#!/usr/bin/env bash
# Trasforma il video di un percorso di camera nei fotogrammi che il sito scorre.
#
#   ./prepara_percorso.sh nome video.mp4 [fotogrammi] [video_verticale.mp4]
#
# - nome: quale percorso si prepara. "insieme" per quello in apertura del sito,
#   l'id della villa (villa-1 … villa-4) per quello della sua pagina.
# - fotogrammi: quanti estrarne in tutto (predefinito 180). Più fotogrammi = moto
#   più fluido ma pagina più pesante: 150–240 è l'intervallo sensato.
# - video_verticale: facoltativo, lo stesso percorso reso in verticale per i
#   telefoni. Se manca, la versione telefono è il ritaglio centrale di quello
#   orizzontale.
# Alla fine stampa i valori da copiare in dati.js.
set -euo pipefail

uso="./prepara_percorso.sh nome video.mp4 [fotogrammi] [video_verticale.mp4]"
nome="${1:?Indica il nome del percorso: $uso}"
video="${2:?Indica il video: $uso}"
quanti="${3:-180}"
verticale="${4:-}"
case "$nome" in *[!a-z0-9-]*) echo "Il nome può contenere solo minuscole, cifre e trattini: $nome" >&2; exit 1 ;; esac

qui="$(cd "$(dirname "$0")" && pwd)"
uscita="$qui/immagini/percorso/$nome"

durata="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$video")"
ritmo="$(awk -v n="$quanti" -v d="$durata" 'BEGIN { printf "%.6f", n / d }')"

rm -rf "$uscita/desktop" "$uscita/telefono"
mkdir -p "$uscita/desktop" "$uscita/telefono"

# Schermi larghi: 1920 px di larghezza.
ffmpeg -v error -y -i "$video" -vf "fps=$ritmo,scale=1920:-2:flags=lanczos" \
  -frames:v "$quanti" -c:v libwebp -quality 72 -start_number 1 "$uscita/desktop/%04d.webp"

# Telefoni: 900 px di larghezza in verticale.
if [ -n "$verticale" ]; then
  durata_v="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$verticale")"
  ritmo_v="$(awk -v n="$quanti" -v d="$durata_v" 'BEGIN { printf "%.6f", n / d }')"
  ffmpeg -v error -y -i "$verticale" -vf "fps=$ritmo_v,scale=900:-2:flags=lanczos" \
    -frames:v "$quanti" -c:v libwebp -quality 68 -start_number 1 "$uscita/telefono/%04d.webp"
else
  ffmpeg -v error -y -i "$video" -vf "fps=$ritmo,crop=ih*3/4:ih,scale=900:-2:flags=lanczos" \
    -frames:v "$quanti" -c:v libwebp -quality 68 -start_number 1 "$uscita/telefono/%04d.webp"
fi

fatti="$(find "$uscita/desktop" -name '*.webp' | wc -l | tr -d ' ')"
fatti_tel="$(find "$uscita/telefono" -name '*.webp' | wc -l | tr -d ' ')"
if [ "$fatti" != "$fatti_tel" ]; then
  echo "Attenzione: $fatti fotogrammi per desktop e $fatti_tel per telefono; devono coincidere." >&2
  exit 1
fi

echo "Fatto: $fatti fotogrammi. Peso: $(du -sh "$uscita/desktop" | cut -f1) desktop, $(du -sh "$uscita/telefono" | cut -f1) telefono."
if [ "$nome" = "insieme" ]; then echo "In dati.js → percorso:"; else echo "In dati.js → villa \"$nome\" → percorso:"; fi
echo "    cartella: \"immagini/percorso/$nome/desktop\","
echo "    cartella_telefono: \"immagini/percorso/$nome/telefono\","
echo "    fotogrammi: $fatti,"
