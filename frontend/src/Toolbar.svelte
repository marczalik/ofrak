<style>
  .vbox {
    display: flex;
    flex-direction: column;
    flex-wrap: nowrap;
    justify-content: flex-start;
    align-items: stretch;
  }

  button {
    margin-bottom: 1em;
    padding-top: 0.5em;
    padding-bottom: 0.5em;
    padding-left: 1em;
    padding-right: 1em;
    background-color: var(--main-bg-color);
    color: var(--main-fg-color);
    border: 1px solid var(--main-fg-color);
    border-radius: 0;
    font-size: smaller;
    overflow: hidden;
    box-shadow: none;
  }

  button:hover,
  button:focus {
    outline: none;
    box-shadow: inset 1px 1px 0 var(--main-fg-color),
      inset -1px -1px 0 var(--main-fg-color);
  }

  button:active {
    box-shadow: inset 2px 2px 0 var(--main-fg-color),
      inset -2px -2px 0 var(--main-fg-color);
  }
</style>

<script>
  import Icon from "./Icon.svelte";

  import { shortcuts } from "./keyboard.js";

  export let toolbarButtons;

  /***
   * Show the loading spinner while an async onclick function does its thing.
   */
  function wrapOnCick(button) {
    return async (e) => {
      const oldIcon = button.iconUrl;
      button.iconUrl = "/icons/loading.svg";
      toolbarButtons = toolbarButtons;
      await button
        .onclick(e)
        .then((_) => {
          button.iconUrl = oldIcon;
          toolbarButtons = toolbarButtons;
        })
        .catch((e) => {
          button.iconUrl = "/icons/error.svg";
          toolbarButtons = toolbarButtons;
          try {
            let errorObject = JSON.parse(e.message);
            alert(`${errorObject.type}: ${errorObject.message}`);
          } catch {
            alert(e);
          }
          console.error(e);
        });
    };
  }

  $: Array.from(toolbarButtons).forEach((button) => {
    if (!button.shortcut) {
      return;
    }
    shortcuts[button.shortcut] = wrapOnCick(button);
  });
</script>

<div class="vbox">
  {#each toolbarButtons as button}
    <button
      on:click="{wrapOnCick(button)}"
      title="{button.text +
        (button.shortcut
          ? ' (Shortcut key: ' +
            button.shortcut.split('+').reverse().join(' + ') +
            ')'
          : '')}"
    >
      {#if button.iconUrl}
        <Icon url="{button.iconUrl}" />
      {/if}
      {button.text}
    </button>
  {/each}
</div>
