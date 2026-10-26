# Mi UChile — App Oficial

App web del Club Universidad de Chile con datos en vivo desde Wikipedia (CC BY-SA).

## Características

- **Tabla de Posiciones** — 16 equipos de la Liga de Primera, actualizada automáticamente desde Wikipedia.
- **Partidos** — Próximo partido y últimos resultados de la U.
- **Plantel** — Lista oficial de jugadores 2026.
- **Copas** — Sub-tabs para:
  - Serie Pre-Libertadores
  - Copa Libertadores
  - Copa Sudamericana
  - Supercopa de Chile
- **Estadísticas** — Goleadores, asistencias (Wikipedia) y vallas invictas.
- **Mística** — Historia del Romántico Viajero + cánticos de Los de Abajo.
- Estilo visual **Apple Design** (Liquid Glass, springs, tipografía optical).

## Cómo funciona la actualización automática

```
  ┌────────────────────────────┐
  │   Wikipedia (es.wikipedia) │
  │   Licencia: CC BY-SA       │
  └────────────┬───────────────┘
               │ cada 6 horas
               ▼
  ┌────────────────────────────┐
  │   GitHub Action             │
  │   .github/workflows/        │
  │   update-data.yml           │
  └────────────┬───────────────┘
               │ ejecuta
               ▼
  ┌────────────────────────────┐
  │   scripts/                  │
  │   scrape_wikipedia.py       │
  │   (scraper Python)          │
  └────────────┬───────────────┘
               │ genera
               ▼
  ┌────────────────────────────┐
  │   data.json                 │
  │   (commit automático)       │
  └────────────┬───────────────┘
               │ tu index.html
               │ carga con fetch()
               ▼
  ┌────────────────────────────┐
  │   GitHub Pages              │
  │   https://TU.github.io/     │
│   mi-uchile-app/             │
  └────────────────────────────┘
```

Cada 6 horas (00:00, 06:00, 12:00, 18:00 UTC), el Action corre el scraper, que descarga la página de Wikipedia de la Liga de Primera 2026, parsea la tabla de posiciones y los goleadores/asistentes, y comitea `data.json` al repo. GitHub Pages se actualiza solo.

## Estructura del repositorio

```
mi-uchile-app/
├── index.html                          ← la web (HTML estático)
├── data.json                           ← datos generados (auto, no editar a mano)
├── logos/                               ← 16 escudos vectorizados
│   ├── colo-colo.svg
│   ├── universidad-de-chile.png
│   └── ... (14 más)
├── scripts/
│   └── scrape_wikipedia.py             ← scraper que lee Wikipedia y genera data.json
├── .github/
│   └── workflows/
│       └── update-data.yml              ← GitHub Action (cada 6 horas)
├── .gitignore
└── README.md                            ← este archivo
```

Total: ~1.5 MB (casi todo son los escudos).

## Publicar en GitHub Pages (5 minutos)

### 1) Crear el repositorio
- Ve a https://github.com/new
- Nombre: `mi-uchile-app` (o el que quieras)
- **Público** (necesario para GitHub Pages gratuito)
- **NO** marques "Add a README" — ya tienes uno aquí
- Click **Create repository**

### 2) Subir los archivos
**Opción A — Por la web (más simple)**
1. En tu repo nuevo, click **Add file → Upload files**
2. Arrastra **TODO** el contenido de la carpeta: `index.html`, `data.json`, `logos/`, `scripts/`, `.github/`, `README.md`, `.gitignore`
   - Para `.github/` y `scripts/`: arrastra la carpeta completa, GitHub la sube recursivamente
   - Para `.gitignore`: GitHub no muestra archivos que empiezan con punto; súbelo así: Add file → Create new file → nombre `.gitignore` → pega el contenido → Commit
3. Commit message: `App inicial con escudos y scraper`
4. Click **Commit changes**

**Opción B — Con git en terminal**
```bash
git clone https://github.com/TU_USUARIO/mi-uchile-app.git
cd mi-uchile-app
# Copia aquí TODO el contenido de la carpeta
git add .
git commit -m "App inicial con escudos y scraper"
git push origin main
```

### 3) Activar GitHub Pages
1. En tu repo: pestaña **Settings** → **Pages** (menú izquierdo)
2. **Source**: *Deploy from a branch*
3. **Branch**: `main` / **Folder**: `/ (root)`
4. Click **Save**
5. Espera 30–60 segundos. Tu URL será:
   ```
   https://TU_USUARIO.github.io/mi-uchile-app/
   ```

### 4) Verificar que el Action corre
1. Ve a la pestaña **Actions** de tu repo
2. Deberías ver el workflow **"Actualizar datos desde Wikipedia"** con un run en amarillo (running) o verde (success)
3. Si no corre inmediatamente, puedes dispararlo manualmente: Actions → selecciona el workflow → **Run workflow**
4. Cuando termina, verás un commit automático de `github-actions[bot]` con el `data.json` actualizado

## Mantenimiento

### ¿Cada cuánto se actualiza?
El Action corre **cada 6 horas** (cron `0 0,6,12,18 * * *`). Para cambiar la frecuencia, edita `.github/workflows/update-data.yml` y modifica el `cron`. Mínimo: cada 5 minutos (no recomendado, sería irrespetuoso con Wikipedia).

### ¿Cómo forzar una actualización ahora?
1. Ve a la pestaña **Actions**
2. Selecciona "Actualizar datos desde Wikipedia"
3. Click **Run workflow** → **Run workflow**
4. En ~30 segundos tendrás el `data.json` actualizado y la web refrescada

### ¿Qué pasa si Wikipedia cambia el formato?
Si el scraper falla (el `data.json` no se actualiza), el Action mostrará una ❌ roja. La web seguirá funcionando con el último `data.json` válido (gracias al `FALLBACK_DATA` embebido en el HTML). Para arreglarlo, edita `scripts/scrape_wikipedia.py` y ajusta el parser, luego comitea — el Action correrá con la nueva versión.

### ¿Cómo cambiar el User-Agent del scraper?
Wikipedia pide un User-Agent descriptivo con contacto. El scraper usa por defecto:
```
MiUChileApp/1.0 (https://github.com/youruser/mi-uchile-app; mockup@app.example.com)
```
Cámbialo en `scripts/scrape_wikipedia.py` (línea con `UA = ...`) por uno con tu GitHub real y tu email. No es obligatorio, pero es de buena educación para con Wikipedia.

## Notas legales

- **Datos**: Wikipedia, licencia [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). La app cita la fuente en el footer de la vista Estadísticas.
- **Logos**: 10 descargados de Wikimedia Commons (CC BY-SA), 6 estilizados con colores y código de equipo (los clubes sin escudo oficial en Commons).
- **App**: código libre para uso personal/educativo. No afiliada con la ANFP ni con Club Universidad de Chile.

## Si más adelante quieres actualizar un escudo

Solo reemplaza el archivo en `logos/` (con el mismo nombre) y vuelve a hacer commit + push. GitHub Pages se actualiza solo en ~30s.
