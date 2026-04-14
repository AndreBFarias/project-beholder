# Sprint 14 — Packaging: .deb, Flatpak e AppImage

**Issue:** #9
**Status:** Backlog
**Prioridade:** Média

---

## Contexto

Adicionar distribuição formal do Beholder como pacotes instaláveis. Referência:
`~/Desenvolvimento/Conversor-Video-Para-ASCII/packaging/`

---

## Arquivos a Criar

```
packaging/
  build-deb.sh              # dpkg-deb para Ubuntu/Debian
  build-appimage.sh         # linuxdeploy para AppImage universal
  flatpak-launcher.sh       # wrapper para Flatpak
  com.beholder.app.desktop  # .desktop para uso no pacote
com.beholder.app.yml        # Manifesto Flatpak
debian/
  control                   # Package, Depends, Description
  changelog
  copyright
  rules
  compat
.github/
  workflows/
    release.yml             # CI: test + 3 builds + GitHub Release
```

---

## Dependências de Sistema (para .deb e AppImage)

```
python3 (>= 3.12)
python3-gi
python3-gi-cairo
gir1.2-gtk-4.0
gir1.2-adw-1
gir1.2-glib-2.0
python3-venv
```

**Não incluir:** Ollama e Moondream nos pacotes — são baixados pelo run.sh em runtime.

---

## Checklist de Execução

- [ ] Ler packaging/ do Conversor-Video-Para-ASCII como referência
- [ ] Criar packaging/build-deb.sh (ver issue #9 para código completo)
- [ ] Criar debian/control com dependências corretas
- [ ] Criar com.beholder.app.yml (Flatpak manifest)
- [ ] Criar packaging/build-appimage.sh adaptado para GTK4
- [ ] Criar .github/workflows/release.yml
- [ ] Testar: `./packaging/build-deb.sh 1.0.0` gera .deb
- [ ] Testar: `sudo dpkg -i *.deb` instala sem erro
- [ ] Verificar: app aparece no menu após dpkg
- [ ] `just ci-local` verde
- [ ] Commit + push + fechar issue #9

---

## Critério de Aceite

- `./packaging/build-deb.sh 1.0.0` gera `beholder_1.0.0_amd64.deb`
- `sudo dpkg -i beholder_1.0.0_amd64.deb` instala e app aparece no menu
- Manifesto Flatpak válido (`flatpak-builder --dry-run` sem erro)
- `release.yml` válido e ativado para tags `v*`
