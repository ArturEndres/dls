# dls

**`ls` com drag and drop direto do terminal.**

Liste os arquivos como sempre e arraste-os do próprio terminal para o Nautilus, o navegador, o WhatsApp Web, um e-mail ou qualquer app que aceite arquivos. Nenhuma janela extra se abre.

![Arrastando um arquivo do terminal para uma página de upload](assets/arrastar.gif)

---

## Por que existe

Terminais não deixam arrastar arquivos *para fora*. Para mandar um arquivo pelo navegador, quem está no terminal precisa abrir o gerenciador de arquivos, navegar até a mesma pasta e só então arrastar. O `dls` elimina esse caminho: o arquivo que você está vendo no terminal pode ser arrastado dali mesmo.

## Recursos

- **Arraste nativo** (XDND): funciona com qualquer app que aceite arquivos soltos.
- **Seleção múltipla**: arraste sobre os nomes (como selecionar texto), use Shift+clique para um intervalo ou Ctrl+clique para alternar.
- **Indicadores visuais**: a linha sob o mouse fica destacada (translúcida com compositor, sólida sem ele, como nas demos), o cursor vira mão, a seleção aparece em vídeo invertido e o ícone do arraste mostra quantos arquivos vão junto.
- **Abrir**: duplo clique abre com o app padrão. O clique direito mostra um menu *abrir com…* com os apps instalados para aquele tipo de arquivo.
- **Mantém o formato do `ls`**: cores, `-l`, `-h`, `-a` e as demais flags de exibição.
- **Leve**: um único arquivo Python, sem dependências para instalar num GNOME padrão. A lista aparece em ~30 ms e a interação fica pronta em ~150 ms.
- **Não deixa o terminal quebrado**: ao sair com `q`, ao fechar a aba ou ao receber `kill`, o terminal volta ao normal.

## Requisitos

**Funciona de cara:** Ubuntu e derivados com GNOME (Zorin, Pop!_OS…) numa sessão X11, usando o gnome-terminal.
**Não funciona:** sessão Wayland (padrão do Ubuntu 22.04+) e terminais que não usam a fonte do perfil do gnome-terminal (Konsole, xfce4-terminal, Ptyxis com fonte própria). Nesses casos o `dls` não quebra, só fica desalinhado ou vira `ls`.

| | |
|---|---|
| Sessão | **X11** (no Ubuntu 22.04+ o padrão é Wayland: escolha *Ubuntu on Xorg* na tela de login) |
| Terminal | **gnome-terminal** (ou outro baseado em VTE que use a fonte do perfil do gnome-terminal) |
| Python | 3.8+ |
| Bibliotecas | PyGObject, pycairo, GTK 3 |

Ubuntu, Zorin, Pop!_OS, Fedora Workstation e outras distros com GNOME já trazem tudo isso. Se faltar algo:

```bash
# Debian / Ubuntu
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0

# Fedora
sudo dnf install python3-gobject python3-cairo gtk3
```

## Instalação

```bash
git clone https://github.com/ArturEndres/dls.git
cd dls
ln -s "$PWD/dls" ~/.local/bin/dls
```

`~/.local/bin` precisa estar no seu `PATH` (no Ubuntu e derivados já está). Para conferir:

```bash
command -v dls
```

Para desinstalar, basta `rm ~/.local/bin/dls`.

## Uso

```bash
dls                  # pasta atual
dls -lh ~/Downloads  # aceita as flags do ls
dls *.pdf            # só os arquivos que casam com o padrão
dls -a               # inclui ocultos
```

O `dls` imprime a lista e fica esperando o mouse. Ao sair, a lista continua no terminal.

### Mouse

![Selecionando vários arquivos arrastando sobre os nomes e com Ctrl+clique, depois enviando todos de uma vez](assets/selecao-multipla.gif)


| Ação | Resultado |
|---|---|
| Passar o mouse sobre um nome | destaca a linha; o cursor vira mão |
| Segurar sobre um nome e mover **para o lado** | arrasta esse arquivo |
| Segurar e mover **para cima/baixo** | seleciona as linhas percorridas (o primeiro movimento decide entre arrastar e selecionar) |
| …e então sair da coluna dos nomes para o lado | arrasta todos os selecionados |
| Clique | seleciona só aquele arquivo |
| Shift + clique | seleciona o intervalo desde o último clique |
| Ctrl + clique | adiciona ou remove da seleção |
| Arrastar uma linha já selecionada | arrasta toda a seleção |
| Duplo clique | abre com o app padrão |
| Clique direito | menu *abrir com…* |

### Teclado

| Tecla | Resultado |
|---|---|
| `a` | seleciona todos |
| `Esc` | limpa a seleção (com nada selecionado, sai) |
| `q` / `Ctrl+C` | sai |

### Fora de um terminal interativo

Com a saída redirecionada (`dls | grep x`) ou sem display gráfico (SSH, TTY), o `dls` se comporta exatamente como `ls`. Erros do `ls` (por exemplo, um caminho inexistente) são exibidos e o código de saída é preservado.

## Como funciona

Nenhum programa rodando *dentro* de um terminal consegue iniciar um arraste: enquanto o botão está pressionado, o X11 entrega o ponteiro à janela do terminal. O `dls` contorna isso assim:

1. **Mouse tracking.** O `dls` liga o modo de rastreamento de mouse do terminal (`?1003` + `?1006`). A partir daí, o terminal informa em qual célula (linha, coluna) o mouse está.
2. **Calibração.** O tamanho da célula vem da fonte do seu perfil do gnome-terminal, medida pela Pango do mesmo jeito que a VTE (o motor do gnome-terminal) mede. A posição da grade na tela é deduzida cruzando cada evento do terminal com a posição real do ponteiro. Cada evento restringe a origem a um intervalo, e a interseção converge para o pixel exato em poucos movimentos.
3. **Janela transparente.** Uma janela sem bordas e semitransparente é posicionada exatamente sobre a linha sob o mouse. É ela, e não o terminal, que recebe o clique, então o arraste é um arraste GTK/XDND nativo.
4. **Seleção.** Fica guardada no `dls` e é desenhada no próprio terminal com sequências ANSI (vídeo invertido).

## Limitações

- **Só X11.** No Wayland, uma janela não pode se posicionar em coordenadas absolutas nem consultar a posição global do ponteiro. Numa sessão Wayland o `dls` avisa e funciona como `ls`.
- **Zoom do terminal** (`Ctrl +` / `Ctrl -`) ou um perfil diferente do padrão desalinham o destaque, porque a medida vem da fonte do perfil padrão.
- **Ordenação:** a lista sai sempre em ordem alfabética. Flags como `-t` e `-S` são ignoradas.
- **Listas maiores que a tela:** só as linhas visíveis respondem ao mouse. Prefira filtrar (`dls *.pdf`).
- **Nomes com caracteres largos** (CJK, emoji) podem deixar o destaque um pouco mais estreito que a linha.
- **Flags com argumento separado** (`-I padrão`, `-w 80`) são repassadas ao `ls`, mas o argumento não entra na lista de arrastáveis. Já os arquivos ocultados por `-I` ainda aparecem para arrastar.
- **Se o terminal ficar imprimindo números ao clicar** (só acontece se o `dls` for morto com `kill -9`), restaure com `reset` ou com:

  ```bash
  printf '\e[?1003l\e[?1006l\e[?7h'
  ```

## Desenvolvimento

O projeto é um único arquivo executável (`dls`) mais uma verificação automática:

```bash
python3 test_dls.py   # imprime "ok"
```

O teste cobre o parsing das flags, a lista de arquivos e a calibração da grade. A parte gráfica foi validada num servidor X aninhado (Xephyr) com um terminal VTE real e mouse simulado via XTest.

## Licença

Defina antes de publicar, por exemplo [MIT](https://choosealicense.com/licenses/mit/).
