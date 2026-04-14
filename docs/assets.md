# docs/assets.md — Prompts para Geração de Ícones

Guia completo de prompts para geração dos ícones do Project Beholder.
Ferramentas suportadas: Grok/Aurora, Midjourney, DALL-E 3, Stable Diffusion.

**Referência de logo:** `beholder-icon.png` na raiz — olho estilizado em tons magenta/rosa sobre fundo circular escuro, estética cyberpunk, estilo vetor limpo.

**Paleta Dracula obrigatória:**
```
background:   #282a36
current_line: #44475a
foreground:   #f8f8f2
comment:      #6272a4
cyan:         #8be9fd
green:        #50fa7b
orange:       #ffb86c
pink:         #ff79c6
purple:       #bd93f9
red:          #ff5555
yellow:       #f1fa8c
```

---

## Ícone Principal do App (GTK / .desktop)

Referência: `beholder-icon.png` já existe e é o ícone oficial.
Usar como base para gerar variantes se necessário.

**Prompt positivo:**
```
stylized eye icon, single eye with geometric iris, cyberpunk aesthetic,
magenta and purple color palette (#bd93f9 purple, #ff79c6 pink),
dark circular background (#282a36), clean vector art, minimalist,
high contrast, suitable for app icon, 512x512, transparent background,
no text, no decorations
```

**Prompt negativo:**
```
realistic, photographic, complex background, text, watermark,
low contrast, blurry, multiple eyes, cartoon, cute style
```

---

## Ícones de Ação — Módulo Caçada

### INICIAR (estado padrão)
**Cor de destaque:** `#50fa7b` (green)
**Prompt positivo:**
```
minimalist icon, play button arrow pointing right, filled triangle,
color #50fa7b green on transparent background, clean vector,
32x32 pixels, pixel-perfect, single color, no gradients, no shadows
```

### PAUSAR (aparece durante scraping)
**Cor de destaque:** `#ffb86c` (orange)
**Prompt positivo:**
```
minimalist icon, two vertical parallel bars (pause symbol),
color #ffb86c orange on transparent background, clean vector,
32x32 pixels, pixel-perfect, single color, no gradients
```

### CANCELAR
**Cor de destaque:** `#ff5555` (red)
**Prompt positivo:**
```
minimalist icon, X mark or cross symbol, bold strokes,
color #ff5555 red on transparent background, clean vector,
32x32 pixels, pixel-perfect, single color, no gradients
```

### FURTIVO (toggle)
**Cor de destaque:** `#8be9fd` (cyan) quando ativo, `#6272a4` (comment) quando inativo
**Prompt positivo:**
```
minimalist icon, ghost or shadow figure, simple silhouette,
color #8be9fd cyan on transparent background, clean vector,
32x32 pixels, stealth/hidden concept, no details, flat design
```

---

## Ícones de Ação — Módulo Córtex

### ANALISAR
**Cor de destaque:** `#ff79c6` (pink)
**Prompt positivo:**
```
minimalist icon, brain outline or neural network nodes connected,
simple geometric representation, color #ff79c6 pink,
transparent background, clean vector, 32x32 pixels, flat design
```

### PAUSAR IA
**Cor de destaque:** `#ffb86c` (orange)
(Reutilizar variante de PAUSAR com contexto de IA — dois traços verticais + pequeno ícone de circuito)

### EXPURGAR VRAM
**Cor de destaque:** `#ff5555` (red)
**Prompt positivo:**
```
minimalist icon, memory chip or GPU chip with X or eject symbol,
bold and clear, color #ff5555 red on transparent background,
clean vector, 32x32 pixels, flat design, no gradients
```

---

## Ícones de Ação — Módulo Espólio

### GERAR PACOTE
**Cor de destaque:** `#50fa7b` (green)
**Prompt positivo:**
```
minimalist icon, archive box or package with down arrow,
color #50fa7b green on transparent background, clean vector,
32x32 pixels, flat design, represents creating a zip package
```

### ABRIR PASTA
**Cor de destaque:** `#8be9fd` (cyan)
**Prompt positivo:**
```
minimalist icon, folder with arrow pointing outward or opening,
color #8be9fd cyan on transparent background, clean vector,
32x32 pixels, flat design, file explorer concept
```

### EXPORTAR CSV
**Cor de destaque:** `#f1fa8c` (yellow)
**Prompt positivo:**
```
minimalist icon, spreadsheet or table grid with export arrow,
color #f1fa8c yellow on transparent background, clean vector,
32x32 pixels, flat design, data export concept
```

### LIMPAR SESSÃO
**Cor de destaque:** `#ff5555` (red)
**Prompt positivo:**
```
minimalist icon, trash can or broom sweeping, bold and clear,
color #ff5555 red on transparent background, clean vector,
32x32 pixels, flat design, destructive action visual cue
```

---

## Ícones de Ação — Módulo Protocolo

### ADICIONAR URL
**Cor de destaque:** `#50fa7b` (green)
**Prompt positivo:**
```
minimalist icon, plus sign inside circle or link symbol with plus,
color #50fa7b green on transparent background, clean vector,
32x32 pixels, flat design, add new item concept
```

### IMPORTAR LISTA
**Cor de destaque:** `#8be9fd` (cyan)
**Prompt positivo:**
```
minimalist icon, document with lines and down arrow, import symbol,
color #8be9fd cyan on transparent background, clean vector,
32x32 pixels, flat design, file import concept
```

### EXECUTAR LOTE
**Cor de destaque:** `#bd93f9` (purple)
**Prompt positivo:**
```
minimalist icon, stack of arrows pointing right or play button with lines,
color #bd93f9 purple on transparent background, clean vector,
32x32 pixels, flat design, batch execution concept
```

### RETOMAR SESSÃO
**Cor de destaque:** `#ffb86c` (orange)
**Prompt positivo:**
```
minimalist icon, curved arrow pointing right (resume/restore symbol),
color #ffb86c orange on transparent background, clean vector,
32x32 pixels, flat design, resume/restore concept
```

---

## Ícones de Ação — Módulo Grimório

### SALVAR
**Cor de destaque:** `#50fa7b` (green)
**Prompt positivo:**
```
minimalist icon, floppy disk or save symbol, classic and recognizable,
color #50fa7b green on transparent background, clean vector,
32x32 pixels, flat design, save action
```

### TESTAR OLLAMA
**Cor de destaque:** `#8be9fd` (cyan) — verde se OK, vermelho se falha
**Prompt positivo:**
```
minimalist icon, signal waves or WiFi-like symbol with checkmark,
color #8be9fd cyan on transparent background, clean vector,
32x32 pixels, flat design, connectivity test concept
```

### RESTAURAR PADRÕES
**Cor de destaque:** `#ffb86c` (orange)
**Prompt positivo:**
```
minimalist icon, circular arrow (reset/restore symbol), simple loop,
color #ffb86c orange on transparent background, clean vector,
32x32 pixels, flat design, reset to defaults concept
```

### ABRIR LOGS
**Cor de destaque:** `#6272a4` (comment)
**Prompt positivo:**
```
minimalist icon, document with horizontal lines representing text log,
color #6272a4 grey-blue on transparent background, clean vector,
32x32 pixels, flat design, log file concept
```

---

## Ícones de Status Bar

### Status Ativo
**Cor:** `#50fa7b` (green)
**Formato:** ponto circular preenchido, 8×8px

### Status Pausado
**Cor:** `#ffb86c` (orange)
**Formato:** ponto circular preenchido, 8×8px

### Status Concluído
**Cor:** `#8be9fd` (cyan)
**Formato:** ponto circular preenchido, 8×8px

### Status com Erro
**Cor:** `#ff5555` (red)
**Formato:** ponto circular preenchido, 8×8px

---

## Ícones da Sidebar (Adwaita Symbolic — preferidos)

Os ícones da sidebar usam o conjunto **Adwaita symbolic** incluído no GNOME.
Não requerem geração externa. Referências por módulo:

| Módulo   | Ícone Adwaita sugerido                  | Cor de destaque |
|----------|-----------------------------------------|-----------------|
| Caçada   | `system-search-symbolic`               | `#bd93f9`       |
| Córtex   | `preferences-system-symbolic`          | `#ff79c6`       |
| Espólio  | `folder-download-symbolic`             | `#50fa7b`       |
| Protocolo| `view-list-symbolic`                   | `#ffb86c`       |
| Grimório | `accessories-text-editor-symbolic`     | `#8be9fd`       |

---

## Diretrizes Gerais de Estilo

1. **Fundo:** sempre transparente (PNG com canal alpha)
2. **Cor única:** cada ícone usa uma cor da paleta Dracula — sem gradientes
3. **Tamanho padrão:** 32×32px para botões de ação, 512×512px para ícone do app
4. **Estilo:** flat design, linhas limpas, sem sombras, sem bordas decorativas
5. **Espessura de traço:** mínimo 2px para garantir legibilidade em telas HiDPI
6. **Exportação:** SVG preferencialmente (vetorial), PNG como fallback

## Ferramentas Recomendadas

- **Grok/Aurora:** melhor para ícones vetoriais com instruções precisas de cor
- **DALL-E 3:** bom para conceitos abstratos, menos preciso em cores exatas
- **Midjourney:** excelente qualidade visual, usar com `--style raw` para flat design
- **Stable Diffusion + ControlNet:** maior controle sobre forma, requer setup local
- **Inkscape:** edição manual pós-geração para ajuste de paleta exata Dracula
