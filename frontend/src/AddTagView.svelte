<style>
  form {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    justify-content: space-between;
    align-items: center;
  }

  button {
    padding-top: 0.5em;
    padding-bottom: 0.5em;
    padding-left: 1em;
    padding-right: 1em;
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

  .container {
    min-height: 100%;
    display: flex;
    flex-direction: column;
    flex-wrap: nowrap;
    justify-content: center;
    align-items: stretch;
    align-content: center;
  }

  .inputs {
    flex-grow: 1;
  }

  .inputs *:first-child {
    margin-top: 0;
  }

  .actions {
    margin-top: 2em;
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    justify-content: space-evenly;
    align-items: center;
    align-content: center;
  }

  .error {
    margin-top: 2em;
  }

  button,
  select,
  option {
    background-color: var(--main-bg-color);
    color: inherit;
    border: 1px solid;
    border-color: inherit;
    border-radius: 0;
    padding-top: 0.5em;
    padding-bottom: 0.5em;
    padding-left: 1em;
    padding-right: 1em;
    margin-left: 0.5em;
    margin-right: 0.5em;
    font-size: inherit;
    font-family: var(--font);
    box-shadow: none;
  }

  select {
    flex-grow: 1;
    margin: 0 2ch;
  }

  option {
    font-family: monospace;
  }
</style>

<script>
  import { selected, selectedResource, backendUrl } from "./stores.js";
  import { onMount } from "svelte";
  import LoadingText from "./LoadingText.svelte";
  import { cleanOfrakType } from "./helpers";

  export let modifierView, resourceNodeDataMap, dataPromise;
  let errorMessage,
    ofrakTagsPromise = new Promise(() => {}),
    selectedTag;

  function refreshResource() {
    // Force tree view children refresh
    resourceNodeDataMap[$selected].collapsed = false;
    resourceNodeDataMap[$selected].childrenPromise =
      $selectedResource.get_children();

    // Force hex view refresh with colors
    const originalSelected = $selected;
    $selected = undefined;
    $selected = originalSelected;
  }

  function chooseTag() {
    if (selectedTag) {
      modifierView = undefined;
      $selectedResource.add_tag(selectedTag);
    }
  }

  onMount(async () => {
    try {
      await fetch(`${backendUrl}/get_all_tags`).then(async (r) => {
        if (!r.ok) {
          throw Error(JSON.stringify(await r.json(), undefined, 2));
        }
        r.json().then((ofrakTags) => {
          ofrakTags.sort(function (a, b) {
            if (cleanOfrakType(a) > cleanOfrakType(b)) {
              return 1;
            } else {
              return -1;
            }
          });
          ofrakTagsPromise = ofrakTags;
        });
      });
    } catch (err) {
      try {
        errorMessage = JSON.parse(err.message).message;
      } catch (_) {
        errorMessage = err.message;
      }
    }
  });
</script>

<div class="container">
  <div class="inputs">
    <p>Select tag to add to resource.</p>
    {#await ofrakTagsPromise}
      <LoadingText />
    {:then ofrakTags}
      {#if ofrakTags && ofrakTags.length > 0}
        <form on:submit|preventDefault="{chooseTag}">
          New Tag: <select
            on:click|stopPropagation="{() => undefined}"
            bind:value="{selectedTag}"
          >
            <option value="{null}">Select a tag to add</option>
            {#each ofrakTags as ofrakTag}
              <option value="{ofrakTag}">
                {cleanOfrakType(ofrakTag)}
              </option>
            {/each}
          </select>

          <button
            on:click|stopPropagation="{() => undefined}"
            disabled="{!selectedTag}"
            type="submit">Add</button
          >
        </form>
      {:else}
        No tags found!
      {/if}
    {:catch}
      <p>Failed to get the list of OFRAK tags!</p>
      <p>The back end server may be down.</p>
    {/await}
    {#if errorMessage}
      <p class="error">
        Error:
        {errorMessage}
      </p>
    {/if}
  </div>
  <div class="actions">
    <button on:click="{() => (modifierView = undefined)}">Cancel</button>
  </div>
</div>
