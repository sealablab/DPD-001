---
created: 2025-12-01
modified: 2025-12-01 20:37:14
accessed: 2025-12-01 20:37:14
type: N
---
# [MarkdownVSCode](docs/N/MarkdownVSCode.md)
This note exists to briefly explain how one can get 'Obsidian like' markdown editing (in particular the quick switch to/from 'preview' mode) with one easy trick** (external vs code plugin)


### keybindings.json : (`~/Library/AppSupp/<Code>|<Cursor>/User/)

> [!NOTE] Enable quick switch between markdown / preview mode with these shortcuts!

``` json

{
	"key": "ctrl+shift+enter",
	"command": "markdown.showPreview",
	"when": "editorLangId == markdown"
},

{

	"key": "ctrl+shift+enter",
	"command": "markdown.showSource",
	"when": "activeWebviewPanelId == 'markdown.preview'"
}
```
