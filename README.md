# FinniApp Web

Sitio público de FinniApp, construido como una página estática y publicado mediante GitHub Pages.

## Desarrollo local

Abre `index.html` directamente en el navegador o inicia un servidor estático:

```powershell
npx serve .
```

## Publicación

Cada push a `main` ejecuta el flujo `.github/workflows/pages.yml`. En la configuración del repositorio, GitHub Pages debe utilizar **GitHub Actions** como origen.

La URL esperada es:

`https://victorvargass.github.io/FinniApp-Web/`

La política de privacidad queda disponible en:

`https://victorvargass.github.io/FinniApp-Web/privacy.html`
