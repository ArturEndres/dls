# TODO

Só o que falta. O que já foi feito está no histórico do git.

## Plataforma

- [ ] **Backend OSC 72 (protocolo de drag-and-drop do kitty).** Adiado em 13/10/2026 porque precisa do kitty instalado para testar.
  O programa manda sequências de escape e o terminal faz o arraste nativo. Funciona no Wayland, no X11 e no macOS, sem GTK, sem janela sobreposta e sem calibração. Dá para fazer só com a biblioteca padrão do Python.
  - Motivo: o Ubuntu 25.10+ e o GNOME 50 não têm mais sessão X11, então o backend atual só funciona até o Ubuntu 24.04 ([Ubuntu](https://discourse.ubuntu.com/t/ubuntu-25-10-drops-support-for-gnome-on-xorg/62538), [GNOME 50](https://www.phoronix.com/news/GNOME-Mutter-Drops-X11)).
  - kitty 0.47+ (maio/2026), protocolo estável desde junho/2026. O yazi já usa.
  - Ordem de escolha: OSC 72 → backend X11 atual → aviso + `ls`.
  - Spec: <https://sw.kovidgoyal.net/kitty/dnd-protocol/>
- [ ] Acompanhar o suporte a OSC 72 (talvez abrir uma issue no VTE pedindo):
  - Ghostty: em desenvolvimento ([#12852](https://github.com/ghostty-org/ghostty/issues/12852)).
  - iTerm2: citado como suportado, não confirmado.
  - tmux: recusou por enquanto em 9/10/2026 ([#5595](https://github.com/tmux/tmux/issues/5595)).
  - VTE (gnome-terminal, Ptyxis): nada encontrado.

## Diferenças em relação ao `ls`

- [ ] Enquanto aberto, várias pastas (e o `-R`) ficam sem cabeçalho e o `-l` fica sem a linha `total`. Hoje está documentado como limitação no README.

## Desempenho

- [ ] O `ls` roda 3 vezes (listar, renderizar, imprimir ao sair). Com 10 mil arquivos o `dls` abre em 128 ms (`ls`) e 240 ms (`-lt`). Aceitável; só cortar se incomodar.

## Testes

- [ ] Não coberto pelo `test_gui.py`: duplo clique (abriria apps de verdade) e o destaque translúcido com compositor (o Xephyr não tem compositor).
