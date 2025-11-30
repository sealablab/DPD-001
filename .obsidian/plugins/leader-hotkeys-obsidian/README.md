# README.md
I added this directory specifically to try out my tmux-esque leader hotkey config keybindings
``` bash
/Users/johnycsh/DPD/DPD-001/.obsidian/plugins/leader-hotkeys-obsidian
cat data.json | jq
```

``` json
{
  "hotkeys": [
    {
      "sequence": [
        {
          "key": "1",
          "shift": true,
          "alt": false,
          "ctrl": true,
          "meta": false
        }
      ],
      "commandID": "workspace:goto-tab-1"
    },
    {
      "sequence": [
        {
          "key": "@",
          "shift": true,
          "alt": false,
          "ctrl": true,
          "meta": false
        }
      ],
      "commandID": "workspace:goto-tab-2"
    },
    {
      "sequence": [
        {
          "key": "3",
          "shift": true,
          "alt": false,
          "ctrl": true,
          "meta": false
        }
      ],
      "commandID": "workspace:goto-tab-3"
    },
    {
      "sequence": [
        {
          "key": "ArrowLeft",
          "shift": true,
          "alt": false,
          "ctrl": true,
          "meta": false
        }
      ],
      "commandID": "editor:focus-left"
    },
    {
      "sequence": [
        {
          "key": "ArrowRight",
          "shift": true,
          "alt": false,
          "ctrl": true,
          "meta": false
        }
      ],
      "commandID": "editor:focus-right"
    },
    {
      "sequence": [
        {
          "key": "ArrowUp",
          "shift": true,
          "alt": false,
          "ctrl": true,
          "meta": false
        }
      ],
      "commandID": "workspace:previous-tab"
    },
    {
      "sequence": [
        {
          "key": "|",
          "shift": true,
          "alt": false,
          "ctrl": true,
          "meta": false
        }
      ],
      "commandID": "workspace:split-vertical"
    },
    {
      "sequence": [
        {
          "key": "_",
          "shift": true,
          "alt": false,
          "ctrl": true,
          "meta": false
        }
      ],
      "commandID": "workspace:split-horizontal"
    },
    {
      "sequence": [
        {
          "key": "ArrowLeft",
          "shift": true,
          "alt": false,
          "ctrl": false,
          "meta": true
        }
      ],
      "commandID": "editor:focus-left"
    },
    {
      "sequence": [
        {
          "key": "ArrowRight",
          "shift": true,
          "alt": false,
          "ctrl": false,
          "meta": true
        }
      ],
      "commandID": "editor:focus-right"
    }
  ]
}
```
